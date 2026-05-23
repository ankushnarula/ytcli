import argparse
import json
import sys
from typing import Any, Callable, Iterable

from . import auth, client, config


def _cmd_register(_args: argparse.Namespace) -> int:
    cfg = config.load()
    cfg = auth.register(cfg)
    config.save(cfg)
    print(f"Credentials saved to {config.CONFIG_PATH}")
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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ytcli",
        description="Command-line client for the YouTube Data API.",
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    p_register = sub.add_parser("register", help="Authenticate with YouTube and store credentials.")
    p_register.set_defaults(func=_cmd_register)

    p_playlists = sub.add_parser("playlists", help="Operate on the collection of your playlists.")
    pls_sub = p_playlists.add_subparsers(dest="action", metavar="<action>")
    pls_list = pls_sub.add_parser("list", help="List the authenticated user's playlists.")
    _add_list_flags(pls_list)
    pls_list.set_defaults(func=_cmd_playlists_list)

    p_playlist = sub.add_parser("playlist", help="Operate on a single playlist.")
    pl_sub = p_playlist.add_subparsers(dest="action", metavar="<action>")
    pl_list = pl_sub.add_parser("list", help="List the items in a playlist.")
    pl_list.add_argument("playlist_id", help="YouTube playlist ID.")
    _add_list_flags(pl_list)
    pl_list.set_defaults(func=_cmd_playlist_list)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help(sys.stderr)
        return 2
    return args.func(args)
