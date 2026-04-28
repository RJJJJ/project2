from __future__ import annotations

from copy import deepcopy
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas import (
    BasketAskRequest,
    BasketAskResponse,
    TextResponse,
    UserAlertStatusRequest,
    UserWatchlistRequest,
    WatchlistSignalsRequest,
)
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
from services.watchlist_alert_service import generate_watchlist_alerts
from services.watchlist_signal_service import analyze_watchlist_items
from services import user_watchlist_store
from services.data_provider_config import get_sqlite_db_path, is_sqlite_provider_enabled
from services.simple_basket_parser import parse_simple_basket_text
from services.sqlite_query_service import (
    build_sqlite_simple_basket,
    connect_readonly,
    get_latest_date as sqlite_get_latest_date,
    search_product_candidates_for_point as sqlite_search_product_candidates_for_point,
)


router = APIRouter(prefix="/api")


def _valid_user_token(user_token: str | None) -> str:
    if not isinstance(user_token, str) or not user_token.strip():
        raise HTTPException(status_code=400, detail="user_token is required")
    return user_token.strip()


def _store_error(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


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



def _sqlite_db_path_or_503() -> Any:
    db_path = get_sqlite_db_path()
    if not db_path.exists():
        raise HTTPException(status_code=503, detail=f"SQLite provider enabled but database not found: {db_path}")
    return db_path


def _sqlite_date(conn: Any, requested_date: str) -> str:
    if requested_date == "latest":
        latest = sqlite_get_latest_date(conn)
        if not latest:
            raise HTTPException(status_code=503, detail="SQLite provider enabled but no price_records date found")
        return latest
    return requested_date


def _sqlite_basket_response(request: BasketAskRequest) -> dict[str, Any]:
    point = resolve_point_from_request(request.point_code, request.point_name, request.district)
    point_code = str(point["point_code"])
    db_path = _sqlite_db_path_or_503()
    with connect_readonly(db_path) as conn:
        selected_date = _sqlite_date(conn, request.date)
        parsed_items = parse_simple_basket_text(request.text)
        basket = build_sqlite_simple_basket(conn, selected_date, point_code, parsed_items)
    stores_by_oid: dict[str, dict[str, Any]] = {}
    plan_items: list[dict[str, Any]] = []
    for item in basket["items"]:
        plan_item = dict(item)
        if item.get("matched"):
            plan_item["requested_quantity"] = item.get("quantity", 1)
            supermarket_oid = str(item.get("supermarket_oid"))
            stores_by_oid.setdefault(supermarket_oid, {"supermarket_oid": item.get("supermarket_oid"), "supermarket_name": item.get("supermarket_name")})
        plan_items.append(plan_item)
    plan = {
        "plan_type": "sqlite_simple_basket",
        "estimated_total_mop": basket["estimated_total_mop"],
        "store_count": len(stores_by_oid),
        "stores": list(stores_by_oid.values()),
        "items": plan_items,
    }
    return {
        "date": selected_date,
        "point_code": point_code,
        "parsed_items": [{"keyword": item.get("keyword"), "quantity": item.get("quantity", 1)} for item in parsed_items],
        "plans": [plan],
        "warnings": basket.get("warnings", []),
        "recommended_plan_type": "sqlite_simple_basket",
        "recommendation_reason": "SQLite prototype：根據商品匹配及最低價生成，未等同正式採購優化器。",
    }


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


def _watchlist_alerts_result(request: WatchlistSignalsRequest) -> dict[str, Any]:
    processed_root = get_processed_root()
    point = resolve_point_from_request(point_code=request.point_code)
    return generate_watchlist_alerts(
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
    if is_sqlite_provider_enabled():
        return _sqlite_basket_response(request)
    result, _point = _basket_result(request)
    return result


@router.get("/products/candidates")
def product_candidates(
    keyword: str = Query(..., min_length=1),
    point_code: str = Query(..., min_length=1),
    date: str = "latest",
    limit: int = Query(10, ge=1, le=50),
) -> dict[str, Any]:
    point = resolve_point_from_request(point_code=point_code)
    selected_point_code = str(point["point_code"])
    if is_sqlite_provider_enabled():
        db_path = _sqlite_db_path_or_503()
        with connect_readonly(db_path) as conn:
            selected_date = _sqlite_date(conn, date)
            candidates = sqlite_search_product_candidates_for_point(conn, selected_date, selected_point_code, keyword, limit=limit)
        return {"date": selected_date, "point_code": selected_point_code, "keyword": keyword, "candidates": candidates}

    processed_root = get_processed_root()
    selected_date = resolve_date(date, processed_root)
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


@router.post("/watchlist/alerts")
def post_watchlist_alerts(request: WatchlistSignalsRequest) -> dict[str, Any]:
    return _watchlist_alerts_result(request)


@router.get("/user/watchlist")
def get_user_watchlist(user_token: str = Query(..., min_length=1)) -> dict[str, Any]:
    token = _valid_user_token(user_token)
    try:
        return {"user_token": token, "items": user_watchlist_store.get_user_watchlist(token)}
    except ValueError as exc:
        raise _store_error(exc) from exc


@router.post("/user/watchlist")
def post_user_watchlist(request: UserWatchlistRequest) -> dict[str, Any]:
    token = _valid_user_token(request.user_token)
    try:
        result = user_watchlist_store.add_watchlist_item(
            token,
            request.item.model_dump() if hasattr(request.item, "model_dump") else request.item.dict(),
        )
        response = {"user_token": token, "items": result["items"]}
        if result.get("warning"):
            response["warning"] = result["warning"]
        return response
    except ValueError as exc:
        raise _store_error(exc) from exc


@router.delete("/user/watchlist/{product_oid}")
def delete_user_watchlist_item(
    product_oid: int,
    user_token: str = Query(..., min_length=1),
    point_code: str = Query(..., min_length=1),
) -> dict[str, Any]:
    token = _valid_user_token(user_token)
    try:
        result = user_watchlist_store.remove_watchlist_item(token, product_oid, point_code)
        response = {"user_token": token, "items": result["items"]}
        if result.get("warning"):
            response["warning"] = result["warning"]
        return response
    except ValueError as exc:
        raise _store_error(exc) from exc


@router.get("/user/alert-history")
def get_user_alert_history(user_token: str = Query(..., min_length=1)) -> dict[str, Any]:
    token = _valid_user_token(user_token)
    try:
        return {"user_token": token, "alert_history": user_watchlist_store.get_alert_history(token)}
    except ValueError as exc:
        raise _store_error(exc) from exc


@router.post("/user/alert-history")
def post_user_alert_history(request: UserAlertStatusRequest) -> dict[str, Any]:
    token = _valid_user_token(request.user_token)
    try:
        result = user_watchlist_store.set_alert_status(
            token,
            request.alert.model_dump() if hasattr(request.alert, "model_dump") else request.alert.dict(),
        )
        return {"user_token": token, "alert_history": result["alert_history"]}
    except ValueError as exc:
        raise _store_error(exc) from exc


@router.delete("/user/alert-history")
def delete_user_alert_history(user_token: str = Query(..., min_length=1)) -> dict[str, Any]:
    token = _valid_user_token(user_token)
    try:
        result = user_watchlist_store.clear_alert_history(token)
        return {"user_token": token, "alert_history": result["alert_history"]}
    except ValueError as exc:
        raise _store_error(exc) from exc


@router.get("/signals/{point_code}/text", response_model=TextResponse)
def get_signals_text(
    point_code: str,
    date: str = "latest",
    top_n: int = Query(5, ge=1),
) -> dict[str, str]:
    signals = _signals_result(point_code, date, top_n)
    return {"text": format_signals_text(signals, top_n=top_n)}
