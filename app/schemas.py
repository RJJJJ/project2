from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SelectedProduct(BaseModel):
    keyword: str
    product_oid: int


class BasketAskRequest(BaseModel):
    text: str
    point_code: str | None = None
    point_name: str | None = None
    district: str | None = None
    date: str = "latest"
    format: str = "json"
    selected_products: list[SelectedProduct] | None = None


class ShoppingAgentRequest(BaseModel):
    query: str
    point_code: str | None = None
    use_llm: bool = False
    include_price_plan: bool = False
    price_strategy: str = "cheapest_single_store"
    decision_policy: str = "cheapest_single_store"
    decision_policy_options: dict[str, Any] | None = None
    clarification_answers: dict[str, str] | None = None
    planner_mode: str = "rule"
    local_llm_model: str | None = None
    local_llm_endpoint: str | None = None
    retrieval_mode: str = "taxonomy"
    composer_mode: str = "template"


class BasketAskResponse(BaseModel):
    date: str
    point_code: str
    parsed_items: list[dict[str, Any]]
    plans: list[dict[str, Any]]
    warnings: list[str]
    recommended_plan_type: str | None = None
    recommendation_reason: str | None = None


class TextResponse(BaseModel):
    text: str


class WatchlistSignalItem(BaseModel):
    product_oid: int
    product_name: str | None = None


class WatchlistSignalsRequest(BaseModel):
    point_code: str
    date: str = "latest"
    lookback_days: int = 30
    items: list[WatchlistSignalItem] = Field(default_factory=list)


class UserWatchlistItem(BaseModel):
    product_oid: int
    product_name: str | None = None
    package_quantity: str | None = None
    category_name: str | None = None
    point_code: str
    point_name: str | None = None


class UserWatchlistRequest(BaseModel):
    user_token: str
    item: UserWatchlistItem


class UserAlertStatus(BaseModel):
    alert_id: str
    product_oid: int | None = None
    point_code: str | None = None
    alert_type: str | None = None
    status: str


class UserAlertStatusRequest(BaseModel):
    user_token: str
    alert: UserAlertStatus

