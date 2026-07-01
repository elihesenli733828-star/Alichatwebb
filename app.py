import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, abort
from flask_socketio import SocketIO, emit, send
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'alichat_gizli_anahtar'

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, 'alichat.db')

# --- VERİTABANI KURULUMU ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # users tablosuna is_admin (0 veya 1) ve is_banned (0 veya 1) alanlarını ekledik
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0
        )
    ''')
    # İlk admin hesabını otomatik oluşturuyoruz (Kullanıcı adı: admin, Şifre: admin123)
    try:
        admin_pass = generate_password_hash('admin123')
        cursor.execute("INSERT INTO users (username, password, is_admin) VALUES ('admin', ?, 1)", (admin_pass,))
    except sqlite3.IntegrityError:
        pass # Admin zaten varsa hata vermesin
        
    conn.commit()
    conn.close()

init_db()

# Admin kontrol fonksiyonu
def is_current_user_admin():
    if 'username' not in session:
        return False
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT is_admin FROM users WHERE username = ?', (session['username'],))
    user = cursor.fetchone()
    conn.close()
    return user and user[0] == 1

# --- SAYFA YÖNLENDİRMELERİ ---

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # Ban kontrolü
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT is_banned FROM users WHERE username = ?', (session['username'],))
    user = cursor.fetchone()
    conn.close()
    
    if user and user[0] == 1:
        session.pop('username', None)
        return "Hesabınız admin tarafından yasaklanmıştır (BANNED)!", 403
        
    return render_template('index.html', username=session['username'], is_admin=is_current_user_admin())

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            return render_template('register.html', error="Lütfen tüm alanları doldurun.")
        
        hashed_password = generate_password_hash(password)
        
        try:
            conn = sqlite3.connect(DB_FILE)
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (username, password, is_admin, is_banned) VALUES (?, ?, 0, 0)', (username, hashed_password))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return render_template('register.html', error="Bu kullanıcı adı zaten alınmış!")
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT password, is_banned FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            if user[1] == 1:
                return render_template('login.html', error="Bu hesap yasaklanmıştır!")
            if check_password_hash(user[0], password):
                session['username'] = username
                return redirect(url_for('index'))
                
        return render_template('login.html', error="Hatalı kullanıcı adı veya şifre!")
    return render_template('login.html')

# 🛠️ ADMIN PANELİ ROTASI
@app.route('/admin')
def admin_panel():
    if not is_current_user_admin():
        return abort(403) # Admin olmayan erişemez
        
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT id, username, is_banned, is_admin FROM users')
    users = cursor.fetchall()
    conn.close()
    return render_template('admin.html', users=users)

# 🔨 BANLAMA TETİKLEYİCİSİ
@app.route('/admin/ban/<int:user_id>')
def ban_user(user_id):
    if not is_current_user_admin(): return abort(403)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_banned = 1 WHERE id = ? AND is_admin = 0', (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_panel'))

# 🔓 BAN AÇMA TETİKLEYİCİSİ
@app.route('/admin/unban/<int:user_id>')
def unban_user(user_id):
    if not is_current_user_admin(): return abort(403)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_banned = 0 WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_panel'))

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

# --- SOHBET OLAYLARI ---
@socketio.on('message')
def handle_message(msg):
    send(msg, broadcast=True)
    # Admin paneline de canlı düşmesi için admin_room veya genel dinleyiciye pushlanabilir.
    # Mevcut yapıda admin de odada olacağı için tüm akışı canlı görür.

@socketio.on('audio_message')
def handle_audio_message(data):
    emit('audio_message', data, broadcast=True)

@socketio.on('image_message')
def handle_image_message(data):
    emit('image_message', data, broadcast=True)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
