"""Entry point for the Pacman TUI client.

Usage:
    python -m pacman --host localhost:8000
"""

import argparse
import sys


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="pacman",
        description="Multiplayer Pacman TUI client",
    )
    parser.add_argument(
        "--host",
        required=True,
        help="Game server host (e.g. localhost:8000)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Run the Pacman TUI client."""
    args = parse_args(argv)
    host = args.host
    # Normalize the host into a WebSocket URL
    if not host.startswith(("ws://", "wss://")):
        url = f"ws://{host}/ws"
    elif not host.endswith("/ws"):
        url = f"{host}/ws"
    else:
        url = host

    print(f"Connecting to {url}...")
    # App launch will be wired in Task 7
    sys.exit(0)


if __name__ == "__main__":
    main()
