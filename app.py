import os
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, send

app = Flask(__name__)
app.config['SECRET_KEY'] = 'alichat_gizli_anahtar'

socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('message')
def handle_message(msg):
    send(msg, broadcast=True)

@socketio.on('audio_message')
def handle_audio_message(data):
    emit('audio_message', data, broadcast=True)

# Gelen fotoğraf mesajını alıp odadaki herkese (broadcast) iletiyoruz
@socketio.on('image_message')
def handle_image_message(data):
    emit('image_message', data, broadcast=True)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
