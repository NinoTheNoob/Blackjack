"""Graphical desktop blackjack game."""

from __future__ import annotations

from collections.abc import Callable
import tkinter as tk
from tkinter import messagebox

from blackjack_engine import BlackjackGame, Card, MIN_BET
from lan_network import LanClient, LanServer, get_local_ip
from lan_ui import LanBlackjackApp


BG = "#071512"
PANEL = "#10241d"
FELT = "#0b603d"
FELT_DARK = "#08472e"
GOLD = "#f2c66d"
TEXT = "#f4f0e6"
MUTED = "#b7c9bf"
RED = "#d65b5b"
CARD_BG = "#fffdf7"


class BlackjackApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.game = BlackjackGame()
        self.bet = 20
        self.status_text = "Place your bet, then deal."
        self.game_over_prompted = False

        root.title("Blackjack")
        root.configure(bg=BG)
        root.minsize(900, 680)
        root.geometry("1120x790")

        self._build_layout()
        self._refresh()

    def _build_layout(self) -> None:
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=34, pady=(22, 14))

        tk.Label(
            header, text="BLACKJACK", bg=BG, fg=GOLD,
            font=("Segoe UI", 25, "bold"),
        ).pack(side="left")
        tk.Label(
            header, text="SINGLE PLAYER  •  SIX-DECK SHOE", bg=BG, fg=MUTED,
            font=("Segoe UI", 9, "bold"),
        ).pack(side="left", padx=20, pady=(9, 0))

        self.bankroll_label = tk.Label(
            header, bg=BG, fg=TEXT, font=("Segoe UI", 13, "bold")
        )
        self.bankroll_label.pack(side="right", pady=(8, 0))

        self.table = tk.Frame(
            self.root, bg=FELT, highlightbackground=GOLD, highlightthickness=2
        )
        self.table.pack(fill="both", expand=True, padx=34, pady=6)

        self.dealer_title = tk.Label(
            self.table, text="DEALER", bg=FELT, fg=TEXT,
            font=("Segoe UI", 10, "bold"),
        )
        self.dealer_title.pack(pady=(20, 5))
        self.dealer_cards = tk.Frame(self.table, bg=FELT)
        self.dealer_cards.pack(pady=(0, 5))
        self.dealer_total = tk.Label(
            self.table, bg=FELT, fg=MUTED, font=("Segoe UI", 10)
        )
        self.dealer_total.pack()

        self.status_label = tk.Label(
            self.table, text="", bg=FELT_DARK, fg=TEXT,
            font=("Segoe UI", 12, "bold"), padx=18, pady=10,
        )
        self.status_label.pack(pady=15)

        self.hands_frame = tk.Frame(self.table, bg=FELT)
        self.hands_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        bottom = tk.Frame(self.root, bg=BG)
        bottom.pack(fill="x", padx=34, pady=(14, 22))

        bet_box = tk.Frame(bottom, bg=PANEL, padx=16, pady=12)
        bet_box.pack(side="left")
        tk.Label(
            bet_box, text="YOUR BET", bg=PANEL, fg=MUTED,
            font=("Segoe UI", 9, "bold"),
        ).grid(row=0, column=0, columnspan=3, sticky="w")
        self.bet_label = tk.Label(
            bet_box, bg=PANEL, fg=TEXT, font=("Segoe UI", 17, "bold"), width=8
        )
        self.bet_label.grid(row=1, column=1, padx=4)
        self.decrease_bet_button = self._button(
            bet_box, "− $10", self._decrease_bet, compact=True
        )
        self.decrease_bet_button.grid(row=1, column=0)
        self.increase_bet_button = self._button(
            bet_box, "+ $10", self._increase_bet, compact=True
        )
        self.increase_bet_button.grid(row=1, column=2)

        actions = tk.Frame(bottom, bg=BG)
        actions.pack(side="right")
        self.deal_button = self._button(actions, "DEAL", self._deal, primary=True)
        self.deal_button.pack(side="left", padx=4)
        self.hit_button = self._button(actions, "HIT", self._hit)
        self.hit_button.pack(side="left", padx=4)
        self.stand_button = self._button(actions, "STAND", self._stand)
        self.stand_button.pack(side="left", padx=4)
        self.double_button = self._button(actions, "DOUBLE", self._double)
        self.double_button.pack(side="left", padx=4)
        self.split_button = self._button(actions, "SPLIT", self._split)
        self.split_button.pack(side="left", padx=4)

        footer = tk.Label(
            self.root,
            text="Blackjack pays 3:2  •  Dealer stands on 17  •  Split up to four hands",
            bg=BG, fg="#82968b", font=("Segoe UI", 9),
        )
        footer.pack(pady=(0, 12))

    @staticmethod
    def _button(
        parent: tk.Widget,
        text: str,
        command: Callable[[], None],
        *,
        primary: bool = False,
        compact: bool = False,
    ) -> tk.Button:
        bg = GOLD if primary else "#1d392d"
        fg = "#18231c" if primary else TEXT
        button = tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground="#f8d991" if primary else "#2c4c3c",
            activeforeground=fg,
            disabledforeground="#6f8177",
            relief="flat",
            bd=0,
            padx=10 if compact else 15,
            pady=9,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2",
        )
        return button

    def _decrease_bet(self) -> None:
        self.bet = max(MIN_BET, self.bet - 10)
        self._refresh()

    def _increase_bet(self) -> None:
        if self.bet + 10 <= self.game.bankroll:
            self.bet += 10
        self._refresh()

    def _deal(self) -> None:
        try:
            self.game.start_round(self.bet)
        except ValueError as error:
            self.status_text = str(error)
        else:
            self.status_text = (
                "Blackjack!" if self.game.round_over and self.game.results[0] == "BLACKJACK!"
                else "Dealer has blackjack." if self.game.round_over
                else "Your turn — hit, stand, double, or split."
            )
        self._refresh()

    def _run_action(self, action: object) -> None:
        try:
            action()
        except ValueError as error:
            self.status_text = str(error)
        else:
            if self.game.round_over:
                self.status_text = self._round_summary()
            else:
                hand = self.game.current_hand
                if hand is not None and len(self.game.hands) > 1:
                    self.status_text = (
                        f"Hand {self.game.active_hand + 1} of {len(self.game.hands)} — "
                        "your turn."
                    )
                else:
                    self.status_text = "Your turn — hit, stand, double, or split."
        self._refresh()

    def _hit(self) -> None:
        self._run_action(self.game.hit)

    def _stand(self) -> None:
        self._run_action(self.game.stand)

    def _double(self) -> None:
        self._run_action(self.game.double_down)

    def _split(self) -> None:
        self._run_action(self.game.split)

    def _round_summary(self) -> str:
        dealer_total = self.game.dealer_total
        dealer_cards = " ".join(map(str, self.game.dealer))
        outcomes = "  •  ".join(
            f"Hand {index + 1}: {result}"
            for index, result in enumerate(self.game.results)
        )
        return f"Dealer {dealer_total} ({dealer_cards})  •  {outcomes}"

    def _draw_card(self, parent: tk.Frame, text: str, hidden: bool = False) -> None:
        card = tk.Frame(
            parent,
            bg="#173c30" if hidden else CARD_BG,
            width=62,
            height=88,
            highlightbackground="#0a3b27" if hidden else "#e5dfd1",
            highlightthickness=1,
        )
        card.pack(side="left", padx=4)
        card.pack_propagate(False)
        if hidden:
            tk.Label(
                card, text="✦", bg="#173c30", fg=GOLD,
                font=("Segoe UI", 22, "bold"),
            ).place(relx=0.5, rely=0.5, anchor="center")
            return

        rank, suit = text[:-1], text[-1]
        color = RED if suit in ("♥", "♦") else "#17221c"
        tk.Label(
            card, text=f"{rank}\n{suit}", justify="left",
            bg=CARD_BG, fg=color, font=("Segoe UI", 13, "bold"),
        ).place(x=6, y=5, anchor="nw")
        tk.Label(
            card, text=suit, bg=CARD_BG, fg=color,
            font=("Segoe UI", 23),
        ).place(relx=0.5, rely=0.58, anchor="center")

    def _render_cards(
        self, parent: tk.Frame, cards: list[Card], hide_hole: bool
    ) -> None:
        for child in parent.winfo_children():
            child.destroy()
        for index, card in enumerate(cards):
            self._draw_card(parent, str(card), hidden=hide_hole and index == 1)

    def _render_hands(self) -> None:
        for child in self.hands_frame.winfo_children():
            child.destroy()

        for index, hand in enumerate(self.game.hands):
            is_active = not self.game.round_over and index == self.game.active_hand
            panel = tk.Frame(
                self.hands_frame,
                bg="#0b5035" if is_active else FELT,
                padx=10,
                pady=8,
                highlightbackground=GOLD if is_active else FELT,
                highlightthickness=2 if is_active else 0,
            )
            panel.pack(side="left", expand=True, padx=5, pady=2)
            title = f"HAND {index + 1}  •  ${hand.bet}"
            if is_active:
                title += "  •  PLAYING"
            tk.Label(
                panel, text=title, bg=panel["bg"], fg=GOLD if is_active else MUTED,
                font=("Segoe UI", 9, "bold"),
            ).pack(pady=(0, 6))
            cards = tk.Frame(panel, bg=panel["bg"])
            cards.pack()
            self._render_cards(cards, hand.cards, hide_hole=False)
            description = (
                self.game.results[index] if self.game.round_over
                else f"Total: {hand.total}" + ("  •  BUST" if hand.busted else "")
            )
            tk.Label(
                panel, text=description, bg=panel["bg"], fg=TEXT,
                font=("Segoe UI", 10, "bold"),
            ).pack(pady=(7, 0))

    def _refresh(self) -> None:
        self.bankroll_label.config(
            text=f"CHIPS  ${self.game.bankroll:,}    "
            f"RECORD  {self.game.wins}-{self.game.losses}-{self.game.pushes}"
        )
        self.bet_label.config(text=f"${self.bet:,}")
        self.status_label.config(text=self.status_text)
        self._render_cards(
            self.dealer_cards,
            self.game.dealer,
            hide_hole=not self.game.round_over and bool(self.game.dealer),
        )
        dealer_total = (
            f"Showing: {self.game.dealer[0].rank}"
            if not self.game.round_over and self.game.dealer
            else f"Total: {self.game.dealer_total}" if self.game.dealer else ""
        )
        self.dealer_total.config(text=dealer_total)
        self._render_hands()

        active = self.game.current_hand
        can_deal = self.game.round_over and self.bet <= self.game.bankroll
        self.deal_button.config(state="normal" if can_deal else "disabled")
        self.hit_button.config(state="normal" if active else "disabled")
        self.stand_button.config(state="normal" if active else "disabled")
        can_double = active is not None and len(active.cards) == 2
        self.double_button.config(
            state="normal" if can_double and self.game.bankroll >= active.bet else "disabled"
        )
        can_split = (
            active is not None
            and len(active.cards) == 2
            and active.cards[0].value == active.cards[1].value
            and len(self.game.hands) < 4
            and self.game.bankroll >= active.bet
            and not active.split_aces
        )
        self.split_button.config(state="normal" if can_split else "disabled")
        betting_enabled = self.game.round_over
        self.decrease_bet_button.config(
            state="normal" if betting_enabled and self.bet > MIN_BET else "disabled"
        )
        self.increase_bet_button.config(
            state="normal"
            if betting_enabled and self.bet + 10 <= self.game.bankroll
            else "disabled"
        )
        if (
            self.game.round_over
            and self.game.bankroll < MIN_BET
            and not self.game_over_prompted
        ):
            self.game_over_prompted = True
            self.root.after_idle(self._ask_restart)

    def _ask_restart(self) -> None:
        if not self.root.winfo_exists():
            return
        restart = messagebox.askyesno(
            "Out of chips",
            "You're out of chips. Would you like to restart with $1,000?",
            parent=self.root,
        )
        if restart:
            self.game = BlackjackGame()
            self.bet = 20
            self.status_text = "New game — place your bet, then deal."
            self.game_over_prompted = False
            self._refresh()
        else:
            self.root.destroy()


