"""Entry point for the Pacman TUI client.

Usage:
    python -m pacman --host localhost:8000
    python -m pacman --host localhost:8000 --name MyTeam
"""

import argparse

from pacman.app import PacmanApp


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
    parser.add_argument(
        "--name",
        default="Player",
        help="Player display name (default: Player)",
    )
    return parser.parse_args(argv)


def normalize_url(host: str) -> str:
    """Normalize a host string into a WebSocket URL.

    Args:
        host: Host string (e.g. 'localhost:8000' or 'ws://host/ws').

    Returns:
        A fully qualified WebSocket URL.
    """
    if not host.startswith(("ws://", "wss://")):
        return f"ws://{host.rstrip('/')}/ws"
    # If user provided a full ws:// or wss:// URL, trust it as-is
    return host


def main(argv: list[str] | None = None) -> None:
    """Run the Pacman TUI client."""
    args = parse_args(argv)
    url = normalize_url(args.host)
    app = PacmanApp(url=url, player_name=args.name)
    app.run()


if __name__ == "__main__":
    main()
