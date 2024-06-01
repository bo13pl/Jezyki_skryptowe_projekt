from flask import Flask, render_template, request, redirect, send_from_directory, url_for, jsonify, session
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet
import os
import json
import threading
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///users.db')
db = SQLAlchemy(app)
migrate = Migrate(app, db)
socketio = SocketIO(app, cors_allowed_origins="*")

# Generate a key for encryption if not already present
encryption_key_path = 'encryption_key.key'
if not os.path.exists(encryption_key_path):
    key = Fernet.generate_key()
    with open(encryption_key_path, 'wb') as key_file:
        key_file.write(key)
else:
    with open(encryption_key_path, 'rb') as key_file:
        key = key_file.read()
cipher_suite = Fernet(key)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    birthdate = db.Column(db.Date, nullable=True)
    gender = db.Column(db.String(10), nullable=True)

    def __init__(self, username, password, birthdate=None, gender=None):
        self.username = username
        self.password = generate_password_hash(password)
        self.last_activity = datetime.utcnow()
        self.birthdate = birthdate
        self.gender = gender

# Create tables
with app.app_context():
    db.create_all()

# Path to store encrypted messages
messages_file_path = 'forum_messages.json'

def read_messages():
    if os.path.exists(messages_file_path):
        with open(messages_file_path, 'rb') as file:
            encrypted_data = file.read()
            if encrypted_data:
                decrypted_data = cipher_suite.decrypt(encrypted_data)
                return json.loads(decrypted_data.decode('utf-8'))
    return {}

def write_messages(messages):
    with open(messages_file_path, 'wb') as file:
        encrypted_data = cipher_suite.encrypt(json.dumps(messages).encode('utf-8'))
        file.write(encrypted_data)

@app.before_request
def update_last_activity():
    if 'username' in session:
        user = User.query.filter_by(username=session['username']).first()
        if user:
            user.last_activity = datetime.utcnow()
            db.session.commit()

@app.route('/profile/<username>', methods=['GET', 'POST'])
def profile(username):
    user = User.query.filter_by(username=username).first()
    if not user:
        return "User not found", 404
    
    is_owner = session.get('username') == username
    name_incorrect = False

    if request.method == 'POST' and is_owner:
        new_username = request.form.get('username')
        new_password = request.form.get('password')
        new_birthdate = request.form.get('birthdate')
        new_gender = request.form.get('gender')

        if new_username and (new_username != user.username):
            existing_user = User.query.filter_by(username=new_username).first()
            if existing_user:
                name_incorrect = True
            else:
                user.username = new_username
                session['username'] = new_username

        if new_password:
            user.password = generate_password_hash(new_password)
        if new_birthdate:
            user.birthdate = datetime.strptime(new_birthdate, '%Y-%m-%d').date()
        if new_gender:
            user.gender = new_gender

        db.session.commit()

        if name_incorrect:
            return render_template('profile.html', user=user, is_owner=is_owner, name_incorrect=name_incorrect)

        return redirect(url_for('profile', username=user.username))

    return render_template('profile.html', user=user, is_owner=is_owner, name_incorrect=name_incorrect, my_name=session.get('username'))

@app.route('/')
def home():
    active_users = User.query.filter_by(is_active=True).all()
    if 'username' in session:
        user = User.query.filter_by(username=session['username']).first()
        if user:
            user.last_activity = datetime.utcnow()
            db.session.commit()
            return render_template('home_logged_in.html', 
                                   username=session['username'], 
                                   active_users=[{'username': user.username, 'profile_url': url_for('profile', username=user.username)} for user in active_users])
        else:
            return render_template('home_not_logged_in.html', active_user_count=len(active_users))
    return render_template('home_not_logged_in.html', active_user_count=len(active_users))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['username'] = username
            user.is_active = True
            user.last_activity = datetime.utcnow()
            db.session.commit()
            return redirect(url_for('home'))
        else:
            error = 'Invalid username or password. Please try again.'
            return render_template('login.html', error=error)

    return render_template('login.html')

@app.route('/logout')
def logout():
    if 'username' in session:
        user = User.query.filter_by(username=session['username']).first()
        if user:
            user.is_active = False
            user.last_activity = datetime.utcnow()
            db.session.commit()
        session.pop('username', None)
    return redirect(url_for('home'))

@app.route('/index')
def index():
    if 'username' in session:
        active_users = User.query.filter_by(is_active=True).all()
        current_user = User.query.filter_by(username=session['username']).first()
        if current_user:
            current_user.last_activity = datetime.utcnow()
            db.session.commit()
            return render_template('index.html', 
                                   username=session['username'], 
                                   active_users=[{'username': user.username, 'profile_url': url_for('profile', username=user.username)} for user in active_users])
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if User.query.filter_by(username=username).first():
            error = 'Username already exists. Please choose a different username.'
            return render_template('register.html', error=error)

        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()

        session['username'] = username
        return redirect(url_for('home'))

    return render_template('register.html')
