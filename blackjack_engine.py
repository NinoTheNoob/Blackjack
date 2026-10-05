"""Rules and game state for a single-player blackjack game."""

from __future__ import annotations

import random
from dataclasses import dataclass, field


SUITS = ("♠", "♥", "♦", "♣")
RANKS = ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K")
MIN_BET = 10
MAX_SPLIT_HANDS = 4


@dataclass(frozen=True)
class Card:
    rank: str
    suit: str

    @property
    def value(self) -> int:
        if self.rank == "A":
            return 11
        if self.rank in ("J", "Q", "K"):
            return 10
        return int(self.rank)

    def __str__(self) -> str:
        return f"{self.rank}{self.suit}"


@dataclass
class Hand:
    bet: int
    cards: list[Card] = field(default_factory=list)
    from_split: bool = False
    split_aces: bool = False
    stood: bool = False
    doubled: bool = False

    @property
    def total(self) -> int:
        total = sum(card.value for card in self.cards)
        aces = sum(card.rank == "A" for card in self.cards)
        while total > 21 and aces:
            total -= 10
            aces -= 1
        return total

    @property
    def busted(self) -> bool:
        return self.total > 21

    @property
    def blackjack(self) -> bool:
        return len(self.cards) == 2 and not self.from_split and self.total == 21

    @property
    def finished(self) -> bool:
        return self.stood or self.busted


class Shoe:
    """A six-deck shoe which reshuffles when fewer than one deck remains."""

    def __init__(self, rng: random.Random | None = None, decks: int = 6) -> None:
        if decks < 1:
            raise ValueError("A shoe must contain at least one deck.")
        self._rng = rng or random.Random()
        self._decks = decks
        self._cards: list[Card] = []
        self._shuffle()

    def _shuffle(self) -> None:
        self._cards = [
            Card(rank, suit)
            for _ in range(self._decks)
            for suit in SUITS
            for rank in RANKS
        ]
        self._rng.shuffle(self._cards)

    def draw(self) -> Card:
        if len(self._cards) < 52:
            self._shuffle()
        return self._cards.pop()


