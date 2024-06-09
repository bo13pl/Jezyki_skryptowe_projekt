from asyncio.windows_events import NULL
from flask import Flask, render_template, request, redirect, flash, url_for, jsonify, session
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet
from Tici_tac import TicTacToe, ai_move_smurt
from blackjack import Game
import os
import json
import threading
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///users.db')
db = SQLAlchemy(app)
app.static_folder = 'templates'
app.static_folder = 'templates\cards'
app.static_folder = 'static'
migrate = Migrate(app, db)
socketio = SocketIO(app, cors_allowed_origins="*")

# Create tables
with app.app_context():
    db.create_all()

# Path to store encrypted messages
messages_file_path = 'forum_messages.json'

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
    money = db.Column(db.Integer, nullable=False)

    def __init__(self, username, password, birthdate=None, gender=None):
        self.username = username
        self.password = generate_password_hash(password)
        self.is_active = True
        self.last_activity = datetime.utcnow()
        self.birthdate = birthdate
        self.gender = gender
        self.money = 1000                           #start balance



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
        all_users = User.query.all()
        if current_user:
            current_user.last_activity = datetime.utcnow()
            db.session.commit()
            return render_template('index.html', 
                                   username=session['username'], 
                                   active_users=[{'username': user.username, 'profile_url': url_for('profile', username=user.username)} for user in active_users],
                                   all_users=[{'username': user.username, 'profile_url': url_for('profile', username=user.username)} for user in all_users])
    return render_template('not_logged_in.html')

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
                    socketio.emit('inactive_warning', {'message': f'You, {user.username}, will be logged out due to inactivity'}, room=user.username)

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
    if 'username' not in session:
        return render_template('not_logged_in.html')
    # Sort usernames to ensure consistent URL structure
    sorted_usernames = sorted([username1, username2])
    if (username1, username2) != (sorted_usernames[0], sorted_usernames[1]):
        return redirect(url_for('chat_priv', username1=sorted_usernames[0], username2=sorted_usernames[1]))

    user1 = User.query.filter_by(username=sorted_usernames[0]).first()
    user2 = User.query.filter_by(username=sorted_usernames[1]).first()
    user1.last_activity = datetime.utcnow()
    user2.last_activity = datetime.utcnow()
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

games = []

def find_latest_game_by_player(player_name):
    filtered_games = [game for game in games if game['player'] == player_name]
    if not filtered_games:
        return None
    filtered_games.sort(key=lambda x: x['datet'], reverse=True)
    return filtered_games[0]

@app.route('/blackjack/start_game', methods=['POST'])
def start_game():
    if 'username' not in session:
        return render_template('not_logged_in.html')
    
    money = int(request.form.get('money')) if request.form.get('money') is not None or not '' else 0
    current_user = User.query.filter_by(username=session['username']).first()
    user = session['username']
    current_user.last_activity = datetime.utcnow()
    print(request.form.get('money'))
    if money==0 or money == NULL:
        db.session.commit()
        return render_template('blackjack.html', user_name=user, user_profile_url = url_for('profile', username=user), im_money=False, user_money = current_user.money)
    else:
        user = session['username']
        current_user = User.query.filter_by(username=session['username']).first()
        current_user.last_activity = datetime.utcnow()


        current_user.money-=money
        game_session = {'game': Game(), 'datet': datetime.utcnow(), 'player': user, 'winner': [], 'hands': 1}
        games.append(game_session)
        
        game = game_session['game']
        game.clear_hands()
        game.deal_initial_cards()
        session['game'] = game.to_dict()
        game_session['standed_hands'] = 1

        player_winners = [winner for winner in game_session['winner'] if 'Player' in winner]


        if game.is_blackjack(game.player_hands[0]):
            current_user.money+=money*2.5
            game_session['winner'].append(f'Hand 1 win Player')
            games.remove(game_session)
            db.session.commit()
            return render_template('blackjack.html', user_name=user, player_hands=[{'hand':card.get_cards(), 'value': card.get_value()} for card in game.player_hands], dealer=game.dealer_hand.value, dealer_hand=game.dealer_hand.get_cards(),
                                winner=game_session['winner'], is_winner=bool(game_session['winner']), enumerate=enumerate, num_of_hands=len(game_session['winner']), user_profile_url=url_for('profile', username=user), user_money=current_user.money,
                                  im_money=True, bet = money)
        db.session.commit()
        return render_template('blackjack.html', user_name=user, player_hands=[{'hand':card.get_cards(), 'value': card.get_value()} for card in game.player_hands], dealer=game.dealer_hand.value,
                                dealer_hand=game.dealer_hand.get_cards(), enumerate=enumerate, num_of_hands=len(game_session['winner']), user_profile_url=url_for('profile', username=user),
                                  user_money=current_user.money, im_money=True, bet = money)