@app.route('/forum', methods=['GET', 'POST'])
def forum():
    if 'username' in session:
        selected_forum = request.args.get('selected_forum', 'Forum1')
        messages = read_messages()

        if request.method == 'POST':
            message = request.form['message']
            username = session['username']
            
            if selected_forum not in messages:
                messages[selected_forum] = []
            
            messages[selected_forum].append((username, message))
            write_messages(messages)
            return '', 204  

        forum_messages = messages.get(selected_forum, [])

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return render_template('forum_partial.html', messages=[{'username': username, 'profile_url': url_for('profile', username=username), 'message':message} for username, message in forum_messages])
        else:
            return render_template('forum.html',
                    user={'username': session.get('username'), 'profile_url': url_for('profile', username=session.get('username'))},
                    messages=[{'username': username, 'profile_url': url_for('profile', username=username), 'message': message} for username, message in forum_messages],
                    selected_forum=selected_forum)

    return render_template('not_logged_in.html')

@socketio.on('connect')
def handle_connect():
    if 'username' in session:
        user = User.query.filter_by(username=session['username']).first()
        if user:
            user.is_active = True
            join_room(user.username)
            user.last_activity = datetime.utcnow()
            db.session.commit()

@socketio.on('message')
def handle_message(data):
    if 'username' in session:
        recipient = data.get('recipient')
        message = data['message']
        sender = session['username']
        user = User.query.filter_by(username=session['username']).first()
        if user:
            user.last_activity = datetime.utcnow()
            db.session.commit()
            messages = read_messages()
            if recipient == 'all':
                messages.setdefault('all', []).append((sender, message))
                write_messages(messages)
                socketio.emit('new_message', {'username': sender, 'message': message}, room='all')
            else:
                recipient_user = User.query.filter_by(username=recipient).first()
                if recipient_user and recipient_user.is_active:
                    emit('message', {'message': message, 'username': sender}, room=recipient_user.username)
                else:
                    emit('message', {'message': f'User {recipient} is not online', 'username': 'System'})

@socketio.on('check_inactivity')
def check_inactivity():
    while True:
        with app.app_context():
            now = datetime.utcnow()
            inactive_warning_users = User.query.filter(
                User.is_active == True,
                User.last_activity < now - timedelta(minutes=30),
            ).all()
            sended =[]
            for user in inactive_warning_users:
                if user not in sended:
                    sended.append(user)
                    socketio.emit('inactive_warning', {'message': f'You, {user.username}, will be logged out due to inactivity in 1 minute'}, room=user.username)

            time.sleep(60)

            inactive_users = User.query.filter(
                User.is_active == True,
                User.last_activity < now - timedelta(minutes=30)
            ).all()

            for user in inactive_users:
                if user.is_active:
                    user.is_active = False
                    db.session.commit()
                    leave_room(user.username)

@app.route('/forum/<username1>/<username2>', methods=['GET', 'POST'])
def chat_priv(username1, username2):
    # Sort usernames to ensure consistent URL structure
    sorted_usernames = sorted([username1, username2])
    if (username1, username2) != (sorted_usernames[0], sorted_usernames[1]):
        return redirect(url_for('chat_priv', username1=sorted_usernames[0], username2=sorted_usernames[1]))

    user1 = User.query.filter_by(username=sorted_usernames[0]).first()
    user2 = User.query.filter_by(username=sorted_usernames[1]).first()
    
    if not user1 or not user2:
        return "User not found", 404
    
    current_username = session.get('username')
    is_owner = current_username in sorted_usernames
    
    if not is_owner:
        return render_template('not_logged_in.html'), 403
    
    selected_forum = request.args.get(f'selected_forum_{sorted_usernames[0]}_{sorted_usernames[1]}', f'selected_forum_{sorted_usernames[0]}_{sorted_usernames[1]}')
    messages = read_messages()

    if request.method == 'POST':
        message = request.form['message']
        
        if selected_forum not in messages:
            messages[selected_forum] = []
        
        messages[selected_forum].append((current_username, message))
        write_messages(messages)
        return '', 204  # No Content

    forum_messages = messages.get(selected_forum, [])

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template('forum_partial.html', messages=[
            {'username': username, 'profile_url': url_for('profile', username=username), 'message': message}
            for username, message in forum_messages
        ])
    else:
        return render_template('forum.html',
                               user={'username': current_username, 'profile_url': url_for('profile', username=current_username)},
                               messages=[
                                   {'username': username, 'profile_url': url_for('profile', username=username), 'message': message}
                                   for username, message in forum_messages
                               ],
                               selected_forum=selected_forum)

if __name__ == '__main__':
    thread = threading.Thread(target=check_inactivity)
    thread.daemon = True
    thread.start()  
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)