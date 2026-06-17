import os
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, send

app = Flask(__name__)
app.config['SECRET_KEY'] = 'alichat_gizli_anahtar'

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')

# Engellenen IP adreslerinin tutulacağı liste
BANNED_IPS = set()

# Basit yapay zeka/küfür kontrol listesi (Burayı istediğin gibi genişletebilirsin)
BAD_WORDS = ["küfür1", "küfür2", "argo1", "aptal", "salak", "piç", "oç"]

# Kullanıcıların IP adreslerini takip etmek için (İsim: IP) map'i
user_ips = {}

@app.route('/')
def index():
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if user_ip in BANNED_IPS:
        return "<h1>Giriş Engellendi!</h1><p>Kuralları ihlal ettiğiniz için bu sohbetten uzaklaştırıldınız.</p>", 403
    return render_template('index.html')

# --- ADMİN KONTROL PANELİ ---
@app.route('/admin')
def admin_panel():
    return render_template('admin.html')

@app.route('/api/banned-ips', methods=['GET'])
def get_banned_ips():
    return jsonify(list(BANNED_IPS))

@app.route('/api/unban', methods=['POST'])
def unban_ip():
    data = request.json
    ip_to_unban = data.get('ip')
    if ip_to_unban in BANNED_IPS:
        BANNED_IPS.remove(ip_to_unban)
        return jsonify({"success": True, "message": f"{ip_to_unban} engel kaldırıldı."})
    return jsonify({"success": False, "message": "IP bulunamadı."})
# ----------------------------

@socketio.on('connect')
def handle_connect():
    # Kullanıcının gerçek IP adresini alıyoruz (Render arkasında olduğu için X-Forwarded-For)
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if user_ip in BANNED_IPS:
        return False # Bağlantıyı reddet

@socketio.on('register_ip')
def handle_ip_registration(data):
    nickname = data.get('nickname', '').strip()
    user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if nickname:
        user_ips[nickname] = user_ip

@socketio.on('message')
def handle_message(msg):
    send(msg, broadcast=True)

@socketio.on('submit_report')
def handle_report(data):
    reported_text = data.get('text', '')
    
    # Yapay zeka / Küfür analizi simülasyonu
    is_offensive = False
    lower_text = reported_text.lower()
    for word in BAD_WORDS:
        if word in lower_text:
            is_offensive = True
            break
            
    if is_offensive:
        # Mesajı yazan kullanıcıyı tespit etmeye çalışalım (Format: "İsim: Mesaj")
        separator_index = reported_text.indexOf(':') if hasattr(reported_text, 'indexOf') else reported_text.find(':')
        if separator_index != -1:
            sender_name = reported_text[:separator_index].strip()
            target_ip = user_ips.get(sender_name)
            
            if target_ip:
                BANNED_IPS.add(target_ip)
                socketio.emit('report_result', {"status": "banned", "message": f"Küfür tespit edildi! {sender_name} adlı kullanıcı engellendi."})
                return
                
        socketio.emit('report_result', {"status": "success", "message": "Küfür tespit edildi ve işlem yapıldı!"})
    else:
        socketio.emit('report_result', {"status": "clear", "message": "Yapay Zeka Analizi: Mesaj temiz, herhangi bir küfür bulunamadı."})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