@app.route('/blackjack', methods=['GET', 'POST'])
def blackjack():
    if 'username' not in session:
        return render_template('not_logged_in.html')
        
    user = session['username']
    current_user = User.query.filter_by(username=session['username']).first()
    current_user.last_activity = datetime.utcnow()
    db.session.commit()

    money = int(request.form.get('money')) if request.form.get('money') is not None else 0
    print(money)
    if current_user.money<=10:
        return  redirect(url_for('topup'))
    elif money==0 or money == NULL:
        db.session.commit()
        return render_template('blackjack.html', user_name=user, user_profile_url = url_for('profile', username=user), im_money=False, user_money = current_user.money, bet = money)
    else:
        game_session = {'game': Game(), 'datet': datetime.utcnow(), 'player': user, 'winner': [], 'hands': 1}
        games.append(game_session)
        game = game_session['game']
        game.clear_hands()
        game.deal_initial_cards()
        session['game'] = game.to_dict()
        game_session['standed_hands'] = 1
        if game.is_blackjack(game.player_hands[0]):
            game_session['winner'].append(f'Hand 1 win Player')
            games.remove(game_session)
            db.session.commit()
            return render_template('blackjack.html', user_name=user, player_hands=[{'hand':card.get_cards(), 'value': card.get_value()} for card in game.player_hands], dealer=game.dealer_hand.value, dealer_hand=game.dealer_hand.get_cards(),
                            winner=game_session['winner'], is_winner=bool(game_session['winner']), enumerate=enumerate, num_of_hands = len(game_session['winner']), user_profile_url = url_for('profile', username=user), user_money = current_user.money, im_money=True, bet = money)
        db.session.commit()
        return render_template('blackjack.html', user_name=user, player_hands=[{'hand':card.get_cards(), 'value': card.get_value()} for card in game.player_hands], dealer=game.dealer_hand.value,
                                dealer_hand=game.dealer_hand.get_cards(), enumerate=enumerate, num_of_hands = len(game_session['winner']), user_profile_url = url_for('profile', username=user), user_money = current_user.money, im_money=True, bet = money)

@app.route('/blackjack/hit', methods=['POST'])
def blackjack_hit():
    if 'username' not in session:
        return render_template('not_logged_in.html')
    user = session['username']
    current_user = User.query.filter_by(username=session['username']).first()
    current_user.last_activity = datetime.utcnow()
    db.session.commit()
    money = int(request.form.get('money')) if request.form.get('money') is not None else 0
    hand_index = int(request.form.get('hand_index', 0))
    game_session = find_latest_game_by_player(user)
    if 'game' in game_session:
        game = game_session['game']
        if game.get_player_turn_ended() and len(game_session['winner']) == game_session['hands']:
            db.session.commit()
            return render_template('blackjack.html', user_name=user, player_hands=[{'hand':card.get_cards(), 'value': card.get_value()} for card in game.player_hands], dealer=game.dealer_hand.value,
                                    dealer_hand=game.dealer_hand.get_cards(), enumerate=enumerate, num_of_hands = len(game_session['winner']), user_profile_url = url_for('profile', username=user), user_money = current_user.money, im_money=True, bet = money)
            
        game.hit(game.player_hands[hand_index])
        if game.is_bust(game.player_hands[hand_index]):
            game_session['winner'].append(f'Hand {hand_index + 1} win Dealer')
            if game.get_player_turn_ended() and len(game_session['winner']) == game_session['hands']:
                games.remove(game_session) 
        elif game.is_blackjack(game.player_hands[hand_index]):
            game_session['winner'].append(f'Hand {hand_index + 1} win Player')
            if game.get_player_turn_ended() and len(game_session['winner']) == game_session['hands']:
                games.remove(game_session) 

        
            
 # Clear the game session after finishing
        db.session.commit()
        return render_template('blackjack.html', user_name=user, player_hands=[{'hand':card.get_cards(), 'value': card.get_value()} for card in game.player_hands], dealer=game.dealer_hand.value, dealer_hand=game.dealer_hand.get_cards(),
                                    winner=game_session['winner'], is_winner=bool(game_session['winner']), enumerate=enumerate, num_of_hands = len(game_session['winner']), user_profile_url = url_for('profile', username=user), user_money = current_user.money, im_money=True, bet = money)

