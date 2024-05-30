from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
socketio = SocketIO(app)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    def __init__(self, username, password):
        self.username = username
        self.password = generate_password_hash(password)

# Create tables
with app.app_context():
    db.create_all()

# Dictionary to store messages for each forum
forum_messages = {}

@app.route('/')
def home():
    active_users = User.query.filter_by(is_active=True).all()
    user_logged = 'username' in session
    
    if user_logged:
        return '''
        <h1>Welcome to our website, {}!</h1>
        <p>Active Users:</p>
        <ul>
            {}
        </ul>
        <p>Please choose an option:</p>
        <ul>
            <li><a href="/logout">Logout</a></li>
            <li><a href="/forum?selected_forum=Forum1">Forum1</a></li>
            <li><a href="/forum?selected_forum=Forum2">Forum2</a></li>
        </ul>
        '''.format(session['username'], ''.join([f'<li>{user.username}</li>' for user in active_users]))
    else:
        return '''
        <h1>Welcome to our website!</h1>
        <p>Please choose an option:</p>
        <ul>
            <li><a href="/login">Login</a></li>
            <li><a href="/register">Register</a></li>
        </ul>
        '''

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['username'] = username
            user.is_active = True 
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
        user.is_active = False  
        db.session.commit()  
        session.pop('username', None)
    return redirect(url_for('home'))


@app.route('/index')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', username=session['username'], active_users=User.query.filter_by(is_active=True).all())

@app.route('/register', methods=['GET', 'POST'])
def register():
    user_logged = 'username' in session
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
    user_logged = 'username' in session
    selected_forum = request.args.get('selected_forum', 'Forum1')
    
    if user_logged:
        if request.method == 'POST':
            message = request.form['message']
            username = session['username']
            
            if selected_forum not in forum_messages:
                forum_messages[selected_forum] = []
            
            forum_messages[selected_forum].append((username, message))
            return '', 204  
        
        messages = forum_messages.get(selected_forum, [])
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return render_template('forum_partial.html', messages=messages)
        else:
            return render_template('forum.html', username=session.get('username'), messages=messages, selected_forum=selected_forum)
    else:
        return '''
        <h1>Sorry you are not logged in</h1>
        <p>Please choose an option:</p>
        <ul>
            <li><a href="/login">Login</a></li>
            <li><a href="/register">Register</a></li>
        </ul>
        '''

@socketio.on('connect')
def handle_connect():
    if 'username' in session:
        user = User.query.filter_by(username=session['username']).first()
        user.is_active = True  
        db.session.commit()  

@socketio.on('message')
def handle_message(data):
    if 'username' in session:
        recipient = data.get('recipient')
        message = data['message']
        sender = session['username']
        
        if recipient == 'all':
            forum_messages[recipient].append((sender, message))
            socketio.emit('new_message', {'username': sender, 'message': message}, room='all', namespace='/')
        elif recipient in User.query.filter_by(is_active=True).all():
            recipient_sid = User.query.filter_by(is_active=True).all()[recipient]
            emit('message', {'message': message, 'username': sender}, room=recipient_sid)
        else:
            emit('message', {'message': f'User {recipient} is not online', 'username': 'System'})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