def main() -> None:
    root = tk.Tk()
    root.title("Blackjack")
    root.configure(bg=BG)
    root.geometry("520x280")
    root.resizable(False, False)
    root.update_idletasks()
    _center_window(root)
    server: LanServer | None = None
    client: LanClient | None = None
    try:
        mode = _choose_mode(root)
        if mode is None:
            root.destroy()
            return
        if mode == "solo":
            _clear_window(root)
            root.resizable(True, True)
            BlackjackApp(root)
            root.mainloop()
            return

        host_address: str | None = None
        if mode == "host":
            name = _ask_name(root)
            if name is None:
                root.destroy()
                return
            server = LanServer()
            server.start()
            host_address = get_local_ip()
            messagebox.showinfo(
                "LAN blackjack hosted",
                f"Your local network address is {host_address}:{server.port}.\n"
                "Share this address with players on the same Wi-Fi. "
                "The host must keep the game open.",
                parent=root,
            )
            client = LanClient("127.0.0.1", name)
        else:
            address = _ask_text(
                root,
                "Join a LAN table",
                "Enter the host's IP address or computer name. You can paste "
                "the full address, including :47920:",
                "127.0.0.1",
            )
            if address is None:
                root.destroy()
                return
            name = _ask_name(root)
            if name is None:
                root.destroy()
                return
            client = LanClient(address, name)
        _clear_window(root)
        root.resizable(True, True)
        LanBlackjackApp(root, client, server, host_address)
        root.mainloop()
    except (OSError, RuntimeError, tk.TclError, ValueError) as error:
        if client is not None:
            client.close()
        if server is not None:
            server.stop()
        try:
            messagebox.showerror(
                "Blackjack could not start",
                _connection_error_message(error),
                parent=root,
            )
        finally:
            root.destroy()


