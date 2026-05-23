import argparse
import sys

from . import auth, config


def _cmd_register(_args: argparse.Namespace) -> int:
    cfg = config.load()
    cfg = auth.register(cfg)
    config.save(cfg)
    print(f"Credentials saved to {config.CONFIG_PATH}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ytcli",
        description="Command-line client for the YouTube Data API.",
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    p_register = sub.add_parser(
        "register",
        help="Authenticate with YouTube and store credentials.",
    )
    p_register.set_defaults(func=_cmd_register)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help(sys.stderr)
        return 2
    return args.func(args)
