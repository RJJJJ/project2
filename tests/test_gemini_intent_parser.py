from __future__ import annotations

import json

from services.gemini_intent_parser import parse_intent

TEXT = "\u6211\u5728\u9ad8\u58eb\u5fb7\uff0c\u60f3\u8cb7\u4e00\u5305\u7c73\u3001\u5169\u652f\u6d17\u982d\u6c34\u3001\u4e00\u5305\u7d19\u5dfe"


class FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class FakeClient:
    def __init__(self, text: str) -> None:
        self.text = text

    def generate_content(self, *args, **kwargs):  # noqa: ANN002, ANN003
        return FakeResponse(self.text)


def test_no_api_key_fallback_parser(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    intent = parse_intent(TEXT)

    assert intent["location_text"] == "\u9ad8\u58eb\u5fb7"
    assert [item["keyword"] for item in intent["items"]] == ["\u7c73", "\u6d17\u982d\u6c34", "\u7d19\u5dfe"]
    assert [item["quantity"] for item in intent["items"]] == [1, 2, 1]
    assert intent["confidence"] == 0.55


def test_fake_gemini_client_json() -> None:
    payload = {
        "location_text": "\u9ad8\u58eb\u5fb7",
        "point_code": None,
        "items": [{"keyword": "\u7c73", "quantity": 1, "unit": "\u5305", "raw_text": "\u4e00\u5305\u7c73"}],
        "preference": "balanced",
        "needs_clarification": False,
        "clarification_question": None,
        "confidence": 0.9,
    }

    intent = parse_intent(TEXT, client=FakeClient(json.dumps(payload, ensure_ascii=False)))

    assert intent["preference"] == "balanced"
    assert intent["items"][0]["keyword"] == "\u7c73"
    assert intent["confidence"] == 0.9


def test_fake_gemini_invalid_json_fallback() -> None:
    intent = parse_intent(TEXT, client=FakeClient("not json"))

    assert intent["items"][0]["keyword"] == "\u7c73"
    assert intent["confidence"] == 0.55


def test_parser_does_not_generate_prices() -> None:
    intent = parse_intent(TEXT, use_gemini=False)

    assert "price" not in json.dumps(intent).casefold()
    assert "total" not in json.dumps(intent).casefold()
