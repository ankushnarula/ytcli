import argparse
import json
import re
import sys
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse

from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError

from . import auth, client, config


_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def _extract_video_id(value: str) -> str:
    s = value.strip()
    if _VIDEO_ID_RE.match(s):
        return s
    parsed = urlparse(s if "://" in s else f"https://{s}")
    host = (parsed.hostname or "").lower().removeprefix("www.")
    candidate: str | None = None
    if host == "youtu.be":
        candidate = parsed.path.lstrip("/").split("/", 1)[0]
    elif host in ("youtube.com", "m.youtube.com", "music.youtube.com"):
        if parsed.path == "/watch":
            v = parse_qs(parsed.query).get("v")
            if v:
                candidate = v[0]
        else:
            parts = parsed.path.lstrip("/").split("/")
            if len(parts) >= 2 and parts[0] in ("shorts", "live", "embed", "v"):
                candidate = parts[1]
    if candidate and _VIDEO_ID_RE.match(candidate):
        return candidate
    raise SystemExit(
        f"Could not extract a YouTube video ID from: {value!r}\n"
        "Expected an 11-character ID or a youtube.com/youtu.be URL."
    )


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


ColumnSpec = list[tuple[str, Callable[[dict], Any]]]


def _emit(items: list[dict], fmt: str, columns: ColumnSpec) -> None:
    if fmt == "json":
        print(json.dumps(items, indent=2))
        return
    rows = [[str(getter(it)) for _, getter in columns] for it in items]
    if fmt == "tsv":
        for r in rows:
            print("\t".join(r))
        return
    # table
    headers = [name for name, _ in columns]
    widths = [
        max(len(headers[i]), max((len(r[i]) for r in rows), default=0))
        for i in range(len(headers))
    ]
    line = "  ".join(f"{{:<{w}}}" for w in widths)
    print(line.format(*headers))
    print(line.format(*("-" * w for w in widths)))
    for r in rows:
        print(line.format(*r))


PLAYLISTS_COLUMNS: ColumnSpec = [
    ("playlistId", lambda it: it["id"]),
    ("items", lambda it: it["contentDetails"]["itemCount"]),
    ("title", lambda it: it["snippet"]["title"]),
]


PLAYLIST_ITEMS_COLUMNS: ColumnSpec = [
    ("pos", lambda it: it["snippet"]["position"]),
    ("playlistItemId", lambda it: it["id"]),
    ("videoId", lambda it: it["snippet"]["resourceId"]["videoId"]),
    ("title", lambda it: it["snippet"]["title"]),
]


PLAYLIST_CREATED_COLUMNS: ColumnSpec = [
    ("playlistId", lambda it: it["id"]),
    ("title", lambda it: it["snippet"]["title"]),
]


PLAYLIST_ITEM_ADDED_COLUMNS: ColumnSpec = [
    ("playlistItemId", lambda it: it["id"]),
    ("videoId", lambda it: it["snippet"]["resourceId"]["videoId"]),
    ("title", lambda it: it["snippet"]["title"]),
]


def _cmd_playlists_list(args: argparse.Namespace) -> int:
    yt = client.youtube()
    items = _paginate(
        yt.playlists().list,
        args.max,
        part="snippet,contentDetails",
        mine=True,
        maxResults=50,
    )
    _emit(items, args.format, PLAYLISTS_COLUMNS)
    return 0


def _cmd_playlist_list(args: argparse.Namespace) -> int:
    yt = client.youtube()
    items = _paginate(
        yt.playlistItems().list,
        args.max,
        part="snippet",
        playlistId=args.playlist_id,
        maxResults=50,
    )
    _emit(items, args.format, PLAYLIST_ITEMS_COLUMNS)
    return 0


def _cmd_playlists_create(args: argparse.Namespace) -> int:
    yt = client.youtube()
    snippet: dict[str, Any] = {"title": args.title}
    if args.description is not None:
        snippet["description"] = args.description
    body = {"snippet": snippet, "status": {"privacyStatus": args.privacy}}
    pl = yt.playlists().insert(part="snippet,status", body=body).execute()
    _emit([pl], args.format, PLAYLIST_CREATED_COLUMNS)
    return 0


def _cmd_playlists_delete(args: argparse.Namespace) -> int:
    if not args.yes:
        if not sys.stdin.isatty():
            print(
                f"Refusing to delete {args.playlist_id} without --yes "
                "in a non-interactive shell.",
                file=sys.stderr,
            )
            return 1
        reply = input(
            f"Delete playlist {args.playlist_id}? This cannot be undone. [y/N] "
        ).strip().lower()
        if reply not in ("y", "yes"):
            print("Cancelled.")
            return 1
    yt = client.youtube()
    yt.playlists().delete(id=args.playlist_id).execute()
    print(f"Deleted playlist {args.playlist_id}")
    return 0


