from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from fastapi.testclient import TestClient

from app.main import app
from services.data_provider_config import get_sqlite_db_path


def main() -> int:
    db_path = get_sqlite_db_path()
    if not db_path.exists():
        print(json.dumps({"ok": False, "errors": [f"SQLite DB not found: {db_path}"]}, ensure_ascii=False, indent=2))
        return 1
    client = TestClient(app)
    candidates_response = client.get("/api/products/candidates", params={"point_code": "p001", "keyword": "\u7c73", "limit": 1})
    basket_response = client.post("/api/basket/ask", json={"text": "\u7c73\u3001\u6d17\u982d\u6c34\u3001\u7d19\u5dfe", "point_code": "p001"})
    payload = {
        "ok": candidates_response.status_code == 200 and basket_response.status_code == 200,
        "db_path": str(db_path),
        "candidates_status": candidates_response.status_code,
        "basket_status": basket_response.status_code,
        "rice_first": (candidates_response.json().get("candidates") or [None])[0] if candidates_response.status_code == 200 else None,
        "basket": basket_response.json() if basket_response.status_code == 200 else None,
        "errors": [],
    }
    if not payload["ok"]:
        payload["errors"].append({"candidates": candidates_response.text, "basket": basket_response.text})
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
