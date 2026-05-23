# ytcli

Command-line client for the YouTube Data API. Initial focus: managing the authenticated user's playlists.

## Install

```sh
pip install -e .
```

## First-time setup

```sh
ytcli register
```

This authenticates with Google via OAuth. On first run you'll need an OAuth
client (Application type: **Desktop app**) from
https://console.cloud.google.com/apis/credentials — `ytcli` will prompt for the
client ID and secret, then open a browser to complete the consent flow.
Credentials are stored in `~/.config/ytcli/ytcli.config.json` (chmod 600).

Re-run `ytcli register` at any time to re-authenticate.

## Commands

```sh
ytcli register   [--reset]                                   # OAuth setup; --reset re-prompts for client_id/secret
ytcli unregister [--all]                                     # Clear credentials; --all also clears the OAuth client

ytcli playlists list   [--format tsv|table|json] [--max N]   # Your playlists
ytcli playlists create <title> [--description D]             #   ...new playlist (default privacy: private)
                       [--privacy private|unlisted|public]
                       [--format tsv|table|json]
ytcli playlists delete <playlist_id> [-y]                    #   ...delete (prompts unless -y)

ytcli playlist list <playlist_id>                            # Items in a playlist
                    [--format tsv|table|json] [--max N]
ytcli playlist add-item <playlist_id> <video>                #   ...append (or --position N)
                        [--position N] [--format tsv|table|json]
ytcli playlist remove-item <playlist_id> <video> [--all]     #   ...remove (errors on duplicates without --all)
```

`<video>` is either an 11-char YouTube video ID or any youtube.com/youtu.be URL.

**Output formats** (all data-emitting commands):
- `tsv` (default) — tab-separated, no headers. Script-friendly: pipe to `cut`, `awk`, etc.
- `table` — aligned columns with headers + separator. For interactive reading.
- `json` — the raw YouTube Data API resource objects. For `jq` pipelines.

`playlists list` lists your playlists. `playlist list <id>` lists the items
inside one playlist. Both auto-paginate; `--max` caps the result count and
`--json` emits the raw YouTube Data API resource objects.

## Config

Location: `$XDG_CONFIG_HOME/ytcli/ytcli.config.json`, or
`~/.config/ytcli/ytcli.config.json` if `XDG_CONFIG_HOME` is unset.

```json
{
  "oauth_client": { "client_id": "...", "client_secret": "..." },
  "credentials":  { "token": "...", "refresh_token": "...", "scopes": [...] }
}
```
