from __future__ import annotations

import json
import logging
import random
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36 price-station-discovery/0.1"
    ),
    "Accept-Language": "zh-HK,zh;q=0.9,en;q=0.7",
}


def polite_sleep(min_seconds: float = 1.0, max_seconds: float = 2.0) -> None:
    time.sleep(random.uniform(min_seconds, max_seconds))


def fetch_html(url: str, output_dir: Path, name: str, logger: logging.Logger) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    html_path = output_dir / f"{name}.html"
    meta_path = output_dir / f"{name}.meta.json"

    result: dict[str, Any] = {
        "url": url,
        "status_code": None,
        "content_type": None,
        "html_file": str(html_path),
        "meta_file": str(meta_path),
        "error": None,
    }

    try:
        polite_sleep()
        response = requests.get(url, headers=DEFAULT_HEADERS, timeout=30)
        result["status_code"] = response.status_code
        result["content_type"] = response.headers.get("content-type")
        response.raise_for_status()
        html_path.write_text(response.text, encoding=response.encoding or "utf-8")
        result["length"] = len(response.text)
    except Exception as exc:  # noqa: BLE001 - discovery must log every failure and continue
        logger.exception("Failed to fetch %s", url)
        result["error"] = repr(exc)
        html_path.write_text("", encoding="utf-8")
    finally:
        meta_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    return result


def parse_home_html(html: str, base_url: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")

    def attrs(tag: Any) -> dict[str, Any]:
        return {key: value for key, value in tag.attrs.items()}

    links = []
    for tag in soup.find_all("a"):
        href = tag.get("href")
        links.append(
            {
                "text": tag.get_text(" ", strip=True),
                "href": href,
                "abs_url": urljoin(base_url, href) if href else None,
                "attrs": attrs(tag),
            }
        )

    forms = []
    for tag in soup.find_all("form"):
        action = tag.get("action")
        forms.append(
            {
                "method": (tag.get("method") or "GET").upper(),
                "action": action,
                "abs_url": urljoin(base_url, action) if action else base_url,
                "attrs": attrs(tag),
                "inputs": [
                    {
                        "name": item.get("name"),
                        "type": item.get("type"),
                        "value": item.get("value"),
                        "attrs": attrs(item),
                    }
                    for item in tag.find_all(["input", "select", "textarea", "button"])
                ],
            }
        )

    scripts = []
    for index, tag in enumerate(soup.find_all("script")):
        src = tag.get("src")
        inline = tag.string or tag.get_text("", strip=False)
        scripts.append(
            {
                "index": index,
                "src": src,
                "abs_url": urljoin(base_url, src) if src else None,
                "attrs": attrs(tag),
                "inline_preview": inline[:1000] if inline else "",
            }
        )

    iframes = []
    for tag in soup.find_all("iframe"):
        src = tag.get("src")
        iframes.append(
            {
                "src": src,
                "abs_url": urljoin(base_url, src) if src else None,
                "attrs": attrs(tag),
                "text": tag.get_text(" ", strip=True),
            }
        )

    text = soup.get_text("\n", strip=True)
    return {
        "base_url": base_url,
        "title": soup.title.get_text(" ", strip=True) if soup.title else "",
        "links": links,
        "forms": forms,
        "scripts": scripts,
        "iframes": iframes,
        "visible_text_preview": text[:5000],
        "counts": {
            "links": len(links),
            "forms": len(forms),
            "scripts": len(scripts),
            "iframes": len(iframes),
        },
    }


def discover_static(url: str, output_dir: Path, logger: logging.Logger) -> dict[str, Any]:
    fetched = fetch_html(url, output_dir, "home_requests", logger)
    html_path = Path(fetched["html_file"])
    html = html_path.read_text(encoding="utf-8") if html_path.exists() else ""
    parsed = parse_home_html(html, url)
    parsed["fetch"] = fetched
    parsed_path = output_dir / "home_static_extract.json"
    parsed_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
    parsed["json_file"] = str(parsed_path)
    return parsed
