from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import sqlite3
import os

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'vulnerable_secret_key_123'  # Intentionally weak

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")  # Vulnerable: allows any origin

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat')
def chat():
    return render_template('chat.html')

# Test WebSocket connection
@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('status', {'msg': 'Connected to server'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)