class BlackjackGame:
    """Blackjack with hit, stand, double down, and splits up to four hands."""

    def __init__(
        self,
        bankroll: int = 1000,
        rng: random.Random | None = None,
    ) -> None:
        if bankroll < 0:
            raise ValueError("The bankroll cannot be negative.")
        self.bankroll = bankroll
        self.shoe = Shoe(rng)
        self.dealer: list[Card] = []
        self.hands: list[Hand] = []
        self.active_hand = 0
        self.round_over = True
        self.results: list[str] = []
        self.wins = 0
        self.losses = 0
        self.pushes = 0
        self.blackjacks = 0

    @property
    def current_hand(self) -> Hand | None:
        if self.round_over or not self.hands:
            return None
        return self.hands[self.active_hand]

    @property
    def dealer_total(self) -> int:
        return self._dealer_total()

    def start_round(self, bet: int) -> None:
        if not self.round_over:
            raise ValueError("Finish the current hand before starting another round.")
        if bet < MIN_BET or bet % 2:
            raise ValueError(f"Bets must be an even amount of at least ${MIN_BET}.")
        if bet > self.bankroll:
            raise ValueError("You don't have enough chips for that bet.")

        self.bankroll -= bet
        self.dealer = [self.shoe.draw()]
        hand = Hand(bet=bet)
        self.hands = [hand]
        self.active_hand = 0
        self.round_over = False
        self.results = []

        hand.cards.append(self.shoe.draw())
        self.dealer.append(self.shoe.draw())
        hand.cards.append(self.shoe.draw())

        if hand.blackjack or self._dealer_has_blackjack():
            self._settle_round()

    def hit(self) -> None:
        hand = self._require_current_hand()
        hand.cards.append(self.shoe.draw())
        if hand.busted:
            self._advance_hand()

    def stand(self) -> None:
        hand = self._require_current_hand()
        hand.stood = True
        self._advance_hand()

    def double_down(self) -> None:
        hand = self._require_current_hand()
        if len(hand.cards) != 2 or hand.doubled:
            raise ValueError("You can double down only on your first two cards.")
        if self.bankroll < hand.bet:
            raise ValueError("You don't have enough chips to double down.")

        self.bankroll -= hand.bet
        hand.bet *= 2
        hand.doubled = True
        hand.cards.append(self.shoe.draw())
        hand.stood = not hand.busted
        self._advance_hand()

    def split(self) -> None:
        hand = self._require_current_hand()
        if len(hand.cards) != 2 or hand.cards[0].value != hand.cards[1].value:
            raise ValueError("You can split only a matching pair.")
        if len(self.hands) >= MAX_SPLIT_HANDS:
            raise ValueError(f"You can play no more than {MAX_SPLIT_HANDS} hands.")
        if self.bankroll < hand.bet:
            raise ValueError("You don't have enough chips to split.")
        if hand.split_aces:
            raise ValueError("Split aces cannot be split again.")

        self.bankroll -= hand.bet
        first_card, second_card = hand.cards
        splitting_aces = first_card.rank == "A"
        hand.cards = [first_card, self.shoe.draw()]
        hand.from_split = True
        hand.split_aces = splitting_aces

        new_hand = Hand(
            bet=hand.bet,
            cards=[second_card, self.shoe.draw()],
            from_split=True,
            split_aces=splitting_aces,
            stood=splitting_aces,
        )
        hand.stood = splitting_aces
        self.hands.insert(self.active_hand + 1, new_hand)
        if splitting_aces:
            self._advance_hand()

    def _require_current_hand(self) -> Hand:
        hand = self.current_hand
        if hand is None:
            raise ValueError("There is no active hand.")
        if hand.finished:
            raise ValueError("This hand has already finished.")
        return hand

    def _dealer_has_blackjack(self) -> bool:
        if len(self.dealer) != 2:
            return False
        total = sum(card.value for card in self.dealer)
        return total == 21 and any(card.rank == "A" for card in self.dealer)

    def _advance_hand(self) -> None:
        for index in range(self.active_hand + 1, len(self.hands)):
            if not self.hands[index].finished:
                self.active_hand = index
                return
        self._dealer_play()

    def _dealer_play(self) -> None:
        if not self._dealer_has_blackjack() and any(
            not hand.busted for hand in self.hands
        ):
            while self._dealer_total() < 17:
                self.dealer.append(self.shoe.draw())
        self._settle_round()

    def _dealer_total(self) -> int:
        total = sum(card.value for card in self.dealer)
        aces = sum(card.rank == "A" for card in self.dealer)
        while total > 21 and aces:
            total -= 10
            aces -= 1
        return total

    def _settle_round(self) -> None:
        dealer_total = self._dealer_total()
        dealer_blackjack = self._dealer_has_blackjack()
        outcomes: list[str] = []

        for hand in self.hands:
            if hand.busted:
                outcomes.append("BUST")
                self.losses += 1
            elif hand.blackjack:
                if dealer_blackjack:
                    self.bankroll += hand.bet
                    outcomes.append("PUSH")
                    self.pushes += 1
                else:
                    self.bankroll += hand.bet * 5 // 2
                    outcomes.append("BLACKJACK!")
                    self.wins += 1
                    self.blackjacks += 1
            elif dealer_blackjack or dealer_total > hand.total:
                outcomes.append("DEALER WINS")
                self.losses += 1
            elif dealer_total < hand.total or dealer_total > 21:
                self.bankroll += hand.bet * 2
                outcomes.append("YOU WIN")
                self.wins += 1
            else:
                self.bankroll += hand.bet
                outcomes.append("PUSH")
                self.pushes += 1

        self.results = outcomes
        self.round_over = True
