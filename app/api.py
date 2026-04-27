from __future__ import annotations

from copy import deepcopy
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas import BasketAskRequest, BasketAskResponse, TextResponse, WatchlistSignalsRequest
from app.utils import (
    DEFAULT_POINT_CODE,
    ensure_processed_data_exists,
    get_processed_root,
    latest_processed_date,
    resolve_date,
    resolve_point_from_request,
)
from scripts.ask_processed_basket import build_result
from scripts.generate_point_signals import format_signals_text
from services.basket_text_formatter import format_basket_text
from services.collection_point_resolver import PointResolutionError, load_collection_points, resolve_point_code
from services.historical_price_signal_analyzer import analyze_historical_price_signals
from services.price_signal_analyzer import analyze_point_signals
from services.product_candidate_search import search_product_candidates
from services.watchlist_signal_service import analyze_watchlist_items


router = APIRouter(prefix="/api")


def _resolve_point_search(query: str) -> dict[str, Any]:
    for kwargs in ({"point_name": query}, {"district": query}):
        try:
            return resolve_point_code(**kwargs)
        except PointResolutionError:
            continue
    raise HTTPException(status_code=404, detail=f"Collection point not found: {query}")


def _basket_result(request: BasketAskRequest) -> tuple[dict[str, Any], dict[str, Any]]:
    processed_root = get_processed_root()
    date = resolve_date(request.date, processed_root)
    point = resolve_point_from_request(request.point_code, request.point_name, request.district)
    point_code = str(point["point_code"])
    ensure_processed_data_exists(date, point_code, processed_root)
    selected_products = [item.dict() for item in request.selected_products or []]
    result = build_result(date, point_code, request.text, processed_root, selected_products=selected_products)
    return result, point


def _signals_result(point_code: str, date: str, top_n: int) -> dict[str, Any]:
    processed_root = get_processed_root()
    selected_date = resolve_date(date, processed_root)
    ensure_processed_data_exists(selected_date, point_code, processed_root)
    signals = deepcopy(analyze_point_signals(selected_date, point_code, processed_root))
    signals["largest_price_gap"] = (signals.get("largest_price_gap") or [])[:top_n]
    return signals


def _historical_signals_result(point_code: str, date: str, lookback_days: int, top_n: int) -> dict[str, Any]:
    processed_root = get_processed_root()
    point = resolve_point_from_request(point_code=point_code)
    return analyze_historical_price_signals(
        str(point["point_code"]),
        current_date=date,
        lookback_days=lookback_days,
        top_n=top_n,
        processed_root=processed_root,
    )


def _watchlist_signals_result(request: WatchlistSignalsRequest) -> dict[str, Any]:
    processed_root = get_processed_root()
    point = resolve_point_from_request(point_code=request.point_code)
    return analyze_watchlist_items(
        str(point["point_code"]),
        [item.model_dump() if hasattr(item, "model_dump") else item.dict() for item in request.items],
        date=request.date,
        lookback_days=request.lookback_days,
        processed_root=processed_root,
    )


@router.get("/health")
def health() -> dict[str, Any]:
    processed_root = get_processed_root()
    return {
        "status": "ok",
        "latest_processed_date": latest_processed_date(processed_root),
        "default_point_code": DEFAULT_POINT_CODE,
        "processed_root": str(processed_root),
        "processed_root_exists": processed_root.exists(),
    }


@router.get("/points")
def points() -> list[dict[str, Any]]:
    return load_collection_points()


@router.get("/points/search")
def search_points(q: str = Query(..., min_length=1)) -> dict[str, Any]:
    return _resolve_point_search(q)


@router.post("/basket/ask", response_model=BasketAskResponse)
def ask_basket(request: BasketAskRequest) -> dict[str, Any]:
    result, _point = _basket_result(request)
    return result


@router.get("/products/candidates")
def product_candidates(
    keyword: str = Query(..., min_length=1),
    point_code: str = Query(..., min_length=1),
    date: str = "latest",
    limit: int = Query(10, ge=1, le=50),
) -> dict[str, Any]:
    processed_root = get_processed_root()
    selected_date = resolve_date(date, processed_root)
    point = resolve_point_from_request(point_code=point_code)
    selected_point_code = str(point["point_code"])
    ensure_processed_data_exists(selected_date, selected_point_code, processed_root)
    return {
        "date": selected_date,
        "point_code": selected_point_code,
        "keyword": keyword,
        "candidates": search_product_candidates(
            selected_date,
            selected_point_code,
            keyword,
            limit=limit,
            processed_root=processed_root,
        ),
    }


@router.post("/basket/ask_text", response_model=TextResponse)
def ask_basket_text(request: BasketAskRequest) -> dict[str, str]:
    result, point = _basket_result(request)
    return {"text": format_basket_text(result, request.text, point)}


@router.get("/signals/{point_code}")
def get_signals(
    point_code: str,
    date: str = "latest",
    top_n: int = Query(5, ge=1),
) -> dict[str, Any]:
    return _signals_result(point_code, date, top_n)


@router.get("/historical-signals/{point_code}")
def get_historical_signals(
    point_code: str,
    date: str = "latest",
    lookback_days: int = Query(30, ge=1),
    top_n: int = Query(10, ge=1),
) -> dict[str, Any]:
    return _historical_signals_result(point_code, date, lookback_days, top_n)


@router.post("/watchlist/signals")
def post_watchlist_signals(request: WatchlistSignalsRequest) -> dict[str, Any]:
    return _watchlist_signals_result(request)


@router.get("/signals/{point_code}/text", response_model=TextResponse)
def get_signals_text(
    point_code: str,
    date: str = "latest",
    top_n: int = Query(5, ge=1),
) -> dict[str, str]:
    signals = _signals_result(point_code, date, top_n)
    return {"text": format_signals_text(signals, top_n=top_n)}