def _connection_error_message(error: Exception) -> str:
    if isinstance(error, OSError):
        return (
            f"Could not connect to the game host.\n\n{error}\n\n"
            "Check that both computers are on the same Wi-Fi/LAN, the host "
            "game is still open, and Windows Firewall allows Blackjack "
            "(TCP port 47920). Enter the host address with or without :47920."
        )
    return str(error)


def _choose_mode(root: tk.Tk) -> str | None:
    _clear_window(root)
    root.title("Blackjack - Choose a game")
    result: list[str | None] = [None]
    completed = tk.BooleanVar(root, value=False)
    root.resizable(False, False)
    frame = tk.Frame(root, bg=BG, padx=36, pady=24)
    frame.pack(fill="both", expand=True)
    tk.Label(
        frame, text="BLACKJACK", bg=BG, fg=GOLD,
        font=("Segoe UI", 20, "bold"),
    ).pack(padx=30, pady=(22, 8))
    tk.Label(
        frame, text="Choose how you want to play.", bg=BG, fg=MUTED,
        font=("Segoe UI", 10),
    ).pack(pady=(0, 12))
    options = tk.Frame(frame, bg=BG)
    options.pack(fill="x", padx=24, pady=(0, 18))
    for label, value in (
        ("SOLO", "solo"),
        ("HOST LAN GAME", "host"),
        ("JOIN LAN GAME", "join"),
    ):
        button = BlackjackApp._button(
            options,
            label,
            lambda selected=value: (
                result.__setitem__(0, selected),
                completed.set(True),
            ),
            primary=value == "host",
        )
        button.pack(fill="x", pady=4)
    root.protocol("WM_DELETE_WINDOW", lambda: completed.set(True))
    root.wait_variable(completed)
    root.protocol("WM_DELETE_WINDOW", root.destroy)
    return result[0]


