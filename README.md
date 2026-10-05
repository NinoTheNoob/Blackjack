# Blackjack

A Windows blackjack game with solo play and multiplayer over a local Wi-Fi/LAN.
The game uses Python's built-in Tkinter interface and needs no third-party
packages to play.

## Play from Python

Install Python 3.10 or newer, then choose Solo, Host LAN Game, or Join LAN Game:

```text
py main.py
```

To join a LAN game, enter the host's displayed address (for example,
`192.168.1.12:47920`); the game accepts it with or without the `:47920` port.
Both computers must be on the same Wi-Fi/LAN, the host must keep the game
running, and the host may need to allow Blackjack through the Windows firewall
(TCP port 47920).
The game opens as a normal desktop window (not a tray app); close its window to
exit.

If you run out of chips in solo mode, the game asks whether you want to restart
with $1,000.

## Build a standalone Windows executable

Double-click `build.bat`. It installs PyInstaller and creates:

```text
dist\Blackjack.exe
```

Close the game before rebuilding so Windows can replace the existing
`dist\Blackjack.exe`. The build script checks for a running copy and reports
its process ID rather than starting a build that will fail with a file-lock
error.

The resulting executable includes the Python runtime; Python is not needed on
the computer that runs it. The first build requires an internet connection to
download PyInstaller.

## Rules

- Start with $1,000 in chips; bets start at $20 and adjust in $10 increments.
- Blackjack pays 3:2. Even bets ensure payouts are exact whole-dollar amounts.
- The dealer stands on all 17s. A six-deck shoe is reshuffled when fewer than
  52 cards remain.
- Hit, stand, double down on the first two cards, and split matching-value pairs.
- Split up to four hands. Split aces receive one card each and cannot be
  resplit.
- A two-card 21 after splitting pays as a regular winning hand, not a natural
  blackjack.
- If you run out of chips in solo mode, choose whether to restart or exit.
- LAN tables support two to six players. The host controls the authoritative
  shared shoe and turn order; disconnected players automatically stand.

## Run the game tests

```text
py -m unittest -v
```

## Support the game

Enjoying Blackjack? You can support its development with a coffee:

<p align="center">
  <a href="https://ko-fi.com/nin0">
    <img src="https://ko-fi.com/img/githubbutton_sm.svg" alt="Support me on Ko-fi" width="200">
  </a>
</p>
