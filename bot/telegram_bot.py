from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from scripts.ask_processed_basket import build_result
from scripts.generate_point_signals import format_signals_text
from services.basket_text_formatter import format_basket_text
from services.collection_point_resolver import PointResolutionError, resolve_point_code
from services.price_signal_analyzer import analyze_point_signals
from services.telegram_message_utils import split_long_message


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROCESSED_ROOT = PROJECT_ROOT / "data" / "processed"
DEFAULT_POINT_CODE = "p001"


START_TEXT = """澳門採購決策 MVP Bot

你可以輸入：
/check 我想買一包米、兩支洗頭水、一包紙巾
/signals p001
/point 高士德

價格只供參考，以店內標示為準。"""

HELP_TEXT = """/check 我想買一包米、兩支洗頭水、一包紙巾
/check p001 我想買一包米、兩支洗頭水
/signals p001
/signals p001 10
/point 高士德"""

POINT_CODE_PATTERN = re.compile(r"^p\d+$", re.IGNORECASE)


def latest_processed_date(processed_root: Path = DEFAULT_PROCESSED_ROOT) -> str | None:
    if not processed_root.exists():
        return None
    dates = [
        path.name
        for path in processed_root.iterdir()
        if path.is_dir() and any((path / point_dir.name).is_dir() for point_dir in path.iterdir())
    ]
    return sorted(dates)[-1] if dates else None


def has_processed_data(date: str, point_code: str, processed_root: Path = DEFAULT_PROCESSED_ROOT) -> bool:
    point_dir = processed_root / date / point_code
    return point_dir.exists() and any(point_dir.glob("category_*_prices.jsonl"))


def resolve_date(date_setting: str | None, processed_root: Path = DEFAULT_PROCESSED_ROOT) -> str | None:
    if not date_setting or date_setting == "latest":
        return latest_processed_date(processed_root)
    return date_setting


def _point_for_code(point_code: str) -> dict[str, Any]:
    return resolve_point_code(point_code=point_code)


def parse_check_args(args: list[str], default_point_code: str = DEFAULT_POINT_CODE) -> tuple[str, str]:
    if args and POINT_CODE_PATTERN.match(args[0]):
        return args[0].lower(), " ".join(args[1:])
    return default_point_code, " ".join(args)


def render_check_message(
    shopping_text: str,
    date_setting: str | None = "latest",
    default_point_code: str = DEFAULT_POINT_CODE,
    processed_root: Path = DEFAULT_PROCESSED_ROOT,
) -> str:
    text = shopping_text.strip()
    if not text:
        return "請在 /check 後輸入購物清單，例如：/check 我想買一包米、兩支洗頭水、一包紙巾"

    date = resolve_date(date_setting, processed_root)
    if not date:
        return f"找不到 processed data：{processed_root}"
    if not has_processed_data(date, default_point_code, processed_root):
        return f"找不到 processed data：date={date}, point_code={default_point_code}"

    point = _point_for_code(default_point_code)
    result = build_result(date, default_point_code, text, processed_root)
    return format_basket_text(result, text, point)


def render_signals_message(
    point_code: str | None = None,
    top_n: int = 5,
    date_setting: str | None = "latest",
    processed_root: Path = DEFAULT_PROCESSED_ROOT,
) -> str:
    selected_point_code = (point_code or DEFAULT_POINT_CODE).strip() or DEFAULT_POINT_CODE
    date = resolve_date(date_setting, processed_root)
    if not date:
        return f"找不到 processed data：{processed_root}"
    if not has_processed_data(date, selected_point_code, processed_root):
        return f"找不到 processed data：date={date}, point_code={selected_point_code}"

    signals = analyze_point_signals(date, selected_point_code, processed_root)
    return format_signals_text(signals, top_n=top_n)


def render_point_message(query: str) -> str:
    value = query.strip()
    if not value:
        return "請在 /point 後輸入地區或採集點名稱，例如：/point 高士德"
    try:
        point = resolve_point_code(point_name=value)
    except PointResolutionError:
        try:
            point = resolve_point_code(district=value)
        except PointResolutionError as exc:
            return f"找不到採集點：{value}\n{exc}"
    return (
        "匹配到採集點：\n"
        f"point_code: {point.get('point_code')}\n"
        f"name: {point.get('name')}\n"
        f"district: {point.get('district')}"
    )


async def _reply_text(update: Any, message: str) -> None:
    for part in split_long_message(message):
        await update.message.reply_text(part)


async def start(update: Any, context: Any) -> None:
    await _reply_text(update, START_TEXT)


async def help_command(update: Any, context: Any) -> None:
    await _reply_text(update, HELP_TEXT)


async def check_command(update: Any, context: Any) -> None:
    point_code, text = parse_check_args(
        context.args,
        default_point_code=context.bot_data.get("default_point_code", DEFAULT_POINT_CODE),
    )
    message = render_check_message(
        text,
        date_setting=context.bot_data.get("default_date", "latest"),
        default_point_code=point_code,
    )
    await _reply_text(update, message)


async def signals_command(update: Any, context: Any) -> None:
    point_code = context.args[0] if context.args else context.bot_data.get("default_point_code", DEFAULT_POINT_CODE)
    top_n = int(context.args[1]) if len(context.args) > 1 and context.args[1].isdigit() else 5
    message = render_signals_message(
        point_code,
        top_n=top_n,
        date_setting=context.bot_data.get("default_date", "latest"),
    )
    await _reply_text(update, message)


async def point_command(update: Any, context: Any) -> None:
    message = render_point_message(" ".join(context.args))
    await _reply_text(update, message)


def build_application(token: str, default_point_code: str = DEFAULT_POINT_CODE, default_date: str = "latest") -> Any:
    from telegram.ext import Application, CommandHandler

    application = Application.builder().token(token).build()
    application.bot_data["default_point_code"] = default_point_code
    application.bot_data["default_date"] = default_date
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("check", check_command))
    application.add_handler(CommandHandler("signals", signals_command))
    application.add_handler(CommandHandler("point", point_command))
    return application


def run_bot(token: str, default_point_code: str = DEFAULT_POINT_CODE, default_date: str = "latest") -> None:
    application = build_application(token, default_point_code, default_date)
    application.run_polling()