def _cmd_playlist_add_item(args: argparse.Namespace) -> int:
    video_id = _extract_video_id(args.video_id)
    yt = client.youtube()
    snippet: dict[str, Any] = {
        "playlistId": args.playlist_id,
        "resourceId": {"kind": "youtube#video", "videoId": video_id},
    }
    if args.position is not None:
        snippet["position"] = args.position
    item = yt.playlistItems().insert(part="snippet", body={"snippet": snippet}).execute()
    _emit([item], args.format, PLAYLIST_ITEM_ADDED_COLUMNS)
    return 0


def _cmd_playlist_remove_item(args: argparse.Namespace) -> int:
    video_id = _extract_video_id(args.video_id)
    yt = client.youtube()
    matches = _paginate(
        yt.playlistItems().list,
        None,
        part="id,snippet",
        playlistId=args.playlist_id,
        videoId=video_id,
        maxResults=50,
    )
    if not matches:
        print(
            f"Video {video_id} is not in playlist {args.playlist_id}.",
            file=sys.stderr,
        )
        return 1
    if len(matches) > 1 and not args.all:
        print(
            f"Video {video_id} appears {len(matches)} times in playlist "
            f"{args.playlist_id}:",
            file=sys.stderr,
        )
        for m in matches:
            print(
                f"  position {m['snippet']['position']}\t{m['id']}",
                file=sys.stderr,
            )
        print("Re-run with --all to remove every occurrence.", file=sys.stderr)
        return 1
    for m in matches:
        yt.playlistItems().delete(id=m["id"]).execute()
        print(f"Removed playlist item {m['id']} (position {m['snippet']['position']})")
    return 0


def _add_format_flag(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "--format",
        choices=["tsv", "table", "json"],
        default="tsv",
        help="Output format (default: tsv).",
    )


def _add_list_flags(p: argparse.ArgumentParser) -> None:
    _add_format_flag(p)
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

    pls_create = pls_sub.add_parser("create", help="Create a new playlist.")
    pls_create.add_argument("title", help="Playlist title.")
    pls_create.add_argument("--description", default=None, help="Playlist description.")
    pls_create.add_argument(
        "--privacy",
        choices=["private", "unlisted", "public"],
        default="private",
        help="Privacy setting (default: private).",
    )
    _add_format_flag(pls_create)
    pls_create.set_defaults(func=_cmd_playlists_create)

    pls_delete = pls_sub.add_parser("delete", help="Delete a playlist.")
    pls_delete.add_argument("playlist_id", help="YouTube playlist ID.")
    pls_delete.add_argument(
        "-y", "--yes", action="store_true", help="Skip the confirmation prompt."
    )
    pls_delete.set_defaults(func=_cmd_playlists_delete)

    p_playlist = sub.add_parser("playlist", help="Operate on a single playlist.")
    p_playlist.set_defaults(func=_help_for(p_playlist))
    pl_sub = p_playlist.add_subparsers(dest="action", metavar="<action>")

    pl_list = pl_sub.add_parser("list", help="List the items in a playlist.")
    pl_list.add_argument("playlist_id", help="YouTube playlist ID.")
    _add_list_flags(pl_list)
    pl_list.set_defaults(func=_cmd_playlist_list)

    pl_add = pl_sub.add_parser("add-item", help="Add a video to a playlist.")
    pl_add.add_argument("playlist_id", help="YouTube playlist ID.")
    pl_add.add_argument(
        "video_id",
        help="YouTube video ID or any youtube.com/youtu.be URL.",
    )
    pl_add.add_argument(
        "--position", type=int, default=None, help="0-based insert position (default: end)."
    )
    _add_format_flag(pl_add)
    pl_add.set_defaults(func=_cmd_playlist_add_item)

    pl_remove = pl_sub.add_parser("remove-item", help="Remove a video from a playlist.")
    pl_remove.add_argument("playlist_id", help="YouTube playlist ID.")
    pl_remove.add_argument(
        "video_id",
        help="YouTube video ID or any youtube.com/youtu.be URL.",
    )
    pl_remove.add_argument(
        "--all",
        action="store_true",
        help="Remove every occurrence if the video appears in the playlist multiple times.",
    )
    pl_remove.set_defaults(func=_cmd_playlist_remove_item)

    return parser


def _format_http_error(e: HttpError) -> str:
    status = getattr(getattr(e, "resp", None), "status", None) or "?"
    try:
        body = json.loads(e.content).get("error", {})
    except (ValueError, TypeError, AttributeError):
        body = {}
    errors = body.get("errors") or []
    reason = errors[0].get("reason", "") if errors else ""
    message = body.get("message", "")
    head = f"HTTP {status}" + (f" {reason}" if reason else "")
    return f"{head}: {message}" if message else head


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return 130
    except RefreshError:
        print(
            "Credentials expired or revoked. Run: ytcli register",
            file=sys.stderr,
        )
        return 1
    except HttpError as e:
        print(_format_http_error(e), file=sys.stderr)
        return 1