@app.route('/blackjack/stand', methods=['POST'])
def blackjack_stand():
    if 'username' not in session:
        return render_template('not_logged_in.html')
    user = session['username']
    current_user = User.query.filter_by(username=session['username']).first()
    current_user.last_activity = datetime.utcnow()
    db.session.commit()
    money = int(request.form.get('money')) if request.form.get('money') is not None else 0
    game_session = find_latest_game_by_player(user)
    if 'game' in game_session:
        game = game_session['game']
        game_session['standed_hands'] += 1
        # Check if the player's turn has ended
        if game.get_player_turn_ended() and len(game_session['winner']) == game_session['hands']:
            db.session.commit()
            return render_template('blackjack.html', user_name=user, player_hands=[{'hand':card.get_cards(), 'value': card.get_value()} for card in game.player_hands], dealer=game.dealer_hand.value,
                                    dealer_hand=game.dealer_hand.get_cards(), enumerate=enumerate, num_of_hands = len(game_session['winner']), user_profile_url = url_for('profile', username=user), user_money = current_user.money, im_money=True, bet = money)
        
        game.dealer_plays()
        winners = game.check_winner()  # Assuming only one hand for simplicity
        if winners:
            game_session['winner'] = winners
            games.remove(game_session)  # Clear the game session after finishing
        player_winners = [winner for winner in game_session['winner'] if 'Player' in winner]
        current_user.money += money * len(player_winners)*2
        player_tie = [winner for winner in game_session['winner'] if 'Tie' in winner]
        current_user.money += money * len(player_tie)
        db.session.commit()
        return render_template('blackjack.html', user_name=user, player_hands=[{'hand':card.get_cards(), 'value': card.get_value()} for card in game.player_hands], dealer=game.dealer_hand.value,
                                dealer_hand=game.dealer_hand.get_cards(), winner=game_session['winner'], is_winner=bool(game_session['winner']),
                                enumerate=enumerate, num_of_hands = len(game_session['winner']), user_profile_url = url_for('profile', username=user), user_money = current_user.money, im_money=True, bet = money)

@app.route('/blackjack/split', methods=['POST'])
def blackjack_split():
    if 'username' not in session:
        return render_template('not_logged_in.html')
    user = session['username']
    current_user = User.query.filter_by(username=session['username']).first()
    current_user.last_activity = datetime.utcnow()
    db.session.commit()
    money = int(request.form.get('money')) if request.form.get('money') is not None else 0

    current_user.money-=money
    db.session.commit()
    game_session = find_latest_game_by_player(user)
    if 'game' in game_session:
        game = game_session['game']
        try:
            game.split_hand(0)
        except ValueError as e:
            db.session.commit()
            return render_template('blackjack.html', user_name=user, player_hands=[{'hand':card.get_cards(), 'value': card.get_value()} for card in game.player_hands], dealer=game.dealer_hand.value, dealer_hand=game.dealer_hand.get_cards(),
                                error=str(e), enumerate=enumerate, num_of_hands = len(game_session['winner']), user_profile_url = url_for('profile', username=user), user_money = current_user.money, im_money=True, bet = money)
        game_session['standed_hands'] *= 2
        session['game'] = game.to_dict()
        db.session.commit()
        return render_template('blackjack.html', user_name=user, player_hands=[{'hand':card.get_cards(), 'value': card.get_value()} for card in game.player_hands], dealer=game.dealer_hand.value,
                                dealer_hand=game.dealer_hand.get_cards(), enumerate=enumerate, num_of_hands = len(game_session['winner']), user_profile_url = url_for('profile', username=user), user_money = current_user.money, im_money=True, bet = money)
games_tici_tac = {}

@app.route('/tictactoe')
def tictactoe():
    if 'username' not in session:
        return render_template('not_logged_in.html')
    current_user = User.query.filter_by(username=session['username']).first()
    current_user.last_activity = datetime.utcnow()
    db.session.commit()
    return render_template('tictactoe.html')
@socketio.on('join_game')
def join_game(data):
    if 'username' not in session:
        emit('redirect', {'url': url_for('login')})
        return
    
    current_user = User.query.filter_by(username=session['username']).first()
    current_user.last_activity = datetime.utcnow()
    db.session.commit()
    game_id = data['game_id']
    sid = session['username']
    

    if game_id not in games_tici_tac:
        games_tici_tac[game_id] = TicTacToe()
    game = games_tici_tac[game_id]
    
    if game_id.startswith('ai'):
        letter = game.add_player(sid)

        join_room(game_id)
        
        emit('game_started', {'board': game.board, 'current_turn': game.current_turn}, room=game_id)
    else:
        if not game.add_player(sid):
            emit('no_permission', room=sid)
            return
        
        letter = game.add_player(sid)
        if letter:
            join_room(game_id)
            emit('game_started', {'board': game.board, 'letter': letter, 'current_turn': game.current_turn}, room=sid)
        else:
            emit('game_full', room=sid)

