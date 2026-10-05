"""Tkinter table view for host-authoritative LAN blackjack."""

from __future__ import annotations

import queue
import tkinter as tk
from tkinter import messagebox
from typing import Any

from blackjack_engine import MIN_BET
from lan_network import LanClient, LanServer


BG = "#071512"
PANEL = "#10241d"
FELT = "#0b603d"
FELT_DARK = "#08472e"
GOLD = "#f2c66d"
TEXT = "#f4f0e6"
MUTED = "#b7c9bf"
RED = "#d65b5b"
CARD_BG = "#fffdf7"


class LanBlackjackApp:
    def __init__(
        self,
        root: tk.Tk,
        client: LanClient,
        server: LanServer | None = None,
        host_address: str | None = None,
    ) -> None:
        self.root = root
        self.client = client
        self.server = server
        self.host_address = host_address
        self.state: dict[str, Any] = {}
        self.viewer_id = ""
        self.bet = 20
        self.waiting = "Connecting to the blackjack table..."

        root.title("Blackjack - LAN table")
        root.configure(bg=BG)
        root.geometry("1160x790")
        root.minsize(900, 650)
        self._build_layout()
        self._poll_updates()
        root.protocol("WM_DELETE_WINDOW", self._close)

    def _build_layout(self) -> None:
        header = tk.Frame(self.root, bg=BG)
        header.pack(fill="x", padx=26, pady=(18, 12))
        tk.Label(
            header, text="BLACKJACK", bg=BG, fg=GOLD,
            font=("Segoe UI", 24, "bold"),
        ).pack(side="left")
        self.phase_label = tk.Label(
            header, text="LOCAL NETWORK TABLE", bg=BG, fg=MUTED,
            font=("Segoe UI", 9, "bold"),
        )
        self.phase_label.pack(side="left", padx=18, pady=(7, 0))
        self.chips_label = tk.Label(
            header, text="", bg=BG, fg=TEXT, font=("Segoe UI", 12, "bold")
        )
        self.chips_label.pack(side="right", pady=(7, 0))

        if self.host_address:
            address_text = f"HOST  {self.host_address}:47920"
            tk.Label(
                self.root, text=address_text, bg=BG, fg=GOLD,
                font=("Segoe UI", 10, "bold"),
            ).pack(pady=(0, 4))

        self.table = tk.Frame(
            self.root, bg=FELT, highlightbackground=GOLD, highlightthickness=2
        )
        self.table.pack(fill="both", expand=True, padx=26, pady=6)
        tk.Label(
            self.table, text="DEALER", bg=FELT, fg=TEXT,
            font=("Segoe UI", 10, "bold"),
        ).pack(pady=(12, 4))
        self.dealer_cards = tk.Frame(self.table, bg=FELT)
        self.dealer_cards.pack()
        self.dealer_total = tk.Label(
            self.table, text="", bg=FELT, fg=MUTED, font=("Segoe UI", 10)
        )
        self.dealer_total.pack(pady=(4, 8))
        self.status_label = tk.Label(
            self.table, text=self.waiting, bg=FELT_DARK, fg=TEXT,
            font=("Segoe UI", 11, "bold"), padx=14, pady=8, wraplength=850,
        )
        self.status_label.pack(pady=8)
        self.players_frame = tk.Frame(self.table, bg=FELT)
        self.players_frame.pack(fill="both", expand=True, padx=12, pady=(0, 8))

        footer = tk.Frame(self.root, bg=BG)
        footer.pack(fill="x", padx=26, pady=(10, 18))
        bet_box = tk.Frame(footer, bg=PANEL, padx=12, pady=9)
        bet_box.pack(side="left")
        tk.Label(
            bet_box, text="YOUR BET", bg=PANEL, fg=MUTED,
            font=("Segoe UI", 8, "bold"),
        ).grid(row=0, column=0, columnspan=3, sticky="w")
        self.bet_label = tk.Label(
            bet_box, text="$20", bg=PANEL, fg=TEXT,
            font=("Segoe UI", 15, "bold"), width=7,
        )
        self.bet_label.grid(row=1, column=1, padx=4)
        self.bet_down = self._button(bet_box, "− $10", self._decrease_bet)
        self.bet_down.grid(row=1, column=0)
        self.bet_up = self._button(bet_box, "+ $10", self._increase_bet)
        self.bet_up.grid(row=1, column=2)
        self.ready_button = self._button(
            footer, "BET & READY", self._ready, primary=True
        )
        self.ready_button.pack(side="left", padx=12)
        action_box = tk.Frame(footer, bg=BG)
        action_box.pack(side="right")
        self.hit_button = self._button(
            action_box, "HIT", lambda: self._send_action("hit")
        )
        self.hit_button.pack(side="left", padx=3)
        self.stand_button = self._button(
            action_box, "STAND", lambda: self._send_action("stand")
        )
        self.stand_button.pack(side="left", padx=3)
        self.double_button = self._button(
            action_box, "DOUBLE", lambda: self._send_action("double")
        )
        self.double_button.pack(side="left", padx=3)
        self.split_button = self._button(
            action_box, "SPLIT", lambda: self._send_action("split")
        )
        self.split_button.pack(side="left", padx=3)

    @staticmethod
    def _button(
        parent: tk.Widget,
        text: str,
        command: Any,
        primary: bool = False,
    ) -> tk.Button:
        foreground = "#18231c" if primary else TEXT
        return tk.Button(
            parent, text=text, command=command,
            bg=GOLD if primary else "#1d392d", fg=foreground,
            activebackground="#f8d991" if primary else "#2c4c3c",
            activeforeground=foreground, disabledforeground="#6f8177",
            relief="flat", bd=0, padx=11, pady=9,
            font=("Segoe UI", 9, "bold"), cursor="hand2",
        )

    def _decrease_bet(self) -> None:
        self.bet = max(MIN_BET, self.bet - 10)
        self._refresh()

    def _increase_bet(self) -> None:
        bankroll = int(self.state.get("viewer_bankroll", 1000))
        if self.bet + 10 <= bankroll:
            self.bet += 10
        self._refresh()

    def _ready(self) -> None:
        self._send(self.client.send_ready, self.bet)

    def _send_action(self, action: str) -> None:
        self._send(self.client.send_action, action)

    def _send(self, callback: Any, *args: Any) -> None:
        try:
            callback(*args)
        except (OSError, ValueError) as error:
            self.waiting = str(error)
            self._refresh()

    def _poll_updates(self) -> None:
        while True:
            try:
                update = self.client.updates.get_nowait()
            except queue.Empty:
                break
            if update.get("type") == "state":
                self.state = update
                self.viewer_id = str(update.get("viewer_id", ""))
                self.waiting = ""
            elif update.get("type") == "error":
                self.waiting = str(update.get("message", "Network error."))
                if update.get("fatal"):
                    messagebox.showerror("LAN connection lost", self.waiting)
                    self._close()
                    return
            self._refresh()
        self.root.after(100, self._poll_updates)

    def _draw_card(self, parent: tk.Frame, value: str) -> None:
        hidden = value == "BACK"
        card = tk.Frame(
            parent, bg="#173c30" if hidden else CARD_BG,
            width=54, height=74,
            highlightbackground="#0a3b27" if hidden else "#e5dfd1",
            highlightthickness=1,
        )
        card.pack(side="left", padx=3)
        card.pack_propagate(False)
        if hidden:
            tk.Label(
                card, text="✦", bg="#173c30", fg=GOLD,
                font=("Segoe UI", 20, "bold"),
            ).place(relx=0.5, rely=0.5, anchor="center")
            return
        rank, suit = value[:-1], value[-1]
        color = RED if suit in ("♥", "♦") else "#17221c"
        tk.Label(
            card, text=f"{rank}\n{suit}", bg=CARD_BG, fg=color,
            justify="left", font=("Segoe UI", 11, "bold"),
        ).place(x=5, y=4, anchor="nw")
        tk.Label(
            card, text=suit, bg=CARD_BG, fg=color,
            font=("Segoe UI", 20),
        ).place(relx=0.5, rely=0.6, anchor="center")

    def _render_cards(self, parent: tk.Frame, cards: list[str]) -> None:
        for child in parent.winfo_children():
            child.destroy()
        for card in cards:
            self._draw_card(parent, card)

    def _render_players(self) -> None:
        for child in self.players_frame.winfo_children():
            child.destroy()
        players = self.state.get("players", [])
        for index, player in enumerate(players):
            row, column = divmod(index, 3)
            is_turn = bool(player.get("is_turn"))
            is_self = player.get("id") == self.viewer_id
            background = "#0b5035" if is_turn else FELT
            border = GOLD if is_turn else FELT
            panel = tk.Frame(
                self.players_frame, bg=background, padx=8, pady=6,
                highlightbackground=border, highlightthickness=2 if is_turn else 0,
            )
            panel.grid(row=row, column=column, sticky="nsew", padx=4, pady=4)
            self.players_frame.grid_columnconfigure(column, weight=1)
            self.players_frame.grid_rowconfigure(row, weight=1)
            player_name = str(player.get("name", "Player"))
            if is_self:
                player_name += " (YOU)"
            if not player.get("connected", True):
                player_name += " (LEFT)"
            elif player.get("eliminated"):
                player_name += " (OUT)"
            title = f"{player_name}  •  ${player.get('bankroll', 0):,}"
            if is_turn:
                title += "  •  PLAYING"
            elif player.get("ready"):
                title += "  •  READY"
            tk.Label(
                panel, text=title, bg=background, fg=GOLD if is_turn else TEXT,
                font=("Segoe UI", 9, "bold"),
            ).pack(pady=(0, 4))

            hands = player.get("hands", [])
            if hands:
                active_hand = int(player.get("active_hand", -1))
                for hand_index, hand in enumerate(hands):
                    hand_row = tk.Frame(panel, bg=background)
                    hand_row.pack(pady=2)
                    cards = tk.Frame(hand_row, bg=background)
                    cards.pack(side="left")
                    self._render_cards(cards, hand.get("cards", []))
                    detail = (
                        f"{hand.get('total', 0)}  ${hand.get('bet', 0)}"
                        + (f"  {hand['result']}" if hand.get("result") else "")
                        + ("  BUST" if hand.get("busted") else "")
                    )
                    tk.Label(
                        hand_row, text=detail, bg=background, fg=TEXT,
                        font=("Segoe UI", 8, "bold"),
                    ).pack(side="left", padx=4)
                    if is_turn and hand_index == active_hand:
                        tk.Label(
                            hand_row, text="▶", bg=background, fg=GOLD,
                            font=("Segoe UI", 10, "bold"),
                        ).pack(side="left")
            elif self.state.get("phase") == "betting":
                bet = int(player.get("bet", MIN_BET))
                tk.Label(
                    panel, text=f"Bet: ${bet}  •  "
                    f"{'OUT OF CHIPS' if player.get('eliminated') else 'waiting for others' if player.get('ready') else 'choose a bet'}",
                    bg=background, fg=MUTED, font=("Segoe UI", 9),
                ).pack(pady=4)

    def _refresh(self) -> None:
        if self.state:
            phase = str(self.state.get("phase", "betting")).upper()
            self.phase_label.config(text=f"LAN TABLE  •  {phase}")
            self.chips_label.config(
                text=f"YOUR CHIPS  ${int(self.state.get('viewer_bankroll', 0)):,}"
            )
            self.status_label.config(
                text=self.waiting or str(self.state.get("message", ""))
            )
            dealer_cards = self.state.get("dealer_cards", [])
            self._render_cards(self.dealer_cards, dealer_cards)
            total = self.state.get("dealer_total")
            self.dealer_total.config(
                text=f"Total: {total}" if total is not None else
                (f"Showing: {dealer_cards[0]}" if dealer_cards else "")
            )
            self._render_players()
        else:
            self.status_label.config(text=self.waiting)

        own = next(
            (
                player for player in self.state.get("players", [])
                if player.get("id") == self.viewer_id
            ),
            {},
        )
        bankroll = int(own.get("bankroll", 1000))
        ready = bool(own.get("ready"))
        phase = self.state.get("phase", "betting")
        self.bet_label.config(text=f"${self.bet:,}")
        can_bet = (
            phase == "betting"
            and not ready
            and own.get("connected", True)
            and not own.get("eliminated", False)
        )
        self.bet_down.config(
            state="normal" if can_bet and self.bet > MIN_BET else "disabled"
        )
        self.bet_up.config(
            state="normal" if can_bet and self.bet + 10 <= bankroll else "disabled"
        )
        eligible_players = [
            player for player in self.state.get("players", [])
            if player.get("connected", True)
            and not player.get("eliminated", False)
            and int(player.get("bankroll", 0)) >= MIN_BET
        ]
        minimum_players = 1 if int(self.state.get("rounds_played", 0)) else 2
        enough_players = len(eligible_players) >= minimum_players
        self.ready_button.config(
            state="normal" if can_bet and enough_players and self.bet <= bankroll
            else "disabled",
            text="READY" if ready else "BET & READY",
        )

        is_turn = bool(self.state.get("is_viewer_turn"))
        self.hit_button.config(state="normal" if is_turn else "disabled")
        self.stand_button.config(state="normal" if is_turn else "disabled")
        own_hands = own.get("hands", [])
        active_index = int(own.get("active_hand", -1))
        active = (
            own_hands[active_index]
            if own.get("is_turn") and 0 <= active_index < len(own_hands)
            else None
        )
        can_double = is_turn and active is not None and len(active.get("cards", [])) == 2
        self.double_button.config(
            state="normal"
            if can_double and bankroll >= int(active.get("bet", 0))
            else "disabled"
        )
        cards = active.get("cards", []) if active is not None else []
        can_split = (
            is_turn and len(cards) == 2 and len(own.get("hands", [])) < 4
            and bankroll >= int(active.get("bet", 0))
            and self._card_value(cards[0]) == self._card_value(cards[1])
            and not active.get("split_aces")
        )
        self.split_button.config(state="normal" if can_split else "disabled")

    @staticmethod
    def _card_value(card: str) -> int:
        rank = card[:-1]
        if rank == "A":
            return 11
        if rank in ("J", "Q", "K"):
            return 10
        return int(rank)

    def _close(self) -> None:
        self.client.close()
        if self.server is not None:
            self.server.stop()
        self.root.destroy()
