from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from models import (init_db, create_user, authenticate_user, get_user_by_id, 
                   save_message, get_messages_between_users, get_all_users_except,
                   update_user_online_status)
import sqlite3

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'vulnerable_secret_key_123'  # Intentionally weak

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")  # Vulnerable: allows any origin

# Store active connections (in production, use Redis or database)
active_users = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat')
def chat():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Get all other users for the user list
    other_users = get_all_users_except(session['user_id'])
    return render_template('chat.html', users=other_users)

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
            
            # Update online status
            update_user_online_status(user['id'], 1)
            
            return redirect(url_for('chat'))
        else:
            flash('Invalid credentials')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    if 'user_id' in session:
        update_user_online_status(session['user_id'], 0)
    session.clear()
    return redirect(url_for('index'))

# API endpoint to get messages between users
@app.route('/api/messages/<int:other_user_id>')
def get_messages(other_user_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    messages = get_messages_between_users(session['user_id'], other_user_id)
    return jsonify(messages)

# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    if 'user_id' in session:
        user_id = session['user_id']
        display_name = session['display_name']
        
        # Store the connection
        active_users[request.sid] = {
            'user_id': user_id,
            'display_name': display_name
        }
        
        # Update online status
        update_user_online_status(user_id, 1)
        
        print(f'User {display_name} connected')
        
        # Broadcast to all users that someone came online
        emit('user_status_update', {
            'user_id': user_id,
            'display_name': display_name,
            'status': 'online'
        }, broadcast=True)
        
        emit('status', {'msg': f'Connected as {display_name}'})
    else:
        print('Unauthenticated user tried to connect')
        emit('status', {'msg': 'Authentication required'})

@socketio.on('disconnect')
def handle_disconnect():
    if request.sid in active_users:
        user_info = active_users[request.sid]
        user_id = user_info['user_id']
        display_name = user_info['display_name']
        
        # Remove from active users
        del active_users[request.sid]
        
        # Update online status
        update_user_online_status(user_id, 0)
        
        print(f'User {display_name} disconnected')
        
        # Broadcast to all users that someone went offline
        emit('user_status_update', {
            'user_id': user_id,
            'display_name': display_name,
            'status': 'offline'
        }, broadcast=True)

@socketio.on('send_message')
def handle_message(data):
    if 'user_id' not in session:
        emit('error', {'msg': 'Not authenticated'})
        return
    
    sender_id = session['user_id']
    sender_name = session['display_name']
    receiver_id = data.get('receiver_id')
    message_content = data.get('message')
    
    if not receiver_id or not message_content:
        emit('error', {'msg': 'Invalid message data'})
        return
    
    # VULNERABILITY: No input sanitization on message content
    # VULNERABILITY: No rate limiting on messages
    
    # Save message to database
    if save_message(sender_id, receiver_id, message_content):
        # Create message object to send
        message_data = {
            'sender_id': sender_id,
            'sender_name': sender_name,
            'receiver_id': receiver_id,
            'content': message_content,
            'sent_at': 'now'  # In real app, use proper timestamp
        }
        
        # Send to sender (confirmation)
        emit('message_received', message_data)
        
        # Send to receiver if they're online
        # Find receiver's socket ID
        receiver_sid = None
        for sid, user_info in active_users.items():
            if user_info['user_id'] == receiver_id:
                receiver_sid = sid
                break
        
        if receiver_sid:
            socketio.emit('message_received', message_data, room=receiver_sid)
        
        print(f"Message from {sender_name} to user {receiver_id}: {message_content}")
    else:
        emit('error', {'msg': 'Failed to save message'})

@socketio.on('typing')
def handle_typing(data):
    """Handle typing indicators"""
    if 'user_id' not in session:
        return
    
    sender_id = session['user_id']
    sender_name = session['display_name']
    receiver_id = data.get('receiver_id')
    is_typing = data.get('is_typing', False)
    
    # Find receiver's socket ID and notify them
    for sid, user_info in active_users.items():
        if user_info['user_id'] == receiver_id:
            socketio.emit('user_typing', {
                'sender_id': sender_id,
                'sender_name': sender_name,
                'is_typing': is_typing
            }, room=sid)
            break

# Initialize database when app starts
if __name__ == '__main__':
    init_db()
    socketio.run(app, debug=True, host='0.0.0.0', port=5001)