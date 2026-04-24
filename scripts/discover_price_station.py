from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import date
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from crawler.discover_links import discover_static
from crawler.network_recorder import classify_api_candidate, record_with_playwright


HOME_URL = "https://www.consumer.gov.mo/commodity/price_station.aspx?lang=zh"
MODULES = [
    "超市物價一覽通",
    "至抵超市龍虎榜",
    "價差超過五成的貨品排名",
    "專項物價",
]


KNOWN_ENTRYPOINTS = {
    "超市物價一覽通": [
        "https://www.consumer.gov.mo/commodity/price_station_type.aspx?lang=zh&type=t1",
        "https://www.consumer.gov.mo/commodity/price_station_type.aspx?lang=zh&type=t8",
    ],
    "至抵超市龍虎榜": [
        "https://www.consumer.gov.mo/commodity/price_station_type.aspx?lang=zh&type=t3",
    ],
    "價差超過五成的貨品排名": [
        "https://www.consumer.gov.mo/commodity/price_station_type.aspx?lang=zh&type=t4",
    ],
    "專項物價": [
        "https://www.consumer.gov.mo/commodity/price_station_type.aspx?lang=zh&type=t2",
        "https://www.consumer.gov.mo/special/index.aspx?lan=cn",
    ],
}


def setup_logger(output_dir: Path) -> logging.Logger:
    logger = logging.getLogger("price_station_discovery")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler = logging.FileHandler(output_dir / "discovery.log", encoding="utf-8")
    file_handler.setFormatter(formatter)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


def merge_module_results(playwright_modules: list[dict[str, Any]], all_responses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_name = {item["name"]: item for item in playwright_modules}
    modules = []
    for name in MODULES:
        item = by_name.get(
            name,
            {
                "name": name,
                "visible_text": "",
                "detected_url": None,
                "api_candidates": [],
                "html_files": [],
                "response_files": [],
                "status": "not_found",
            },
        )

        known_urls = KNOWN_ENTRYPOINTS.get(name, [])
        item.setdefault("known_entrypoints", known_urls)
        if not item.get("detected_url") and known_urls:
            item["detected_url"] = known_urls[0]
            if item.get("status") == "not_found":
                item["status"] = "needs_manual_inspection"

        candidates = list(item.get("api_candidates") or [])
        for response in all_responses:
            url = response.get("url") or ""
            if any(url.startswith(entry) for entry in known_urls) and classify_api_candidate(response):
                candidates.append(response)

        seen = set()
        deduped = []
        for candidate in candidates:
            key = (candidate.get("method"), candidate.get("url"), candidate.get("body_file"))
            if key not in seen:
                seen.add(key)
                deduped.append(candidate)
        item["api_candidates"] = deduped

        if item.get("status") == "found" and not item["api_candidates"]:
            item["status"] = "needs_manual_inspection"
        modules.append(item)
    return modules


def main() -> int:
    parser = argparse.ArgumentParser(description="Discover Macao Consumer Council price station data sources.")
    parser.add_argument("--home-url", default=HOME_URL)
    parser.add_argument("--output-root", default="data/discovery")
    parser.add_argument("--headed", action="store_true", help="Run Playwright in headed mode.")
    args = parser.parse_args()

    output_dir = Path(args.output_root) / date.today().isoformat()
    output_dir.mkdir(parents=True, exist_ok=True)
    logger = setup_logger(output_dir)
    logger.info("Starting discovery: %s", args.home_url)

    static_result = discover_static(args.home_url, output_dir, logger)
    logger.info("Static extraction complete: %s", static_result.get("json_file"))

    playwright_result = asyncio.run(
        record_with_playwright(
            args.home_url,
            MODULES,
            output_dir,
            logger,
            headless=not args.headed,
        )
    )

    modules = merge_module_results(
        playwright_result.get("modules", []),
        playwright_result.get("responses", []),
    )

    api_candidates = [
        response
        for response in playwright_result.get("responses", [])
        if classify_api_candidate(response)
    ]

    report = {
        "home_url": args.home_url,
        "output_dir": str(output_dir),
        "static_extract_file": static_result.get("json_file"),
        "network_log_file": playwright_result.get("network_log_file"),
        "errors": {
            "static": static_result.get("fetch", {}).get("error"),
            "playwright": playwright_result.get("error"),
        },
        "summary": {
            "static_counts": static_result.get("counts", {}),
            "network_request_count": len(playwright_result.get("requests", [])),
            "network_response_count": len(playwright_result.get("responses", [])),
            "api_candidate_count": len(api_candidates),
        },
        "api_candidates": api_candidates,
        "modules": modules,
    }

    report_path = output_dir / "discovery_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Discovery report written: %s", report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
