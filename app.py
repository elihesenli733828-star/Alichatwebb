import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_socketio import SocketIO, emit, send
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'alichat_gizli_anahtar'

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')

DB_FILE = 'alichat.db'

# --- VERİTABANI KURULUMU ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Kullanıcılar tablosu (id, kullanıcı adı, şifre)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# --- SAYFA YÖNLENDİRMELERİ ---

@app.route('/')
def index():
    # Eğer kullanıcı giriş yapmadıysa doğrudan Login sayfasına yönlendir
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', username=session['username'])

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')
        
        if not username or not password:
            return render_template('register.html', error="Lütfen tüm alanları doldurun.")
        
        # Şifreyi güvenli bir şekilde hash'liyoruz
        hashed_password = generate_password_hash(password)
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, hashed_password))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            # Eğer kullanıcı adı veritabanında zaten varsa bu hata tetiklenir
            conn.close()
            return render_template('register.html', error="Bu kullanıcı adı zaten alınmış!")
            
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')
        
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT password FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        
        if user and check_password_hash(user[0], password):
            session['username'] = username # Oturumu başlat
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error="Hatalı kullanıcı adı veya şifre!")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None) # Oturumu kapat
    return redirect(url_for('login'))

# --- SOHBET (SOCKET) OLAYLARI ---

@socketio.on('message')
def handle_message(msg):
    send(msg, broadcast=True)

@socketio.on('audio_message')
def handle_audio_message(data):
    emit('audio_message', data, broadcast=True)

@socketio.on('image_message')
def handle_image_message(data):
    emit('image_message', data, broadcast=True)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
