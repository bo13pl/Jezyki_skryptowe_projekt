from flask_socketio import SocketIO, emit, join_room
from flask import session
import random

socketio = SocketIO()

# Poker Game state
poker_game = {
    "players": {},
    "community_cards": [],
    "pot": 0,
    "current_bet": 0,
    "player_turn": None,
    "winner": None
}

def deal_cards():
    deck = [f"{rank} of {suit}" for suit in ['Hearts', 'Diamonds', 'Clubs', 'Spades'] for rank in list(range(2, 11)) + ['J', 'Q', 'K', 'A']]
    random.shuffle(deck)
    for player in poker_game["players"].values():
        player["hand"] = [deck.pop(), deck.pop()]

def determine_winner():
    if poker_game["players"]:
        poker_game["winner"] = random.choice(list(poker_game["players"].keys()))
    else:
        poker_game["winner"] = None

@socketio.on('join_poker_game')
def join_poker_game():
    username = session.get('username')
    if username:
        if username not in poker_game["players"]:
            poker_game["players"][username] = {
                "hand": [],
                "chips": 1000,
                "current_bet": 0
            }
        poker_game["player_turn"] = list(poker_game["players"].keys())[0]
        join_room('poker_room')
        emit('game_state', poker_game, room='poker_room')

@socketio.on('deal_cards')
def on_deal_cards():
    deal_cards()
    emit('game_state', poker_game, room='poker_room')

@socketio.on('place_bet')
def on_place_bet(data):
    username = session.get('username')
    amount = data.get('amount')
    if username and amount:
        player = poker_game["players"].get(username)
        if player and player["chips"] >= amount:
            player["chips"] -= amount
            player["current_bet"] += amount
            poker_game["pot"] += amount
            poker_game["current_bet"] = max(poker_game["current_bet"], player["current_bet"])
            player_turns = list(poker_game["players"].keys())
            current_index = player_turns.index(poker_game["player_turn"])
            poker_game["player_turn"] = player_turns[(current_index + 1) % len(player_turns)]
        emit('game_state', poker_game, room='poker_room')

@socketio.on('determine_winner')
def on_determine_winner():
    determine_winner()
    emit('game_state', poker_game, room='poker_room')