@socketio.on('make_move')
def handle_make_move(data):
    if 'username' not in session:
        emit('redirect', {'url': url_for('login')})
        return
    
    current_user = User.query.filter_by(username=session['username']).first()
    current_user.last_activity = datetime.utcnow()
    db.session.commit()
    game_id = data['game_id']
    move = data['move']
    sid = session['username']
    
    print("start making move")
    game = games_tici_tac.get(game_id)
    
    if game:
        print("pass 0")
        if game_id.startswith('ai'):
            print("pass 1")
            if game.make_move(move, sid):
                print("pass 2")
                emit('move_made', {'board': game.board, 'move': move, 'letter': game.players[sid], 'current_turn': game.current_turn}, room=game_id)
                print(game_id)
                if game.current_winner:
                    emit('game_won', {'winner': game.current_winner}, room=game_id)
                elif ' ' not in game.board:
                    emit('game_tied', room=game_id)
                else:
                    print("start to decide")
                    if game.players[sid] == 'X':
                        player_ai = 'O'
                    elif game.players[sid] == 'O':
                        player_ai = 'X'
                    ai_move_result = ai_move_smurt(game, player_ai)
                    
                    emit('move_made', {'board': game.board, 'move': ai_move_result, 'letter': player_ai, 'current_turn': game.current_turn}, room=game_id)
                    print(game_id)
                    print("finish to decide", ai_move_result)
                    if game.current_winner:
                        emit('game_won', {'winner': game.current_winner}, room=game_id)
                    elif ' ' not in game.board:
                        emit('game_tied', room=game_id)
            elif game.is_empty_board():
                print("start to decide")
                if game.players[sid] == 'X':
                    player_ai = 'O'
                elif game.players[sid] == 'O':
                    player_ai = 'X'
                ai_move_result = ai_move_smurt(game, player_ai)
                    
                emit('move_made', {'board': game.board, 'move': ai_move_result, 'letter': player_ai, 'current_turn': game.current_turn}, room=game_id)
                print(game_id)
                print("finish to decide", ai_move_result)
                if game.current_winner:
                    emit('game_won', {'winner': game.current_winner}, room=game_id)
                elif ' ' not in game.board:
                    emit('game_tied', room=game_id)
        else:
            if game.make_move(move, sid):
                emit('move_made', {'board': game.board, 'move': move, 'letter': game.players[sid], 'current_turn': game.current_turn}, room=game_id)
                if game.current_winner:
                    emit('game_won', {'winner': game.current_winner}, room=game_id)
                elif ' ' not in game.board:
                    emit('game_tied', room=game_id)
            else:
                emit('invalid_move', room=sid)


@socketio.on('replay_game')
def handle_replay_game(data):
    if 'username' not in session:
        return render_template('not_logged_in.html')
    current_user = User.query.filter_by(username=session['username']).first()
    current_user.last_activity = datetime.utcnow()
    game_id = data['game_id']
    game = games_tici_tac.get(game_id)
    if game:
        game.reset_game()
        emit('game_started', {'board': game.board, 'current_turn': game.current_turn}, room=game_id)

@socketio.on('leave_game')
def leave_game(data):
    if 'username' not in session:
        return render_template('not_logged_in.html')
    current_user = User.query.filter_by(username=session['username']).first()
    current_user.last_activity = datetime.utcnow()
    game_id = data['game_id']
    sid = session['username']
    if game_id in games_tici_tac:
        game = games_tici_tac[game_id]
        game.remove_player(sid)
        leave_room(game_id)
        if game.get_players_length() == 0:
            del games_tici_tac[game_id]  
        emit('left_game', room=sid)


@app.route('/topup', methods=['GET', 'POST'])
def topup():
    if 'username' not in session:
        return render_template('not_logged_in.html')
    user = session['username']
    current_user = User.query.filter_by(username=session['username']).first()
    current_user.last_activity = datetime.utcnow()
    
    if request.method == 'POST':
        amount = int(request.form.get('amount', 0))
        if amount > 0:
            current_user.money += amount
            db.session.commit()
            socketio.emit('topup_notification', {'message': 'Your money has been topped up.'}, room=current_user.id)
        else:
            socketio.emit('topup_notification', {'message': 'Your money has been not topped up.'}, room=current_user.id)

    return render_template('balance.html', user=current_user, user_name=user, user_profile_url = url_for('profile', username=user), im_money = current_user.money >10)

if __name__ == '__main__':
    thread = threading.Thread(target=check_inactivity)
    thread.daemon = True
    thread.start()  
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)