def _ask_name(root: tk.Tk) -> str | None:
    while True:
        name = _ask_text(
            root,
            "Player name",
            "Choose a player name (up to 24 characters):",
            "Player",
        )
        if name is None:
            return None
        clean_name = " ".join(name.split())
        if clean_name and len(clean_name) <= 24:
            return clean_name
        messagebox.showerror(
            "Invalid player name",
            "Player names must contain 1 to 24 characters.",
            parent=root,
        )


def _ask_text(
    root: tk.Tk,
    title: str,
    prompt: str,
    initial_value: str,
) -> str | None:
    dialog = tk.Toplevel(root)
    dialog.title(title)
    dialog.configure(bg=BG)
    dialog.resizable(False, False)
    dialog.transient(root)
    dialog.grab_set()
    result = tk.StringVar(root, value="")

    frame = tk.Frame(dialog, bg=BG, padx=20, pady=16)
    frame.pack(fill="both", expand=True)
    tk.Label(frame, text=prompt, bg=BG, fg=TEXT).pack(anchor="w", pady=(0, 8))
    entry = tk.Entry(frame, width=42)
    entry.insert(0, initial_value)
    entry.pack(fill="x", pady=(0, 12))
    entry.focus_set()

    def finish(value: str) -> None:
        result.set(value)
        dialog.destroy()

    buttons = tk.Frame(frame, bg=BG)
    buttons.pack()
    BlackjackApp._button(
        buttons, "CONTINUE", lambda: finish(entry.get()), primary=True
    ).pack(side="left", padx=5)
    BlackjackApp._button(
        buttons, "CANCEL", lambda: finish("")
    ).pack(side="left", padx=5)
    def finish_from_key(event: tk.Event[tk.Entry]) -> str:
        if event.widget is entry:
            finish(entry.get())
        return "break"

    entry.bind("<Return>", finish_from_key)
    dialog.protocol("WM_DELETE_WINDOW", lambda: finish(""))
    root.wait_window(dialog)
    return result.get() or None


def _clear_window(root: tk.Tk) -> None:
    for child in root.winfo_children():
        child.destroy()


def _center_window(root: tk.Tk) -> None:
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = max(0, (root.winfo_screenwidth() - width) // 2)
    y = max(0, (root.winfo_screenheight() - height) // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")


if __name__ == "__main__":
    main()
