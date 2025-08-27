from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_socketio import SocketIO, emit
from models import init_db, create_user, authenticate_user, get_user_by_id
import sqlite3


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
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('chat.html')

# Test WebSocket connection
@socketio.on('connect')
def handle_connect():
    print('Client connected')
    emit('status', {'msg': 'Connected to server'})

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

# Add these routes before the socketio handlers

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email'] 
        password = request.form['password']
        display_name = request.form['display_name']
        
        # VULNERABILITY: No input validation
        if create_user(username, email, password, display_name):
            flash('Registration successful! Please log in.')
            return redirect(url_for('login'))
        else:
            flash('Registration failed. Username or email might already exist.')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = authenticate_user(username, password)
        if user:
            # VULNERABILITY: Session management is basic
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['display_name'] = user['display_name']
            return redirect(url_for('chat'))
        else:
            flash('Invalid credentials')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# Initialize database when app starts
if __name__ == '__main__':
    init_db()
    socketio.run(app, debug=True, host='0.0.0.0', port=5001)