import random

class Card:
    suits = ['Hearts', 'Diamonds', 'Clubs', 'Spades']
    values = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']

    def __init__(self, suit, value):
        self.suit = suit
        self.value = value

    def __str__(self):
        return f'{self.value} of {self.suit}'

class Hand:
    def __init__(self):
        self.cards = []
        self.value = 0
        self.aces = 0

    def add_card(self, card):
        self.cards.append(card)
        self.value += self.card_value(card)
        if card.value == 'A':
            self.aces += 1
        self.adjust_for_ace()

    def card_value(self, card):
        if card.value in ['J', 'Q', 'K']:
            return 10
        elif card.value == 'A':
            return 11
        else:
            return int(card.value)

    def adjust_for_ace(self):
        while self.value > 21 and self.aces:
            self.value -= 10
            self.aces -= 1


    def __str__(self):
        return ', '.join([str(card) for card in self.cards])

class Game:
    def __init__(self, deck=None, player_hand=None, dealer_hand=None):
        self.deck = deck if deck else Deck()
        self.player_hand = Hand()
        self.dealer_hand = Hand()

    def deal_initial_cards(self):
        self.dealer_hand.add_card(self.deck.draw())
        self.player_hand.add_card(self.deck.draw())
        self.player_hand.add_card(self.deck.draw())

    def hit(self, hand):
        hand.add_card(self.deck.draw())

    def is_bust(self, hand):
        return hand.value > 21

    def is_blackjack(self, hand):
        return hand.value == 21 and len(hand.cards) == 2

    def dealer_plays(self):
        while self.dealer_hand.value < 17:
            self.hit(self.dealer_hand)

    def check_winner(self):
        if self.is_bust(self.player_hand):
            return 'Dealer'
        elif self.is_bust(self.dealer_hand):
            return 'Player'
        elif self.dealer_hand.value > self.player_hand.value:
            return 'Dealer'
        elif self.player_hand.value > self.dealer_hand.value:
            return 'Player'
        else:
            return 'Tie'

    def to_dict(self):
        return {
            'deck': [str(card) for card in self.deck.cards],
            'player_hand': [str(card) for card in self.player_hand.cards],
            'dealer_hand': [str(card) for card in self.dealer_hand.cards],
            'player_value': self.player_hand.value,
            'dealer_value': self.dealer_hand.value
        }
    def clear_hands(self):
        self.dealer_hand = Hand()
        self.player_hand = Hand()

    @classmethod
    def from_dict(cls, data):
        deck = Deck()
        deck.cards = [Card(card.split(' of ')[1], card.split(' of ')[0]) for card in data['deck']]
        player_hand = Hand()
        player_hand.cards = [Card(card.split(' of ')[1], card.split(' of ')[0]) for card in data['player_hand']]
        dealer_hand = Hand()
        dealer_hand.cards = [Card(card.split(' of ')[1], card.split(' of ')[0]) for card in data['dealer_hand']]
        game = cls(deck=deck, player_hand=player_hand, dealer_hand=dealer_hand)
        game.player_hand.value = data['player_value']
        game.dealer_hand.value = data['dealer_value']
        return game
class Deck:
    def __init__(self):
        self.cards = [Card(suit, value) for suit in Card.suits for value in Card.values]
        random.shuffle(self.cards)

    def draw(self):
        return self.cards.pop()