from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import threading
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
socketio = SocketIO(app, cors_allowed_origins="*")

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow())  

    def __init__(self, username, password):
        self.username = username
        self.password = generate_password_hash(password)
        self.last_activity =datetime.utcnow()

# Create tables
with app.app_context():
    db.create_all()

# Dictionary to store messages for each forum
forum_messages = {}

@app.before_request
def update_last_activity():
    if 'username':
        if 'username' in session and User.query.filter_by(username=session['username']).first().is_active:
            user = User.query.filter_by(username=session['username']).first()
            if user:
                user.last_activity =datetime.utcnow()
                db.session.commit()

@app.route('/')
def home():
    if 'username':
        active_users = User.query.filter_by(is_active=True).all()
        user_logged = 'username' in session and User.query.filter_by(username=session['username']).first().is_active
        
        if user_logged:
            User.query.filter_by(username=session['username']).first().last_activity =datetime.utcnow()
            return render_template('home_logged_in.html', username=session['username'], active_users=active_users)
        else:
            return render_template('home_not_logged_in.html', active_user_count=len(active_users))
    else:
        return render_template('home_not_logged_in.html', active_user_count=len(active_users))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'username':
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']

            user = User.query.filter_by(username=username).first()

            if user and check_password_hash(user.password, password):
                session['username'] = username
                user.is_active = True
                user.last_activity =datetime.utcnow()
                db.session.commit()
                return redirect(url_for('home'))
            
            else:
                error = 'Invalid username or password. Please try again.'
                return render_template('login.html', error=error)
        
        return render_template('login.html')

@app.route('/logout')
def logout():
    if 'username':
        if 'username' in session and User.query.filter_by(username=session['username']).first().is_active:
            user = User.query.filter_by(username=session['username']).first()
            user.is_active = False
            db.session.commit()

            User.query.filter_by(username=session['username']).first().last_activity =datetime.utcnow()
            session.pop('username')
            session.pop('username', None)
        return redirect(url_for('home'))

@app.route('/index')
def index():
    if 'username':
        if 'username' not in session or not User.query.filter_by(username=session['username']).first().is_active:
            return redirect(url_for('login'))
        active_users = User.query.filter_by(is_active=True).all()
        User.query.filter_by(username=session['username']).first().last_activity =datetime.utcnow()
        return render_template('index.html', username=session['username'], active_users=[user.username for user in active_users])

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'username':
        user_logged = 'username' in session and User.query.filter_by(username=session['username']).first().is_active
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
    if 'username':
        user_logged = 'username' in session and User.query.filter_by(username=session['username']).first().is_active
        selected_forum = request.args.get('selected_forum', 'Forum1')
        
        if user_logged:
            if request.method == 'POST':
                message = request.form['message']
                username = session['username']
                
                if selected_forum not in forum_messages:
                    forum_messages[selected_forum] = []
                
                forum_messages[selected_forum].append((username, message))
                return '', 204  
            User.query.filter_by(username=session['username']).first().last_activity =datetime.utcnow()
            messages = forum_messages.get(selected_forum, [])
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return render_template('forum_partial.html', messages=messages)
            else:
                return render_template('forum.html', username=session.get('username'), messages=messages, selected_forum=selected_forum)
        else:
            return render_template('not_logged_in.html')

@socketio.on('connect')
def handle_connect():
    if 'username':
        if 'username' in session and User.query.filter_by(username=session['username']).first().is_active:
            user = User.query.filter_by(username=session['username']).first()
            user.is_active = True
            username = session['username']
            join_room(username)
            user.last_activity =datetime.utcnow()
            db.session.commit()

@socketio.on('message')
def handle_message(data):
    if 'username':
        if 'username' in session and User.query.filter_by(username=session['username']).first().is_active:
            recipient = data.get('recipient')
            message = data['message']
            sender = session['username']
            User.query.filter_by(username=session['username']).first().last_activity =datetime.utcnow()
            if recipient == 'all':
                forum_messages[recipient].append((sender, message))
                socketio.emit('new_message', {'username': sender, 'message': message}, room='all', namespace='/')
            elif recipient in User.query.filter_by(is_active=True).all():
                recipient_sid = User.query.filter_by(is_active=True).all()[recipient]
                emit('message', {'message': message, 'username': sender}, room=recipient_sid)
            else:
                emit('message', {'message': f'User {recipient} is not online', 'username': 'System'})


@socketio.on('check_inactivity')  # Listen for check_inactivity event from client
def check_inactivity():
    while True:
        with app.app_context():
            now = datetime.utcnow()
            # Find users who have been inactive for more than 4 minutes but less than 5 minutes
            inactive_warning_users = User.query.filter(
                User.is_active == True,
                User.last_activity < now - timedelta(minutes=1),
            ).all()
            # Send warnings to these users
            for user in inactive_warning_users:
                app.logger.info(f'Sending inactive warning to {user.username}')
                socketio.emit('inactive_warning', {'message': f'You, {user.username}, will be logged out due to inactivity in 1 minute'}, room=user.username)
                app.logger.info(f'Inactive warning sent to {user.username}')
            time.sleep(60)
            inactive_users = []
            for user in inactive_warning_users:
                if user.is_active == True and user.last_activity < now - timedelta(minutes=1):
                    inactive_users.append(user) 
            # Log out these users
            user_name_chec = ""
            for user in inactive_users:
                if(user.is_active):
                    socketio.emit('force_logout', {'message': f'You, {user.username}, have been logged out due to inactivity'}, room=user.username)
                    app.logger.info(f'User {user.username} logged out due to inactivity')
                    user.is_active = False
                    db.session.commit()

        # Sleep for 1 minute before running the check again
        time.sleep(60)
if __name__ == '__main__':
    thread = threading.Thread(target=check_inactivity)
    thread.daemon = True
    thread.start()  
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)