# Agent notes

Guidance for coding agents (Claude Code, Codex, Cursor, etc.) working in this
repo. User-facing docs are in `README.md`; this file is the developer/agent
contract.

## Layout

```
src/ytcli/
  cli.py       argparse wiring + _cmd_* handlers + shared helpers
  auth.py      OAuth flow (InstalledAppFlow, Desktop client)
  client.py    builds the YouTube Data API client; refreshes creds
  config.py    XDG config path; atomic 0600 save
```

Entry point: `ytcli = "ytcli.cli:main"` (see `pyproject.toml`).

## Run / test

```sh
pip install -e .
ytcli <command>
```

No test suite, linter, or type-checker is configured. Don't add one without
asking.

## Conventions — follow these when adding commands

- **`--format`** on every data-emitting command. Wire it with
  `_add_format_flag(p)` (or `_add_list_flags(p)` if the command also takes
  `--max`). Emit rows via `_emit(items, args.format, COLUMNS)`. Declare a
  `ColumnSpec` constant near the other ones in `cli.py`; don't inline column
  definitions in handlers.
- **Pagination** uses `_paginate(list_fn, max_items, **params)`. Pass the
  bound `.list` (not `.list()`); `_paginate` injects `pageToken`. Default
  `maxResults=50`.
- **Video arguments** must pass through `_extract_video_id(value)` — accepts
  an 11-char ID or any youtube.com / youtu.be / m.youtube.com /
  music.youtube.com URL (watch / shorts / live / embed / v).
- **Scoped help.** Subcommand groups (`playlists`, `playlist`) call
  `parser.set_defaults(func=_help_for(group_parser))` so `ytcli playlists`
  with no action prints help to stdout and exits 0.
- **Errors are centralized.** `main()` catches `HttpError` and `RefreshError`
  and prints a one-line message to stderr. Do not wrap individual `_cmd_*`
  handlers in try/except for API errors. If a handler needs to fail for a
  user-input reason (validation, ambiguity), print to stderr and `return 1`.
- **Ambiguous mutations fail loudly.** When a playlist item lookup matches
  more than one row: `move-item` errors unconditionally; `remove-item`
  errors unless `--all`. Print every match to stderr (position + id) before
  giving up.
- **Destructive ops confirm.** `playlists delete` prompts unless `-y`, and
  refuses to run non-interactively without `-y`. Mirror this pattern for any
  future destructive command.

## Quota

The YouTube Data API has a 10,000-unit/day default quota. Most reads cost
1 unit; **`search` costs 100 units per call**. Be conservative — don't add
search-based features when a cheaper endpoint exists, and don't auto-paginate
search results beyond what the user asked for.

## Config & secrets

- Stored at `$XDG_CONFIG_HOME/ytcli/ytcli.config.json` (or
  `~/.config/ytcli/...`), 0600. Lives outside the repo.
- Never commit OAuth client_id/secret or credentials to the repo. The
  `BUNDLED_CLIENT_*` constants in `auth.py` stay `None` in source — they're
  a hook for downstream packaging, not for checking in real values.
- OAuth scope: `https://www.googleapis.com/auth/youtube` (full read/write).
  Don't widen without a concrete reason.

## Web sandbox quirks (Claude Code on the web)

The remote git proxy only permits pushes to the assigned feature branch.
Tag pushes and `--delete` of remote branches return HTTP 403. Do those from
a local checkout (or the GitHub web UI).
