import argparse
import json
from typing import Any, Callable, Iterable

from . import auth, client, config


def _cmd_register(args: argparse.Namespace) -> int:
    cfg = config.load()
    cfg = auth.register(cfg, reset=args.reset)
    config.save(cfg)
    print(f"Credentials saved to {config.CONFIG_PATH}")
    return 0


def _cmd_unregister(args: argparse.Namespace) -> int:
    cfg = config.load()
    cfg, cleared = auth.unregister(cfg, all_=args.all)
    if not cleared:
        print("Nothing to clear.")
        return 0
    config.save(cfg)
    print(f"Cleared from {config.CONFIG_PATH}: {', '.join(cleared)}")
    return 0


def _paginate(list_fn: Callable[..., Any], max_items: int | None, **params: Any) -> list[dict]:
    items: list[dict] = []
    page_token: str | None = None
    while True:
        resp = list_fn(pageToken=page_token, **params).execute()
        items.extend(resp.get("items", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
        if max_items is not None and len(items) >= max_items:
            break
    if max_items is not None:
        items = items[:max_items]
    return items


def _emit(items: Iterable[dict], as_json: bool, formatter: Callable[[dict], str]) -> None:
    if as_json:
        print(json.dumps(list(items), indent=2))
        return
    for it in items:
        print(formatter(it))


def _cmd_playlists_list(args: argparse.Namespace) -> int:
    yt = client.youtube()
    items = _paginate(
        yt.playlists().list,
        args.max,
        part="snippet,contentDetails",
        mine=True,
        maxResults=50,
    )
    _emit(
        items,
        args.json,
        lambda it: f"{it['id']}\t{it['contentDetails']['itemCount']:>4}\t{it['snippet']['title']}",
    )
    return 0


def _cmd_playlist_list(args: argparse.Namespace) -> int:
    yt = client.youtube()
    items = _paginate(
        yt.playlistItems().list,
        args.max,
        part="snippet,contentDetails",
        playlistId=args.playlist_id,
        maxResults=50,
    )
    _emit(
        items,
        args.json,
        lambda it: (
            f"{it['snippet']['position']:>3}  "
            f"{it['contentDetails']['videoId']}  "
            f"{it['snippet']['title']}"
        ),
    )
    return 0


def _add_list_flags(p: argparse.ArgumentParser) -> None:
    p.add_argument("--json", action="store_true", help="Emit raw JSON.")
    p.add_argument("--max", type=int, default=None, help="Cap the number of items returned.")


def _help_for(parser: argparse.ArgumentParser) -> Callable[[argparse.Namespace], int]:
    def _show(_args: argparse.Namespace) -> int:
        parser.print_help()
        return 0
    return _show


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ytcli",
        description="Command-line client for the YouTube Data API.",
    )
    parser.set_defaults(func=_help_for(parser))
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    p_register = sub.add_parser("register", help="Authenticate with YouTube and store credentials.")
    p_register.add_argument(
        "--reset",
        action="store_true",
        help="Re-prompt for client_id/secret even if already saved.",
    )
    p_register.set_defaults(func=_cmd_register)

    p_unregister = sub.add_parser("unregister", help="Clear stored credentials.")
    p_unregister.add_argument(
        "--all",
        action="store_true",
        help="Also clear the saved OAuth client_id/secret (full reset).",
    )
    p_unregister.set_defaults(func=_cmd_unregister)

    p_playlists = sub.add_parser("playlists", help="Operate on the collection of your playlists.")
    p_playlists.set_defaults(func=_help_for(p_playlists))
    pls_sub = p_playlists.add_subparsers(dest="action", metavar="<action>")
    pls_list = pls_sub.add_parser("list", help="List the authenticated user's playlists.")
    _add_list_flags(pls_list)
    pls_list.set_defaults(func=_cmd_playlists_list)

    p_playlist = sub.add_parser("playlist", help="Operate on a single playlist.")
    p_playlist.set_defaults(func=_help_for(p_playlist))
    pl_sub = p_playlist.add_subparsers(dest="action", metavar="<action>")
    pl_list = pl_sub.add_parser("list", help="List the items in a playlist.")
    pl_list.add_argument("playlist_id", help="YouTube playlist ID.")
    _add_list_flags(pl_list)
    pl_list.set_defaults(func=_cmd_playlist_list)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
