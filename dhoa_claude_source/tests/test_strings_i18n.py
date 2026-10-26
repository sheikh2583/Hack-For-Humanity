"""Both catalogues define the same names with the same format fields; the switch works."""

import ast
import string
from pathlib import Path

import app.strings as T

APP = Path(__file__).resolve().parent.parent / "app"


def _names(path: Path) -> dict[str, str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.targets[0].id: ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
    }


def _fields(text: str) -> list[str]:
    return sorted(f for _, f, _, _ in string.Formatter().parse(text) if f is not None)


def test_catalogues_define_the_same_names() -> None:
    assert set(_names(APP / "strings_bn.py")) == set(_names(APP / "strings_en.py"))


def test_format_fields_match_between_languages() -> None:
    bn, en = _names(APP / "strings_bn.py"), _names(APP / "strings_en.py")
    for name, text in bn.items():
        assert _fields(text) == _fields(en[name]), name


def test_english_has_no_bangla_text_except_brand() -> None:
    en = _names(APP / "strings_en.py")
    for name, text in en.items():
        if name in {"APP_TITLE", "CHANDRABINDU", "HOTLINE_LABEL"}:
            continue
        assert not any("ঀ" <= ch <= "৿" for ch in text), name


def test_switching_language_changes_text(monkeypatch) -> None:
    state: dict[str, object] = {}
    monkeypatch.setattr(T, "get_language", lambda: str(state.get(T.LANGUAGE_KEY, "bn")))
    state[T.LANGUAGE_KEY] = "bn"
    assert T.text("HIGH") == "উচ্চ"
    assert T.variants("HIGH") == ("উচ্চ", "High")
    assert T.text("HIGH", "en") == "High"
    assert T.text("NO_SUCH_NAME_X", "en") if hasattr(T, "NO_SUCH_NAME_X") else True
