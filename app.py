import os
from flask import Flask, render_template
from flask_socketio import SocketIO, send

app = Flask(__name__)
app.config['SECRET_KEY'] = 'alichat_gizli_anahtar'
# Canlı sunucularda WebSocket bağlantısının kopmaması için async_mode belirledik
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

@app.route('/')
def index():
    # Tarayıcı açıldığında HTML sayfasını yükler
    return render_template('index.html')

@socketio.on('message')
def handle_message(msg):
    print(f"Gelen Mesaj: {msg}")
    # Gelen mesajı, bağlı olan TÜM tarayıcılara geri gönderir
    send(msg, broadcast=True)

if __name__ == '__main__':
    # Render veya diğer platformların verdiği dinamik portu oku, yoksa 5000 portunu kullan
    port = int(os.environ.get("PORT", 5000))
    # host='0.0.0.0' yaparak dış dünyaya erişim izni verdik
    socketio.run(app, host='0.0.0.0', port=port, debug=False)