from __future__ import annotations

import json
import os
import shutil
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_STORE_PATH = Path("data/app_state/watchlists.json")
VALID_ALERT_STATUSES = {"viewed", "dismissed"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_path(path: Path | str | None = None) -> Path:
    return Path(path) if path is not None else DEFAULT_STORE_PATH


def _empty_store() -> dict[str, Any]:
    return {"users": {}}


def _validate_user_token(user_token: str) -> str:
    if not isinstance(user_token, str) or not user_token.strip():
        raise ValueError("user_token must be a non-empty string")
    return user_token.strip()


def _ensure_user(data: dict[str, Any], user_token: str) -> dict[str, Any]:
    users = data.setdefault("users", {})
    return users.setdefault(user_token, {"watchlist": [], "alert_history": []})


def load_store(path: Path | str | None = None) -> dict[str, Any]:
    store_path = _resolve_path(path)
    if not store_path.exists():
        data = _empty_store()
        save_store(data, store_path)
        return data

    try:
        with store_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError:
        data = _empty_store()

    if not isinstance(data, dict):
        data = _empty_store()
    data.setdefault("users", {})
    return data


def save_store(data: dict[str, Any], path: Path | str | None = None) -> None:
    store_path = _resolve_path(path)
    store_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = store_path.with_name(f"{store_path.name}.tmp")
    with tmp_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")
    try:
        os.replace(tmp_path, store_path)
    except PermissionError:
        # Some Windows test sandboxes intermittently deny atomic replace on
        # temp files. Fall back to a direct copy so local state updates still
        # complete; this store is a demo JSON file, not a transactional DB.
        shutil.copyfile(tmp_path, store_path)
        tmp_path.unlink(missing_ok=True)


def get_user_watchlist(user_token: str, path: Path | str | None = None) -> list[dict[str, Any]]:
    token = _validate_user_token(user_token)
    data = load_store(path)
    user = _ensure_user(data, token)
    return deepcopy(user.get("watchlist") or [])


def add_watchlist_item(user_token: str, item: dict[str, Any], path: Path | str | None = None) -> dict[str, Any]:
    token = _validate_user_token(user_token)
    if not isinstance(item, dict):
        raise ValueError("item must be an object")
    if item.get("product_oid") is None or not item.get("point_code"):
        raise ValueError("item.product_oid and item.point_code are required")

    data = load_store(path)
    user = _ensure_user(data, token)
    watchlist = user.setdefault("watchlist", [])
    product_oid = int(item["product_oid"])
    point_code = str(item["point_code"])

    normalized = {
        "product_oid": product_oid,
        "product_name": item.get("product_name"),
        "package_quantity": item.get("package_quantity"),
        "category_name": item.get("category_name"),
        "point_code": point_code,
        "point_name": item.get("point_name") or point_code,
        "added_at": item.get("added_at") or _now_iso(),
    }

    for index, existing in enumerate(watchlist):
        if int(existing.get("product_oid")) == product_oid and str(existing.get("point_code")) == point_code:
            watchlist[index] = {**existing, **normalized, "added_at": existing.get("added_at") or normalized["added_at"]}
            save_store(data, path)
            return {"items": deepcopy(watchlist), "warning": "Item already existed; updated existing item."}

    watchlist.append(normalized)
    save_store(data, path)
    return {"items": deepcopy(watchlist), "warning": None}


def remove_watchlist_item(
    user_token: str,
    product_oid: int,
    point_code: str,
    path: Path | str | None = None,
) -> dict[str, Any]:
    token = _validate_user_token(user_token)
    data = load_store(path)
    user = _ensure_user(data, token)
    watchlist = user.setdefault("watchlist", [])
    before_count = len(watchlist)
    user["watchlist"] = [
        item
        for item in watchlist
        if not (int(item.get("product_oid")) == int(product_oid) and str(item.get("point_code")) == str(point_code))
    ]
    warning = None if len(user["watchlist"]) < before_count else "Watchlist item not found."
    save_store(data, path)
    return {"items": deepcopy(user["watchlist"]), "warning": warning}


def get_alert_history(user_token: str, path: Path | str | None = None) -> list[dict[str, Any]]:
    token = _validate_user_token(user_token)
    data = load_store(path)
    user = _ensure_user(data, token)
    return deepcopy(user.get("alert_history") or [])


def set_alert_status(user_token: str, alert_status: dict[str, Any], path: Path | str | None = None) -> dict[str, Any]:
    token = _validate_user_token(user_token)
    if not isinstance(alert_status, dict):
        raise ValueError("alert must be an object")
    status = alert_status.get("status")
    if status not in VALID_ALERT_STATUSES:
        raise ValueError("status must be viewed or dismissed")
    if not alert_status.get("alert_id"):
        raise ValueError("alert.alert_id is required")

    data = load_store(path)
    user = _ensure_user(data, token)
    history = user.setdefault("alert_history", [])
    normalized = {
        "alert_id": str(alert_status["alert_id"]),
        "product_oid": alert_status.get("product_oid"),
        "point_code": alert_status.get("point_code"),
        "alert_type": alert_status.get("alert_type"),
        "status": status,
        "updated_at": _now_iso(),
    }

    for index, existing in enumerate(history):
        if existing.get("alert_id") == normalized["alert_id"]:
            history[index] = {**existing, **normalized}
            save_store(data, path)
            return {"alert_history": deepcopy(history)}

    history.append(normalized)
    save_store(data, path)
    return {"alert_history": deepcopy(history)}


def clear_alert_history(user_token: str, path: Path | str | None = None) -> dict[str, Any]:
    token = _validate_user_token(user_token)
    data = load_store(path)
    user = _ensure_user(data, token)
    user["alert_history"] = []
    save_store(data, path)
    return {"alert_history": []}
