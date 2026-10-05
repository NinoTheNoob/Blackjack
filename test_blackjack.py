import random
import unittest

from blackjack_engine import BlackjackGame, Card, Hand


def set_draw_order(game: BlackjackGame, cards: list[Card]) -> None:
    fillers = [Card("2", "♠")] * 52
    game.shoe._cards = fillers + list(reversed(cards))


class HandTests(unittest.TestCase):
    def test_aces_adjust_to_avoid_bust(self) -> None:
        hand = Hand(10, [Card("A", "♠"), Card("9", "♥"), Card("5", "♦")])
        self.assertEqual(hand.total, 15)
        self.assertFalse(hand.busted)

    def test_blackjack_is_only_a_natural_two_card_hand(self) -> None:
        natural = Hand(10, [Card("A", "♠"), Card("K", "♥")])
        split_twenty_one = Hand(
            10, [Card("A", "♠"), Card("K", "♥")], from_split=True
        )
        self.assertTrue(natural.blackjack)
        self.assertFalse(split_twenty_one.blackjack)


class GameTests(unittest.TestCase):
    def test_rejects_invalid_bets(self) -> None:
        game = BlackjackGame(rng=random.Random(4))
        for bet in (0, 9, 11, 1002):
            with self.subTest(bet=bet), self.assertRaises(ValueError):
                game.start_round(bet)

    def test_initial_natural_blackjack_pays_three_to_two(self) -> None:
        game = BlackjackGame(rng=random.Random(10))
        set_draw_order(
            game,
            [Card("9", "♠"), Card("A", "♥"), Card("7", "♣"), Card("K", "♦")],
        )
        game.start_round(20)
        self.assertTrue(game.round_over)
        self.assertEqual(game.results, ["BLACKJACK!"])
        self.assertEqual(game.bankroll, 1030)

    def test_double_down_doubles_stake_and_ends_hand(self) -> None:
        game = BlackjackGame(rng=random.Random(3))
        set_draw_order(
            game,
            [
                Card("10", "♠"), Card("5", "♥"), Card("7", "♣"),
                Card("6", "♦"), Card("10", "♠"),
            ],
        )
        game.start_round(20)
        game.double_down()
        self.assertTrue(game.round_over)
        self.assertEqual(game.hands[0].bet, 40)
        self.assertEqual(game.hands[0].total, 21)
        self.assertEqual(game.bankroll, 1040)
        self.assertEqual(game.results, ["YOU WIN"])

    def test_split_plays_both_hands(self) -> None:
        game = BlackjackGame(rng=random.Random(2))
        set_draw_order(
            game,
            [
                Card("10", "♠"), Card("8", "♥"), Card("8", "♣"),
                Card("8", "♦"), Card("10", "♠"), Card("10", "♥"),
            ],
        )
        game.start_round(20)
        game.split()
        self.assertEqual(len(game.hands), 2)
        self.assertEqual(game.hands[0].cards[1].rank, "10")
        self.assertEqual(game.current_hand.cards[1].rank, "10")

        game.stand()
        self.assertEqual(game.active_hand, 1)
        game.stand()
        self.assertTrue(game.round_over)
        self.assertEqual(game.results, ["PUSH", "PUSH"])
        self.assertEqual(game.bankroll, 1000)

    def test_dealer_hits_hard_sixteen(self) -> None:
        game = BlackjackGame(rng=random.Random(1))
        set_draw_order(
            game,
            [
                Card("6", "♠"), Card("10", "♥"), Card("10", "♣"),
                Card("6", "♦"), Card("2", "♠"),
            ],
        )
        game.start_round(20)
        game.stand()
        self.assertEqual(game.dealer_total, 18)
        self.assertEqual(game.results, ["DEALER WINS"])

    def test_dealer_stands_on_soft_seventeen(self) -> None:
        game = BlackjackGame(rng=random.Random(7))
        set_draw_order(
            game,
            [
                Card("A", "♠"), Card("10", "♥"), Card("6", "♣"),
                Card("6", "♦"),
            ],
        )
        game.start_round(20)
        game.stand()
        self.assertEqual(game.dealer_total, 17)
        self.assertEqual(len(game.dealer), 2)
        self.assertEqual(game.results, ["DEALER WINS"])


if __name__ == "__main__":
    unittest.main()
