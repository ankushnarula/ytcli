import json

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from . import config


def _load_credentials() -> Credentials:
    cfg = config.load()
    cred_info = cfg.get("credentials")
    if not cred_info:
        raise SystemExit("Not authenticated. Run: ytcli register")

    creds = Credentials.from_authorized_user_info(cred_info, cred_info.get("scopes"))

    if not creds.valid:
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            cfg["credentials"] = json.loads(creds.to_json())
            config.save(cfg)
        else:
            raise SystemExit("Credentials invalid or revoked. Re-run: ytcli register")

    return creds


def youtube():
    return build(
        "youtube", "v3",
        credentials=_load_credentials(),
        cache_discovery=False,
    )
