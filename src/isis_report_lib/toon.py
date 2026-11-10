"""Parser for the `.toon` text format.

Supported syntax:

- ``key: value`` — simple pair
- ``key:`` + indented lines — nested object
- ``key[n]:`` + ``- ...`` items — array with n elements
- ``key[n]{a,b}:`` + ``v1,v2`` lines — array of objects
- ``data[n]:`` — the report records (legacy alias ``dados[n]:`` still accepted)
- ``key{Label,format,align}`` — inline compact layout field
"""

import re
from typing import Any


class ToonParser:
    """Convert `.toon` text into a structured dict."""

    @staticmethod
    def _convert_value(value: str) -> Any:
        v = value.strip()
        if v.lower() == "true":
            return True
        if v.lower() == "false":
            return False
        try:
            return int(v)
        except ValueError:
            pass
        try:
            return float(v)
        except ValueError:
            pass
        return v

    def parse(self, text: str) -> dict:
        """Parse `.toon` text into a dict (``dados`` accepted as legacy alias of ``data``)."""
        try:
            tokens = self._tokenize(text)
            result, _ = self._parse_dict(tokens, 0, 0)
        except RecursionError as e:
            raise ValueError("Input is nested too deeply to parse") from e
        if "dados" in result and "data" not in result:
            result["data"] = result.pop("dados")
        return result

    def _tokenize(self, text: str) -> list[tuple[int, str]]:
        tokens = []
        for line in text.split("\n"):
            stripped = line.rstrip()
            content = stripped.strip()
            if not content:
                continue
            indent = len(line) - len(line.lstrip())
            level = indent // 2
            tokens.append((level, content))
        return tokens

    def _parse_dict(self, tokens: list[tuple[int, str]], start: int, level: int) -> tuple[dict, int]:
        result: dict[str, Any] = {}
        i = start
        while i < len(tokens):
            tok_level, content = tokens[i]
            if tok_level < level:
                break
            if tok_level > level:
                i += 1
                continue

            if content.startswith("- "):
                i += 1
                continue

            m = re.match(r"^(\w+)\[(\d+)\]\{([^}]+)\}:$", content)
            if m:
                key = m.group(1)
                fields = [f.strip() for f in m.group(3).split(",")]
                arr = []
                i += 1
                while i < len(tokens) and tokens[i][0] > tok_level:
                    _, val_line = tokens[i]
                    vals = [self._convert_value(v) for v in val_line.split(",")]
                    arr.append(dict(zip(fields, vals, strict=True)))
                    i += 1
                result[key] = arr
                continue

            m = re.match(r"^(\w+)\[(\d+)\]:$", content)
            if m:
                key = m.group(1)
                arr = []
                i += 1
                sub_arr, consumed = self._parse_array(tokens, i, tok_level + 1)
                arr.extend(sub_arr)
                i = consumed
                result[key] = arr
                continue

            m = re.match(r"^(\w+)\{([^,]+),([^,]+),([^,]+)\}$", content)
            if m:
                result[m.group(1)] = {
                    "label": m.group(2).strip(),
                    "format_mask": m.group(3).strip(),
                    "alignment": m.group(4).strip(),
                }
                i += 1
                continue

            m = re.match(r"^([^:]+):\s*(.*)$", content)
            if m:
                key = m.group(1).strip()
                value = m.group(2).strip()
                if value:
                    result[key] = self._convert_value(value)
                    i += 1
                else:
                    if i + 1 < len(tokens) and tokens[i + 1][0] > tok_level:
                        sub_dict, consumed = self._parse_dict(tokens, i + 1, tok_level + 1)
                        result[key] = sub_dict if sub_dict else {}
                        i = consumed
                    else:
                        result[key] = {}
                        i += 1
                continue

            i += 1

        return result, i

    def _parse_array(self, tokens: list[tuple[int, str]], start: int, level: int) -> tuple[list, int]:
        result: list[Any] = []
        i = start
        while i < len(tokens):
            tok_level, content = tokens[i]
            if tok_level < level:
                break
            if tok_level > level:
                i += 1
                continue

            if content.startswith("- "):
                item: Any = {}
                item_text = content[2:].strip()
                m = re.match(r"^([^:]+):\s*(.*)$", item_text)
                if m:
                    key = m.group(1).strip()
                    value = m.group(2).strip()
                    if value:
                        item[key] = self._convert_value(value)
                    else:
                        sub_dict: dict[str, Any] = {}
                        if i + 1 < len(tokens) and tokens[i + 1][0] > tok_level:
                            sub_dict, consumed = self._parse_dict(tokens, i + 1, tok_level + 1)
                            i = consumed
                        item[key] = sub_dict if sub_dict else {}
                else:
                    item = self._convert_value(item_text)
                    i += 1
                    result.append(item)
                    continue

                i += 1
                if i < len(tokens) and tokens[i][0] == tok_level + 1:
                    extra_dict, consumed = self._parse_dict(tokens, i, tok_level + 1)
                    item.update(extra_dict)
                    i = consumed
                result.append(item)
            else:
                i += 1

        return result, i


def parse_toon(text: str) -> dict[str, Any]:
    """Functional shortcut: ``ToonParser().parse(text)``."""
    return ToonParser().parse(text)
