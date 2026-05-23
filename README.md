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
ytcli register                         # OAuth setup (run once)
ytcli playlists list [--json] [--max N]
ytcli playlist  list <playlist_id> [--json] [--max N]
```

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
