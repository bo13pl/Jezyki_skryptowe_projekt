import random

class Card:
    suits = ['hearts', 'diamonds', 'clubs', 'spades']
    values = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'jack', 'queen', 'king', 'ace']

    def __init__(self, suit, value):
        self.suit = suit
        self.value = value

    def __str__(self):
        return f'{self.value}_of_{self.suit}.png'

class Hand:
    def __init__(self):
        self.cards = []
        self.value = 0
        self.aces = 0

    def add_card(self, card):
        self.cards.append(card)
        self.value += self.card_value(card)
        if card.value == 'ace':
            self.aces += 1
        self.adjust_for_ace()

    def card_value(self, card):
        if card.value in ['jack', 'queen', 'king']:
            return 10
        elif card.value == 'ace':
            return 11
        else:
            return int(card.value)

    def adjust_for_ace(self):
        while self.value > 21 and self.aces:
            self.value -= 10
            self.aces -= 1

    def can_split(self):
        return len(self.cards) == 2 and self.card_value(self.cards[0]) == self.card_value(self.cards[1])

    def split(self):
        if self.can_split():
            new_hand = Hand()
            new_hand.add_card(self.cards.pop())
            self.value = self.card_value(self.cards[0])  # Reset value to the value of the remaining card
            self.adjust_for_ace()  # Adjust for ace if necessary
            return new_hand
        else:
            raise ValueError("Hand cannot be split")

    def __str__(self):
        return ', '.join([str(card) for card in self.cards])
    
    def get_cards(self):
        return [str(card) for card in self.cards]
    
    def get_value(self):
        return self.value
class Deck:
    def __init__(self):
        self.cards = [Card(suit, value) for suit in Card.suits for value in Card.values]
        random.shuffle(self.cards)

    def draw(self):
        return self.cards.pop()

class Game:
    def __init__(self, deck=None, player_hand=None, dealer_hand=None):
        self.deck = deck if deck else Deck()
        self.player_hands = [Hand()]
        self.dealer_hand = Hand()

    def deal_initial_cards(self):
        self.dealer_hand.add_card(self.deck.draw())
        self.player_hands[0].add_card(self.deck.draw())
        self.player_hands[0].add_card(self.deck.draw())

    def hit(self, hand):
        hand.add_card(self.deck.draw())

    def is_bust(self, hand):
        return hand.value > 21
    
    def get_player_turn_ended(self):
        return all(self.is_bust(hand) or self.is_blackjack(hand) for hand in self.player_hands)
    
    def is_blackjack(self, hand):
        return hand.value == 21 and len(hand.cards) == 2

    def dealer_plays(self):
        while self.dealer_hand.value < 17:
            self.hit(self.dealer_hand)

    def check_winner(self):
        results = []
        i=1
        for hand in self.player_hands:
            if self.is_bust(hand):
                results.append(f'Hand {i} win Dealer')
            elif self.is_bust(self.dealer_hand):
                results.append(f'Hand {i} win Player')
            elif self.dealer_hand.value > hand.value:
                results.append(f'Hand {i} win Dealer')
            elif hand.value > self.dealer_hand.value:
                results.append(f'Hand {i} win Player')
            else:
                results.append(f'Hand {i} Tie')
            i+=1
        return results

    def split_hand(self, index):
        if self.player_hands[index].can_split():
            new_hand = self.player_hands[index].split()
            self.player_hands.append(new_hand)
            self.hit(self.player_hands[index])
            self.hit(new_hand)
        else:
            raise ValueError("Hand cannot be split")

    def to_dict(self):
        return {
            'deck': [str(card) for card in self.deck.cards],
            'player_hands': [[str(card) for card in hand.cards] for hand in self.player_hands],
            'dealer_hand': [str(card) for card in self.dealer_hand.cards],
            'player_values': [hand.value for hand in self.player_hands],
            'dealer_value': self.dealer_hand.value
        }

    def clear_hands(self):
        self.dealer_hand = Hand()
        self.player_hands = [Hand()]

    @classmethod
    def from_dict(cls, data):
        deck = Deck()
        deck.cards = [Card(card.split(' of ')[1], card.split(' of ')[0]) for card in data['deck']]
        player_hands = [Hand() for _ in data['player_hands']]
        for hand, cards in zip(player_hands, data['player_hands']):
            for card in cards:
                hand.add_card(Card(card.split(' of ')[1], card.split(' of ')[0]))
        dealer_hand = Hand()
        for card in data['dealer_hand']:
            dealer_hand.add_card(Card(card.split(' of ')[1], card.split(' of ')[0]))
        game = cls(deck=deck, player_hand=player_hands, dealer_hand=dealer_hand)
        game.dealer_hand.value = data['dealer_value']
        for hand, value in zip(game.player_hands, data['player_values']):
            hand.value = value
        return game
