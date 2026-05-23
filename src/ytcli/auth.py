import json
import sys
from typing import Any

from google_auth_oauthlib.flow import InstalledAppFlow

BUNDLED_CLIENT_ID: str | None = None
BUNDLED_CLIENT_SECRET: str | None = None

SCOPES = ["https://www.googleapis.com/auth/youtube"]
AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"


def _client_secrets(client_id: str, client_secret: str) -> dict[str, Any]:
    return {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": AUTH_URI,
            "token_uri": TOKEN_URI,
            "redirect_uris": ["http://127.0.0.1", "http://localhost"],
        }
    }


def resolve_oauth_client(config: dict[str, Any]) -> tuple[str, str]:
    oc = config.get("oauth_client") or {}
    cid, csec = oc.get("client_id"), oc.get("client_secret")
    if cid and csec:
        return cid, csec
    if BUNDLED_CLIENT_ID and BUNDLED_CLIENT_SECRET:
        return BUNDLED_CLIENT_ID, BUNDLED_CLIENT_SECRET
    print(
        "No OAuth client configured.\n"
        "Create one at https://console.cloud.google.com/apis/credentials\n"
        "(Application type: 'Desktop app'), then paste the values below.",
        file=sys.stderr,
    )
    cid = input("Client ID: ").strip()
    csec = input("Client secret: ").strip()
    if not cid or not csec:
        raise SystemExit("Client ID and secret are required.")
    return cid, csec


def register(config: dict[str, Any]) -> dict[str, Any]:
    cid, csec = resolve_oauth_client(config)
    flow = InstalledAppFlow.from_client_config(_client_secrets(cid, csec), SCOPES)
    creds = flow.run_local_server(
        port=0,
        open_browser=True,
        access_type="offline",
        prompt="consent",
    )
    config["oauth_client"] = {"client_id": cid, "client_secret": csec}
    config["credentials"] = json.loads(creds.to_json())
    return config
