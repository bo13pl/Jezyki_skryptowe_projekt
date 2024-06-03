import math
import copy
class TicTacToe:
    def __init__(self):
        self.board = [' '] * 9
        self.current_winner = None
        self.players = {}
        self.current_turn = 'X'

    def add_player(self, sid):
        player = self.players.get(sid)
        if player is not None:
            return player
        elif len(self.players) < 2:
            letter = 'X' if len(self.players) == 0 else 'O'
            self.players[sid] = letter
            return letter
        return None

    
    def get_players_length(self):
        return len(self.players)
    

    def remove_player(self, sid):
        if sid in self.players:
            del self.players[sid]
            if not any(player['letter'] == self.current_turn for player in self.players.values()):
                self.current_turn = None
            else:
                self.current_turn = self.players[0]
            
    def make_move(self, square, sid):
        letter = self.players.get(sid)
        if self.board[square] == ' ' and letter == self.current_turn:
            self.board[square] = letter
            if self.winner(square, letter):
                self.current_winner = letter
            self.current_turn = 'O' if letter == 'X' else 'X'
            return True
        return False

    def winner(self, square, letter):
        row_ind = square // 3
        row = self.board[row_ind*3:(row_ind+1)*3]
        if all([s == letter for s in row]):
            return True
        col_ind = square % 3
        column = [self.board[col_ind+i*3] for i in range(3)]
        if all([s == letter for s in column]):
            return True
        if square % 2 == 0:
            diagonal1 = [self.board[i] for i in [0, 4, 8]]
            if all([s == letter for s in diagonal1]):
                return True
            diagonal2 = [self.board[i] for i in [2, 4, 6]]
            if all([s == letter for s in diagonal2]):
                return True
        return False

    def available_moves(self):
        return [i for i, spot in enumerate(self.board) if spot == ' ']

    def empty_squares(self):
        return ' ' in self.board

    def num_empty_squares(self):
        return self.board.count(' ')

    def is_empty_board(self):
        return self.board.count(' ') == 9

    def reset_game(self):
        self.board = [' '] * 9
        self.current_winner = None
    
    def make_move_ai(self,move, player):
        self.board[move] = player
        if self.winner(move, player):
            self.current_winner = player
        self.current_turn = 'O' if player == 'X' else 'X'
    

def evaluate(board):
    # Check rows
    for i in range(0, 9, 3):
        if board[i] == board[i+1] == board[i+2] == 'X':
            return 10
        elif board[i] == board[i+1] == board[i+2] == 'O':
            return -10

    # Check columns
    for i in range(3):
        if board[i] == board[i+3] == board[i+6] == 'X':
            return 10
        elif board[i] == board[i+3] == board[i+6] == 'O':
            return -10

    # Check diagonals
    if board[0] == board[4] == board[8] == 'X' or \
       board[2] == board[4] == board[6] == 'X':
        return 10
    elif board[0] == board[4] == board[8] == 'O' or \
         board[2] == board[4] == board[6] == 'O':
        return -10

    # No winner
    return 0

def is_moves_left(board):
    return ' ' in board

def minimax(board, is_max):
 
    if is_moves_left(board) or bool( evaluate(board)):
        return evaluate(board)

    if is_max:
        best = -1000
        for i in range(9):
            if board[i] == ' ':
                board[i] = 'X'
                best = max(best, minimax(board, not is_max))
                board[i] = ' '
        return best
    else:
        best = 1000
        for i in range(9):
            if board[i] == ' ':
                board[i] = 'O'
                best = min(best, minimax(board, not is_max))
                board[i] = ' '
        return best

def find_best_move(board, player):
    best_val = -1000
    best_move = -1

    for i in range(9):
        if board[i] == ' ':
            board[i] = 'X'
            move_val = minimax(board, is_max=player=='X')
            board[i] = ' '

            if move_val > best_val:
                best_move = i
                best_val = move_val

    return best_move

def ai_move_smurt(game, player):
    if game.num_empty_squares() == 0:
        return None
    move = find_best_move(game.board, player)
    game.make_move_ai(move, player)
    return move

def ai_move_not_smurt(game, player):
    if game.num_empty_squares() == 0:
        return None
    move = find_best_move(game.board, player)
    game.make_move_ai(move, player)
    return move