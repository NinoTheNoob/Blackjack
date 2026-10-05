"""Authoritative shared blackjack table used by LAN hosts."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from blackjack_engine import Card, Hand, MAX_SPLIT_HANDS, MIN_BET, Shoe


MAX_PLAYERS = 6


@dataclass
class PlayerSeat:
    player_id: str
    name: str
    bankroll: int = 1000
    bet: int = 20
    ready: bool = False
    connected: bool = True
    eliminated: bool = False
    hands: list[Hand] = field(default_factory=list)


class BlackjackTable:
    def __init__(self, rng: random.Random | None = None) -> None:
        self.shoe = Shoe(rng)
        self.players: list[PlayerSeat] = []
        self.dealer: list[Card] = []
        self.phase = "betting"
        self.turn_player = 0
        self.turn_hand = 0
        self.message = "Join the table, set a bet, and get ready."
        self.last_results: dict[str, list[str]] = {}
        self.rounds_played = 0

    def add_player(self, player_id: str, name: str) -> PlayerSeat:
        if self.phase == "playing":
            raise ValueError("Wait until the current round ends to join the table.")
        clean_name = " ".join(name.split())
        if not clean_name or len(clean_name) > 24:
            raise ValueError("Player names must contain 1 to 24 characters.")
        if any(player.name.casefold() == clean_name.casefold() for player in self.players):
            raise ValueError("That player name is already at the table.")
        if len(self.players) >= MAX_PLAYERS:
            raise ValueError(f"The table is full (maximum {MAX_PLAYERS} players).")
        player = PlayerSeat(player_id=player_id, name=clean_name)
        self.players.append(player)
        self.message = f"{clean_name} joined the table."
        return player

    def place_bet(self, player_id: str, bet: int) -> None:
        if self.phase == "playing":
            raise ValueError("Wait until this round ends to place a bet.")
        player = self._player(player_id)
        if not player.connected:
            raise ValueError("Reconnect before placing a bet.")
        if player.eliminated:
            raise ValueError("You are out of chips and cannot continue playing.")
        if bet < MIN_BET or bet % 2:
            raise ValueError(f"Bets must be an even amount of at least ${MIN_BET}.")
        if bet > player.bankroll:
            raise ValueError("You don't have enough chips for that bet.")
        player.bet = bet
        player.ready = True
        self.message = f"{player.name} is ready."
        eligible_players = [
            seat for seat in self.players
            if seat.connected and not seat.eliminated and seat.bankroll >= MIN_BET
        ]
        minimum_players = 1 if self.rounds_played else 2
        if len(eligible_players) >= minimum_players and all(
            seat.ready and seat.bankroll >= seat.bet for seat in eligible_players
        ):
            self._start_round()

    def set_bet(self, player_id: str, bet: int) -> None:
        if self.phase == "playing":
            raise ValueError("You cannot change your bet during a round.")
        player = self._player(player_id)
        if bet < MIN_BET or bet % 2 or bet > player.bankroll:
            raise ValueError("Choose an affordable, even bet of at least $10.")
        player.bet = bet
        player.ready = False

    def act(self, player_id: str, action: str) -> None:
        if self.phase != "playing":
            raise ValueError("There is no active round.")
        if self.players[self.turn_player].player_id != player_id:
            raise ValueError("It is another player's turn.")
        player = self.players[self.turn_player]
        hand = player.hands[self.turn_hand]
        if hand.finished:
            raise ValueError("That hand has already finished.")

        if action == "hit":
            hand.cards.append(self.shoe.draw())
            self.message = f"{player.name} hit."
        elif action == "stand":
            hand.stood = True
            self.message = f"{player.name} stood."
        elif action == "double":
            if len(hand.cards) != 2 or hand.doubled:
                raise ValueError("You can double down only on your first two cards.")
            if player.bankroll < hand.bet:
                raise ValueError("You don't have enough chips to double down.")
            player.bankroll -= hand.bet
            hand.bet *= 2
            hand.doubled = True
            hand.cards.append(self.shoe.draw())
            hand.stood = not hand.busted
            self.message = f"{player.name} doubled down."
        elif action == "split":
            self._split(player, hand)
            self.message = f"{player.name} split a pair."
        else:
            raise ValueError("Unknown game action.")

        if hand.busted:
            self.message = f"{player.name} busted."
        self._advance_turn()

    def disconnect(self, player_id: str) -> None:
        player = self._player(player_id)
        player.connected = False
        player.ready = False
        if self.phase == "playing":
            for hand in player.hands:
                if not hand.finished:
                    hand.stood = True
            self._advance_turn()
        self.message = f"{player.name} disconnected."

    def snapshot(self, viewer_id: str) -> dict[str, object]:
        viewer = self._player(viewer_id)
        reveal_dealer = self.phase != "playing"
        dealer_cards = [str(card) for card in self.dealer]
        if not reveal_dealer and len(dealer_cards) > 1:
            dealer_cards[1] = "BACK"
            dealer_cards = dealer_cards[:2]

        return {
            "type": "state",
            "viewer_id": viewer_id,
            "phase": self.phase,
            "rounds_played": self.rounds_played,
            "message": self.message,
            "players": [
                {
                    "id": player.player_id,
                    "name": player.name,
                    "bankroll": player.bankroll,
                    "bet": player.bet,
                    "ready": player.ready,
                    "connected": player.connected,
                    "eliminated": player.eliminated,
                    "active_hand": self.turn_hand if index == self.turn_player else -1,
                    "is_turn": (
                        self.phase == "playing" and index == self.turn_player
                    ),
                    "hands": [
                        {
                            "cards": [str(card) for card in hand.cards],
                            "total": hand.total,
                            "bet": hand.bet,
                            "busted": hand.busted,
                            "stood": hand.stood,
                            "doubled": hand.doubled,
                            "split_aces": hand.split_aces,
                            "result": (
                                self.last_results.get(player.player_id, [])[hand_index]
                                if hand_index
                                < len(self.last_results.get(player.player_id, []))
                                else ""
                            ),
                        }
                        for hand_index, hand in enumerate(player.hands)
                    ],
                }
                for index, player in enumerate(self.players)
            ],
            "dealer_cards": dealer_cards,
            "dealer_total": self._dealer_total() if reveal_dealer else None,
            "is_viewer_turn": (
                self.phase == "playing"
                and self.players[self.turn_player].player_id == viewer_id
            ),
            "viewer_bankroll": viewer.bankroll,
        }

    def _player(self, player_id: str) -> PlayerSeat:
        for player in self.players:
            if player.player_id == player_id:
                return player
        raise ValueError("Player is no longer at the table.")

    def _start_round(self) -> None:
        self.phase = "playing"
        self.dealer = [self.shoe.draw()]
        self.last_results = {}
        for player in self.players:
            if (
                not player.connected
                or player.eliminated
                or player.bankroll < MIN_BET
            ):
                player.hands = []
                continue
            player.bankroll -= player.bet
            player.hands = [Hand(bet=player.bet)]
            player.ready = False
            player.hands[0].cards.append(self.shoe.draw())
        self.dealer.append(self.shoe.draw())
        for player in self.players:
            if not player.hands:
                continue
            player.hands[0].cards.append(self.shoe.draw())
            if player.hands[0].blackjack:
                player.hands[0].stood = True

        if self._dealer_has_blackjack() or not self._has_playable_hands():
            self._dealer_play()
        else:
            self.turn_player, self.turn_hand = self._first_playable()
            self.message = f"{self.players[self.turn_player].name}'s turn."

    def _split(self, player: PlayerSeat, hand: Hand) -> None:
        if len(hand.cards) != 2 or hand.cards[0].value != hand.cards[1].value:
            raise ValueError("You can split only a matching pair.")
        if len(player.hands) >= MAX_SPLIT_HANDS:
            raise ValueError(f"You can play no more than {MAX_SPLIT_HANDS} hands.")
        if player.bankroll < hand.bet:
            raise ValueError("You don't have enough chips to split.")
        if hand.split_aces:
            raise ValueError("Split aces cannot be split again.")

        first_card, second_card = hand.cards
        splitting_aces = first_card.rank == "A"
        player.bankroll -= hand.bet
        hand.cards = [first_card, self.shoe.draw()]
        hand.from_split = True
        hand.split_aces = splitting_aces
        hand.stood = splitting_aces
        new_hand = Hand(
            bet=hand.bet,
            cards=[second_card, self.shoe.draw()],
            from_split=True,
            split_aces=splitting_aces,
            stood=splitting_aces,
        )
        player.hands.insert(self.turn_hand + 1, new_hand)

    def _first_playable(self) -> tuple[int, int]:
        for player_index, player in enumerate(self.players):
            for hand_index, hand in enumerate(player.hands):
                if not hand.finished:
                    return player_index, hand_index
        raise RuntimeError("No playable hand exists.")

    def _advance_turn(self) -> None:
        current_player = self.players[self.turn_player]
        if (
            self.turn_hand < len(current_player.hands)
            and not current_player.hands[self.turn_hand].finished
        ):
            self.message = f"{current_player.name}'s turn."
            return
        for player_index in range(self.turn_player, len(self.players)):
            player = self.players[player_index]
            start_hand = self.turn_hand + 1 if player_index == self.turn_player else 0
            for hand_index in range(start_hand, len(player.hands)):
                if not player.hands[hand_index].finished:
                    self.turn_player, self.turn_hand = player_index, hand_index
                    self.message = f"{player.name}'s turn."
                    return
        self._dealer_play()

    def _has_playable_hands(self) -> bool:
        return any(
            not hand.finished
            for player in self.players
            for hand in player.hands
        )

    def _dealer_play(self) -> None:
        if not self._dealer_has_blackjack() and any(
            not hand.busted for player in self.players for hand in player.hands
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

    def _dealer_has_blackjack(self) -> bool:
        return (
            len(self.dealer) == 2
            and sum(card.value for card in self.dealer) == 21
            and any(card.rank == "A" for card in self.dealer)
        )

    def _settle_round(self) -> None:
        dealer_total = self._dealer_total()
        dealer_blackjack = self._dealer_has_blackjack()
        self.last_results = {}
        for player in self.players:
            outcomes: list[str] = []
            for hand in player.hands:
                if hand.busted:
                    outcomes.append("BUST")
                elif hand.blackjack:
                    if dealer_blackjack:
                        player.bankroll += hand.bet
                        outcomes.append("PUSH")
                    else:
                        player.bankroll += hand.bet * 5 // 2
                        outcomes.append("BLACKJACK!")
                elif dealer_blackjack or dealer_total > hand.total:
                    outcomes.append("DEALER WINS")
                elif dealer_total < hand.total or dealer_total > 21:
                    player.bankroll += hand.bet * 2
                    outcomes.append("YOU WIN")
                else:
                    player.bankroll += hand.bet
                    outcomes.append("PUSH")
            self.last_results[player.player_id] = outcomes
            if player.bankroll < MIN_BET:
                player.eliminated = True
                player.ready = False
        self.rounds_played += 1
        self.phase = "betting"
        self.message = "Round over. Place your next bet when ready."
