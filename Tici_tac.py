class TicTacToe:
    def __init__(self):
        self.board = [' '] * 9
        self.current_winner = None
        self.players = {}
        self.current_turn = 'X'

    def add_player(self, sid):
        if len(self.players) < 2:
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

    def reset_game(self):
        self.board = [' '] * 9
        self.current_winner = None