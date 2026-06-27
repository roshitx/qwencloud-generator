#!/usr/bin/env python3
"""Shared multi-account Gmail OAuth token store.

Config file: gmail_tokens.json
{
  "default_client": {"client_id": "...", "client_secret": "..."},
  "accounts": {
    "foo@gmail.com": {"refresh_token": "...", "access_token": "...", "expires_at": 1234567890}
  }
}
"""
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List

TOKEN_FILE = Path(__file__).parent / "gmail_tokens.json"
CLIENT_SECRET_FILE = Path(__file__).parent / "client_secret.json"
DEFAULT_EMAIL = "yourname@gmail.com"


def _default_client() -> Dict[str, str]:
    if CLIENT_SECRET_FILE.exists():
        try:
            c = json.loads(CLIENT_SECRET_FILE.read_text())["installed"]
            return {"client_id": c["client_id"], "client_secret": c["client_secret"]}
        except Exception:
            pass
    # fallback to the client used by existing tokens in this repo
    return {
        "client_id": "YOUR_CLIENT_ID",
        "client_secret": "YOUR_CLIENT_SECRET",
    }


def load_tokens(path: Path = None) -> Dict[str, Any]:
    path = Path(path or TOKEN_FILE)
    if not path.exists():
        return {"default_client": _default_client(), "accounts": {}}

    data = json.loads(path.read_text())

    # migrate legacy flat token file
    if "accounts" not in data:
        legacy = dict(data)
        accounts: Dict[str, Any] = {}
        if "refresh_token" in legacy:
            legacy.setdefault("client_id", _default_client()["client_id"])
            legacy.setdefault("client_secret", _default_client()["client_secret"])
            accounts[DEFAULT_EMAIL] = legacy
        data = {"default_client": _default_client(), "accounts": accounts}

    if "default_client" not in data:
        data["default_client"] = _default_client()

    return data


def save_tokens(data: Dict[str, Any], path: Path = None) -> None:
    path = Path(path or TOKEN_FILE)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(path)


def _account(data: Dict[str, Any], email: str) -> Dict[str, Any]:
    return data["accounts"].setdefault(email, {})


def _client_creds(data: Dict[str, Any], email: str) -> tuple:
    acc = _account(data, email)
    cid = acc.get("client_id") or data["default_client"]["client_id"]
    csec = acc.get("client_secret") or data["default_client"]["client_secret"]
    return cid, csec


def refresh_access_token(email: str, data: Dict[str, Any] = None) -> str:
    if data is None:
        data = load_tokens()
    acc = _account(data, email)
    rt = acc.get("refresh_token")
    if not rt:
        raise RuntimeError(f"no refresh_token for {email}; run OAuth setup first")

    cid, csec = _client_creds(data, email)
    body = urllib.parse.urlencode({
        "client_id": cid,
        "client_secret": csec,
        "refresh_token": rt,
        "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    resp = json.loads(urllib.request.urlopen(req).read())
    acc["access_token"] = resp["access_token"]
    acc["expires_at"] = int(time.time()) + resp.get("expires_in", 3600)
    acc["token_type"] = resp.get("token_type", "Bearer")
    save_tokens(data)
    return acc["access_token"]


def normalize_gmail(email: str) -> str:
    """Map a Gmail alias (dots/plus labels) to its real inbox address."""
    try:
        local, domain = email.rsplit("@", 1)
    except ValueError:
        return email
    if domain.lower() in ("gmail.com", "googlemail.com"):
        local = local.replace(".", "")
        if "+" in local:
            local = local.split("+", 1)[0]
    return f"{local}@{domain}"


def get_access_token(email: str) -> str:
    data = load_tokens()
    email = normalize_gmail(email)
    acc = _account(data, email)
    if acc.get("access_token") and acc.get("expires_at", 0) > time.time() + 60:
        return acc["access_token"]
    if acc.get("refresh_token"):
        return refresh_access_token(email, data)
    raise RuntimeError(f"no token for {email}; run OAuth setup first")


def get_auth_header(email: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {get_access_token(email)}"}


def exchange_code(email: str, code: str, redirect_uri: str = "http://localhost:8085/callback") -> Dict[str, Any]:
    data = load_tokens()
    cid, csec = _client_creds(data, email)
    body = urllib.parse.urlencode({
        "code": code,
        "client_id": cid,
        "client_secret": csec,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }).encode()
    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    resp = json.loads(urllib.request.urlopen(req).read())
    acc = _account(data, email)
    acc.update(resp)
    acc["client_id"] = cid
    acc["client_secret"] = csec
    acc["expires_at"] = int(time.time()) + resp.get("expires_in", 3600)
    save_tokens(data)
    return acc


def list_accounts() -> List[str]:
    return list(load_tokens().get("accounts", {}).keys())


def store_token(email: str, token_dict: Dict[str, Any]) -> None:
    data = load_tokens()
    acc = _account(data, email)
    acc.update(token_dict)
    acc["client_id"] = acc.get("client_id") or data["default_client"]["client_id"]
    acc["client_secret"] = acc.get("client_secret") or data["default_client"]["client_secret"]
    if "expires_in" in acc and "expires_at" not in acc:
        acc["expires_at"] = int(time.time()) + acc["expires_in"]
    save_tokens(data)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        print(get_access_token(sys.argv[1]))
    else:
        print("accounts:", list_accounts())
