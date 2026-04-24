from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.processed_price_query import get_point_overview


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect one processed Consumer Council collection point.")
    parser.add_argument("--date", required=True)
    parser.add_argument("--point-code", required=True)
    parser.add_argument("--processed-root", default=str(PROJECT_ROOT / "data" / "processed"))
    args = parser.parse_args()

    overview = get_point_overview(
        args.date,
        args.point_code,
        processed_root=Path(args.processed_root),
    )
    print(json.dumps(overview, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
