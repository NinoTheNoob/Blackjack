import random
import unittest

from blackjack_engine import Card
from lan_game import BlackjackTable


def set_draw_order(table: BlackjackTable, cards: list[Card]) -> None:
    table.shoe._cards = [Card("2", "♠")] * 52 + list(reversed(cards))


class LanGameTests(unittest.TestCase):
    def make_table(self, cards: list[Card]) -> BlackjackTable:
        table = BlackjackTable(random.Random(8))
        set_draw_order(table, cards)
        table.add_player("a", "Alice")
        table.add_player("b", "Bob")
        table.place_bet("a", 20)
        return table

    def test_shared_deal_hides_dealer_hole_card(self) -> None:
        table = self.make_table(
            [
                Card("6", "♠"), Card("10", "♥"), Card("10", "♣"),
                Card("10", "♦"), Card("7", "♠"), Card("6", "♥"),
            ]
        )
        table.place_bet("b", 20)

        self.assertEqual(table.phase, "playing")
        self.assertEqual(table.snapshot("a")["dealer_cards"], ["6♠", "BACK"])
        self.assertEqual(table.snapshot("b")["dealer_cards"], ["6♠", "BACK"])
        self.assertTrue(table.snapshot("a")["is_viewer_turn"])

    def test_hit_keeps_the_turn_until_the_hand_finishes(self) -> None:
        table = self.make_table(
            [
                Card("6", "♠"), Card("10", "♥"), Card("8", "♣"),
                Card("10", "♦"), Card("7", "♠"), Card("7", "♥"),
                Card("2", "♦"),
            ]
        )
        table.place_bet("b", 20)
        table.act("a", "hit")

        self.assertEqual(table.players[0].hands[0].total, 19)
        self.assertEqual(table.players[0].player_id, "a")
        self.assertTrue(table.snapshot("a")["is_viewer_turn"])
        with self.assertRaisesRegex(ValueError, "another player's turn"):
            table.act("b", "stand")

        table.act("a", "stand")
        self.assertTrue(table.snapshot("b")["is_viewer_turn"])

    def test_dealer_resolves_all_players_after_their_turns(self) -> None:
        table = self.make_table(
            [
                Card("6", "♠"), Card("10", "♥"), Card("10", "♣"),
                Card("10", "♦"), Card("7", "♠"), Card("7", "♥"),
                Card("5", "♣"),
            ]
        )
        table.place_bet("b", 20)
        table.act("a", "stand")
        table.act("b", "stand")

        self.assertEqual(table.phase, "betting")
        self.assertEqual(table.snapshot("a")["dealer_total"], 21)
        self.assertEqual(table.snapshot("a")["players"][0]["hands"][0]["result"], "DEALER WINS")
        self.assertEqual(table.snapshot("b")["players"][1]["hands"][0]["result"], "DEALER WINS")

    def test_dealer_bust_pays_active_players_but_not_busted_players(self) -> None:
        table = self.make_table(
            [
                Card("10", "♠"), Card("10", "♥"), Card("10", "♣"),
                Card("6", "♦"), Card("8", "♠"), Card("6", "♥"),
                Card("10", "♦"), Card("10", "♣"),
            ]
        )
        table.place_bet("b", 20)
        table.act("a", "stand")
        table.act("b", "hit")

        snapshot = table.snapshot("a")
        self.assertEqual(snapshot["dealer_total"], 26)
        self.assertEqual(snapshot["players"][0]["hands"][0]["result"], "YOU WIN")
        self.assertEqual(snapshot["players"][1]["hands"][0]["result"], "BUST")
        self.assertEqual(snapshot["players"][0]["bankroll"], 1020)
        self.assertEqual(snapshot["players"][1]["bankroll"], 980)

    def test_ready_requires_two_connected_players(self) -> None:
        table = BlackjackTable(random.Random(3))
        table.add_player("a", "Alice")
        table.place_bet("a", 20)
        self.assertEqual(table.phase, "betting")
        self.assertEqual(len(table.players[0].hands), 0)

    def test_broke_player_is_eliminated_without_blocking_the_next_round(self) -> None:
        table = BlackjackTable(random.Random(9))
        set_draw_order(
            table,
            [
                Card("10", "♠"), Card("5", "♥"), Card("10", "♣"),
                Card("8", "♦"), Card("6", "♠"), Card("8", "♥"),
            ],
        )
        alice = table.add_player("a", "Alice")
        bob = table.add_player("b", "Bob")
        alice.bankroll = 10
        bob.bankroll = 10
        table.place_bet("a", 10)
        table.place_bet("b", 10)
        table.act("a", "stand")
        table.act("b", "stand")

        self.assertTrue(alice.eliminated)
        self.assertFalse(bob.eliminated)
        table.place_bet("b", 10)
        self.assertEqual(table.phase, "playing")
        self.assertEqual(alice.hands, [])
        self.assertEqual(len(bob.hands), 1)


if __name__ == "__main__":
    unittest.main()
