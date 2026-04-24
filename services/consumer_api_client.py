from __future__ import annotations

import time
from collections.abc import Iterable
from typing import Any
from urllib.parse import urlencode

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class ConsumerPriceApiClient:
    base_url = "https://api03.consumer.gov.mo/ccapi/web/sm/v2/uat/itemsPrice/by_condition"

    def __init__(
        self,
        timeout: float = 30.0,
        sleep_seconds: float = 1.0,
        max_retries: int = 3,
        session: requests.Session | None = None,
    ) -> None:
        self.timeout = timeout
        self.sleep_seconds = sleep_seconds
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36 consumer-price-fetcher/0.1"
                ),
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "zh-HK,zh;q=0.9,en;q=0.7",
            }
        )

        retry = Retry(
            total=max_retries,
            connect=max_retries,
            read=max_retries,
            status=max_retries,
            backoff_factor=1.0,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=frozenset(["GET"]),
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def build_category_url(
        self,
        category_id: int,
        lat: float,
        lng: float,
        dst: int = 400,
        lang: str = "cn",
    ) -> str:
        params = {
            "key": "",
            "size": 0,
            "categories": int(category_id),
            "items": "",
            "cet": f"{lat},{lng}",
            "dst": int(dst),
            "lang": lang,
        }
        return f"{self.base_url}?{urlencode(params)}"

    def fetch_category(
        self,
        category_id: int,
        lat: float,
        lng: float,
        dst: int = 400,
        lang: str = "cn",
    ) -> dict[str, Any] | list[Any]:
        url = self.build_category_url(category_id, lat, lng, dst=dst, lang=lang)
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def fetch_all_categories(
        self,
        category_ids: Iterable[int],
        lat: float,
        lng: float,
        dst: int = 400,
        lang: str = "cn",
    ) -> dict[int, dict[str, Any] | list[Any]]:
        results: dict[int, dict[str, Any] | list[Any]] = {}
        for index, category_id in enumerate(category_ids):
            if index:
                time.sleep(self.sleep_seconds)
            results[int(category_id)] = self.fetch_category(category_id, lat, lng, dst=dst, lang=lang)
        return results
