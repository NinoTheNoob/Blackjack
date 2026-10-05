import unittest
from unittest.mock import patch

from blackjack_engine import BlackjackGame
from main import BlackjackApp


class FakeRoot:
    def __init__(self) -> None:
        self.destroyed = False

    def winfo_exists(self) -> bool:
        return True

    def destroy(self) -> None:
        self.destroyed = True


class RestartPromptTests(unittest.TestCase):
    def make_app(self) -> BlackjackApp:
        app = BlackjackApp.__new__(BlackjackApp)
        app.root = FakeRoot()
        app.game = BlackjackGame(bankroll=0)
        app.bet = 20
        app.status_text = "Out of chips."
        app.game_over_prompted = True
        app._refresh = lambda: None
        return app

    @patch("main.messagebox.askyesno", return_value=True)
    def test_accepting_restart_resets_chips_bet_and_stats(self, ask_restart) -> None:
        app = self.make_app()
        app.game.wins = 4
        app._ask_restart()

        self.assertEqual(app.game.bankroll, 1000)
        self.assertEqual(app.game.wins, 0)
        self.assertEqual(app.bet, 20)
        self.assertFalse(app.game_over_prompted)
        self.assertFalse(app.root.destroyed)
        ask_restart.assert_called_once()

    @patch("main.messagebox.askyesno", return_value=False)
    def test_declining_restart_closes_the_game(self, ask_restart) -> None:
        app = self.make_app()
        app._ask_restart()

        self.assertTrue(app.root.destroyed)
        ask_restart.assert_called_once()

    @patch("main.messagebox.askyesno")
    def test_prompt_is_skipped_when_window_is_already_closed(self, ask_restart) -> None:
        app = self.make_app()
        app.root.winfo_exists = lambda: False
        app._ask_restart()

        ask_restart.assert_not_called()


if __name__ == "__main__":
    unittest.main()
