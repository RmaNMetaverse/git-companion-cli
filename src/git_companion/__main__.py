import argparse
import sys
from pathlib import Path

from . import __version__


def main():
    parser = argparse.ArgumentParser(description="A colorful terminal cockpit for Git and Git LFS.")
    parser.add_argument(
        "path", nargs="?", default=".", help="Workspace directory (default: current directory)"
    )
    parser.add_argument(
        "--no-install", action="store_true", help="Do not automatically install missing Git tools"
    )
    parser.add_argument("--ascii", action="store_true", help="Use ASCII decoration instead of Unicode art")
    parser.add_argument("--version", action="version", version=f"git-companion {__version__}")
    args = parser.parse_args()
    path = Path(args.path).expanduser().resolve()
    if not path.is_dir():
        parser.error(f"Directory does not exist: {path}")
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        parser.error("This app needs an interactive terminal. Run git-companion from your terminal.")
    from .app import CompanionApp

    CompanionApp(path, auto_install=not args.no_install, ascii_only=args.ascii).run()


if __name__ == "__main__":
    main()
