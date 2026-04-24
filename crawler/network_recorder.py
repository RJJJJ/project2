from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import random
import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin


NETWORK_RESOURCE_TYPES = {"document", "xhr", "fetch", "script"}
BODY_RESOURCE_TYPES = {"document", "xhr", "fetch"}
API_HINTS = re.compile(
    r"(api|ajax|ashx|asmx|svc|json|handler|price|station|special|commodity|get|list|rank)",
    re.I,
)


def safe_name(value: str, max_len: int = 90) -> str:
    cleaned = re.sub(r"[^0-9A-Za-z._-]+", "_", value).strip("_")
    return cleaned[:max_len] or "response"


def classify_api_candidate(item: dict[str, Any]) -> bool:
    url = item.get("url") or ""
    content_type = (item.get("content_type") or "").lower()
    resource_type = item.get("resource_type") or ""
    return (
        resource_type in {"xhr", "fetch"}
        or "json" in content_type
        or bool(API_HINTS.search(url))
    )


async def _maybe_save_response_body(response: Any, output_dir: Path, logger: logging.Logger) -> str | None:
    request = response.request
    resource_type = request.resource_type
    content_type = response.headers.get("content-type", "")

    if resource_type not in BODY_RESOURCE_TYPES and "json" not in content_type.lower():
        return None

    try:
        body = await response.body()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not read response body %s: %r", response.url, exc)
        return None

    if not body:
        return None

    digest = hashlib.sha1(response.url.encode("utf-8")).hexdigest()[:10]
    suffix = ".json" if "json" in content_type.lower() else ".html" if "html" in content_type.lower() else ".txt"
    filename = f"{resource_type}_{safe_name(response.url)}_{digest}{suffix}"
    path = output_dir / "responses" / filename
    path.parent.mkdir(parents=True, exist_ok=True)

    if suffix in {".json", ".html", ".txt"}:
        path.write_text(body.decode("utf-8", errors="replace"), encoding="utf-8")
    else:
        path.write_bytes(body)
    return str(path)


async def record_with_playwright(
    home_url: str,
    module_names: list[str],
    output_dir: Path,
    logger: logging.Logger,
    headless: bool = True,
) -> dict[str, Any]:
    try:
        from playwright.async_api import TimeoutError as PlaywrightTimeoutError
        from playwright.async_api import async_playwright
    except Exception as exc:  # noqa: BLE001
        logger.exception("Playwright is not available")
        return {"error": repr(exc), "requests": [], "responses": [], "modules": []}

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "responses").mkdir(parents=True, exist_ok=True)
    requests_seen: list[dict[str, Any]] = []
    responses_seen: list[dict[str, Any]] = []
    module_results: dict[str, dict[str, Any]] = {
        name: {
            "name": name,
            "visible_text": "",
            "detected_url": None,
            "api_candidates": [],
            "html_files": [],
            "response_files": [],
            "status": "not_found",
        }
        for name in module_names
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(
            locale="zh-HK",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36 price-station-discovery/0.1"
            ),
        )
        page = await context.new_page()

        page.on(
            "request",
            lambda request: requests_seen.append(
                {
                    "url": request.url,
                    "method": request.method,
                    "resource_type": request.resource_type,
                    "frame_url": request.frame.url if request.frame else None,
                }
            ),
        )

        async def on_response(response: Any) -> None:
            item = {
                "url": response.url,
                "status": response.status,
                "resource_type": response.request.resource_type,
                "method": response.request.method,
                "content_type": response.headers.get("content-type"),
                "body_file": None,
            }
            try:
                item["body_file"] = await _maybe_save_response_body(response, output_dir, logger)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Error while saving response body %s: %r", response.url, exc)
            responses_seen.append(item)

        page.on("response", lambda response: asyncio.create_task(on_response(response)))

        try:
            await page.goto(home_url, wait_until="networkidle", timeout=45000)
            home_html = await page.content()
            home_file = output_dir / "playwright_home.html"
            home_file.write_text(home_html, encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            logger.exception("Playwright failed to load home page")
            await browser.close()
            return {"error": repr(exc), "requests": requests_seen, "responses": responses_seen, "modules": list(module_results.values())}

        for module_name in module_names:
            await page.wait_for_timeout(int(random.uniform(1000, 2000)))
            before_response_count = len(responses_seen)
            before_url = page.url

            try:
                locator = page.get_by_text(module_name, exact=True).first
                count = await page.get_by_text(module_name, exact=True).count()
                if count == 0:
                    locator = page.get_by_text(module_name).first
                    count = await page.get_by_text(module_name).count()

                if count == 0:
                    module_results[module_name]["status"] = "not_found"
                    continue

                visible_text = await locator.inner_text(timeout=5000)
                module_results[module_name]["visible_text"] = visible_text
                module_results[module_name]["status"] = "found"

                try:
                    link = locator.locator("xpath=ancestor-or-self::a[1]")
                    href = await link.get_attribute("href", timeout=2000)
                    if href:
                        module_results[module_name]["detected_url"] = urljoin(home_url, href)
                except Exception:
                    pass

                try:
                    await locator.click(timeout=8000)
                    await page.wait_for_load_state("networkidle", timeout=15000)
                except PlaywrightTimeoutError as exc:
                    logger.info("Click timeout for %s: %r", module_name, exc)
                    module_results[module_name]["status"] = "needs_manual_inspection"
                except Exception as exc:  # noqa: BLE001
                    logger.info("Click did not navigate for %s: %r", module_name, exc)

                after_url = page.url
                if after_url != before_url:
                    module_results[module_name]["detected_url"] = after_url

                await page.wait_for_timeout(int(random.uniform(1000, 2000)))
                html_path = output_dir / f"module_{safe_name(module_name)}.html"
                html_path.write_text(await page.content(), encoding="utf-8")
                module_results[module_name]["html_files"].append(str(html_path))

                new_responses = responses_seen[before_response_count:]
                for item in new_responses:
                    if item.get("body_file"):
                        module_results[module_name]["response_files"].append(item["body_file"])
                    if classify_api_candidate(item):
                        module_results[module_name]["api_candidates"].append(item)

                if after_url != home_url:
                    await page.goto(home_url, wait_until="networkidle", timeout=30000)
            except Exception as exc:  # noqa: BLE001
                logger.exception("Module discovery failed: %s", module_name)
                module_results[module_name]["status"] = "needs_manual_inspection"
                module_results[module_name]["error"] = repr(exc)

        await page.wait_for_timeout(2000)
        await browser.close()

    for item in responses_seen:
        if classify_api_candidate(item):
            for result in module_results.values():
                detected_url = result.get("detected_url") or ""
                if detected_url and item["url"].startswith(detected_url):
                    result["api_candidates"].append(item)

    network_path = output_dir / "network_log.json"
    network_path.write_text(
        json.dumps({"requests": requests_seen, "responses": responses_seen}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "network_log_file": str(network_path),
        "requests": requests_seen,
        "responses": responses_seen,
        "modules": list(module_results.values()),
        "error": None,
    }
