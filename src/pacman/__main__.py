"""Entry point for the Pacman TUI client.

Usage:
    python -m pacman --host localhost:8000
    python -m pacman --host localhost:8000 --name MyTeam
"""

import argparse
import sys

from pacman.app import PacmanApp

# Server enforces 1-30 characters after trimming whitespace
MAX_NAME_LENGTH = 30


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
    name = args.name.strip()
    if not name or len(name) > MAX_NAME_LENGTH:
        print(
            f"Error: Player name must be 1-{MAX_NAME_LENGTH} characters "
            f"(got {len(name)} after trimming).",
            file=sys.stderr,
        )
        sys.exit(1)
    app = PacmanApp(url=url, player_name=name)
    app.run()


if __name__ == "__main__":
    main()
