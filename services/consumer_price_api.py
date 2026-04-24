from __future__ import annotations

import time
from typing import Any
from urllib.parse import urlencode

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class ConsumerPriceApi:
    base_url = "https://api03.consumer.gov.mo/ccapi/web/sm/v2/uat/itemsPrice/by_condition"

    def __init__(
        self,
        timeout: float = 20.0,
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
                    "Chrome/124.0 Safari/537.36 consumer-price-collection-crawler/0.1"
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

    def build_url(
        self,
        category_id: int,
        lat: float,
        lng: float,
        dst: int = 500,
        key: str = "",
        items: str = "",
        lang: str = "cn",
    ) -> str:
        params = {
            "key": key,
            "size": 0,
            "categories": int(category_id),
            "items": items,
            "cet": f"{lat},{lng}",
            "dst": int(dst),
            "lang": lang,
        }
        return f"{self.base_url}?{urlencode(params)}"

    def fetch_by_condition(
        self,
        category_id: int,
        lat: float,
        lng: float,
        dst: int = 500,
        key: str = "",
        items: str = "",
        lang: str = "cn",
    ) -> dict[str, Any]:
        source_url = self.build_url(category_id, lat, lng, dst=dst, key=key, items=items, lang=lang)
        time.sleep(self.sleep_seconds)
        response = self.session.get(source_url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict):
            data.setdefault("source_url", source_url)
        return data

    def fetch_supermarkets_for_point(self, lat: float, lng: float, dst: int = 500) -> dict[str, Any]:
        return self.fetch_by_condition(19, lat, lng, dst=dst)

    def fetch_items_for_point_and_category(
        self,
        lat: float,
        lng: float,
        category_id: int,
        dst: int = 500,
    ) -> dict[str, Any]:
        return self.fetch_by_condition(category_id, lat, lng, dst=dst)
