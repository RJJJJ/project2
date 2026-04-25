from __future__ import annotations


def _hard_split(text: str, max_len: int) -> list[str]:
    return [text[index : index + max_len] for index in range(0, len(text), max_len)]


def _split_with_separator(text: str, separator: str) -> list[str]:
    pieces = text.split(separator)
    return [
        piece + (separator if index < len(pieces) - 1 else "")
        for index, piece in enumerate(pieces)
    ]


def _split_to_limit(text: str, max_len: int, separators: tuple[str, ...]) -> list[str]:
    if len(text) <= max_len:
        return [text]
    if not separators:
        return _hard_split(text, max_len)

    parts: list[str] = []
    current = ""
    for segment in _split_with_separator(text, separators[0]):
        split_segments = (
            [segment]
            if len(segment) <= max_len
            else _split_to_limit(segment, max_len, separators[1:])
        )
        for split_segment in split_segments:
            if current and len(current) + len(split_segment) > max_len:
                parts.append(current)
                current = ""
            if len(split_segment) > max_len:
                parts.extend(_split_to_limit(split_segment, max_len, separators[1:]))
            else:
                current += split_segment
    if current or not parts:
        parts.append(current)
    return parts


def split_long_message(text: str, max_len: int = 3500) -> list[str]:
    if max_len <= 0:
        raise ValueError("max_len must be positive")
    if text == "":
        return [""]
    return _split_to_limit(text, max_len, ("\n\n", "\n"))
