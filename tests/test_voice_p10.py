"""P10: voice guide scripts, stale-audio protection, fallback player, both views render."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import app.strings as T
import app.voice as voice

ROOT = Path(__file__).resolve().parents[1]
NAMES = ("VOICE_INSPECTOR_SCRIPT", "VOICE_COMMUNITY_SCRIPT", "VOICE_READ_ALOUD", "VOICE_STOP", "VOICE_NO_VOICE", "VOICE_TRANSCRIPT")


@pytest.mark.parametrize("lang", ["bn", "en"])
def test_scripts_exist_are_short_and_neutral(lang: str) -> None:
    T.set_language(lang)
    for name in ("VOICE_INSPECTOR_SCRIPT", "VOICE_COMMUNITY_SCRIPT"):
        text = getattr(T, name)
        assert 150 < len(text) < 1100, (name, len(text))  # about 40-80 seconds spoken
        assert "{" not in text and "<" not in text and "http" not in text
        lowered = text.lower()
        assert not any(w in lowered for w in ("violation", "hazardous", "illegal", "advisory", "16131", "১৬১৩১", "লঙ্ঘন", "বিপজ্জনক"))


def test_catalogues_have_all_voice_names() -> None:
    for lang in ("bn", "en"):
        T.set_language(lang)
        assert all(getattr(T, n) for n in NAMES)


def test_audio_used_only_when_hash_matches(tmp_path: Path) -> None:
    (tmp_path / "guide_community_en.mp3").write_bytes(b"ID3")
    assert voice.current_audio("community", "en", "hello", tmp_path) is None  # no manifest
    (tmp_path / voice.MANIFEST).write_text(json.dumps({"guide_community_en.mp3": voice.script_hash("hello")}))
    assert voice.current_audio("community", "en", "hello", tmp_path) is not None
    assert voice.current_audio("community", "en", "hello edited", tmp_path) is None  # stale script
    assert voice.current_audio("inspector", "en", "hello", tmp_path) is None  # file missing


def test_committed_audio_if_any_matches_current_scripts() -> None:
    import importlib

    manifest = voice.AUDIO_DIR / voice.MANIFEST
    if not manifest.is_file():
        pytest.skip("voice files not rendered yet (run tools/generate_voice_guides.py)")
    for lang in voice.LANGUAGES:
        # read the catalogue module directly: T.set_language() is a no-op outside a Streamlit session
        catalogue = importlib.import_module(f"app.strings_{lang}")
        for view, name in (("inspector", "VOICE_INSPECTOR_SCRIPT"), ("community", "VOICE_COMMUNITY_SCRIPT")):
            assert voice.current_audio(view, lang, getattr(catalogue, name)) is not None, (view, lang)


def test_voice_component_follows_streamlit_protocol_and_is_accessible() -> None:
    page = (ROOT / "app" / "components" / "voice_guide" / "index.html").read_text(encoding="utf-8")
    assert "streamlit:componentReady" in page and "streamlit:setFrameHeight" in page
    assert "streamlit:setComponentValue" not in page  # one-way: can never trigger a rerun
    assert "aria-pressed" in page and 'role="status"' in page and ":focus-visible" in page
    assert "textContent" in page and "innerHTML" not in page  # script text is never parsed as HTML
    assert voice.speech_lang("bn") == "bn-BD" and voice.speech_lang("en") == "en-US"
    assert "let playing" in page  # own play state, not synth.speaking (unreliable between chunks)
    assert "chunks(" in page  # long scripts are spoken sentence by sentence (Chrome cuts long utterances)


pytest.importorskip("streamlit")
pytest.importorskip("geopandas")
pytest.importorskip("pyarrow")
from tests.synthetic import write_parquet  # noqa: E402


@pytest.mark.parametrize("view", ["inspector", "community"])
@pytest.mark.parametrize("lang", ["bn", "en"])
def test_both_views_render_with_voice_guide(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, view: str, lang: str) -> None:
    from streamlit.testing.v1 import AppTest

    write_parquet(tmp_path)
    monkeypatch.setenv("DHOA_DATA_DIR", str(tmp_path))
    at = AppTest.from_file(str(ROOT / "app" / "streamlit_app.py"), default_timeout=120)
    at.session_state["dhoa_view_mode"] = view
    if view == "inspector":
        at.session_state["dhoa_role"] = "inspector"
        at.session_state["dhoa_staff_name"] = "Test"
    at.session_state["dhoa_lang"] = lang
    at.run()
    assert not at.exception


# ---- the friendly error card swallows exceptions, so assert on IT, not only at.exception ----
import sys  # noqa: E402


def _run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, view: str, lang: str = "bn"):
    from streamlit.testing.v1 import AppTest

    write_parquet(tmp_path)
    monkeypatch.setenv("DHOA_DATA_DIR", str(tmp_path))
    at = AppTest.from_file(str(ROOT / "app" / "streamlit_app.py"), default_timeout=120)
    at.session_state["dhoa_view_mode"] = view
    if view == "inspector":
        at.session_state["dhoa_role"] = "inspector"
        at.session_state["dhoa_staff_name"] = "Test"
    at.session_state["dhoa_lang"] = lang
    return at.run()


def _has_error_card(at) -> bool:
    return any("class='dhoa-state dhoa-state--error" in m.value for m in at.markdown if not m.value.lstrip().startswith("<style"))


@pytest.mark.parametrize("view", ["overview", "inspector", "community", "about"])
@pytest.mark.parametrize("lang", ["bn", "en"])
def test_no_view_shows_the_error_card(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, view: str, lang: str) -> None:
    at = _run(tmp_path, monkeypatch, view, lang)
    assert not at.exception and not _has_error_card(at)


def _no_audio(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Point the app's voice module at an empty audio folder (forces the browser-voice fallback)."""
    sys.path.insert(0, str(ROOT / "app"))
    import voice as app_voice  # the module object the app script imports

    empty = tmp_path / "no_audio"
    empty.mkdir()
    monkeypatch.setattr(app_voice, "AUDIO_DIR", empty)
    monkeypatch.setattr(app_voice.current_audio, "__defaults__", (empty,))
    return app_voice


@pytest.mark.parametrize("view", ["inspector", "community"])
def test_broken_voice_player_cannot_break_the_view(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, view: str) -> None:
    app_voice = _no_audio(monkeypatch, tmp_path)

    def boom(*_a: object, **_k: object) -> str:
        raise RuntimeError("player broke")

    monkeypatch.setattr(app_voice, "speech_lang", boom)
    at = _run(tmp_path, monkeypatch, view)
    assert not _has_error_card(at)
    assert len(at.get("selectbox")) + len(at.button) > 0  # the page body still rendered


@pytest.mark.parametrize("view", ["inspector", "community"])
@pytest.mark.parametrize("lang", ["bn", "en"])
def test_without_audio_files_the_guide_is_still_offered(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, view: str, lang: str
) -> None:
    """No mp3: the heading, the browser read-aloud component and the written script are all shown."""
    import importlib

    _no_audio(monkeypatch, tmp_path)
    at = _run(tmp_path, monkeypatch, view, lang)
    catalogue = importlib.import_module(f"app.strings_{lang}")
    script = catalogue.VOICE_COMMUNITY_SCRIPT if view == "community" else catalogue.VOICE_INSPECTOR_SCRIPT
    assert not _has_error_card(at)
    assert any(f"**{catalogue.LISTEN_TO_THE_GUIDE}**" == m.value for m in at.markdown)
    assert catalogue.VOICE_TRANSCRIPT in [e.label for e in at.expander]
    assert any(m.value == script for m in at.markdown)  # the transcript text itself
    assert len(at.get("audio")) == 0  # no dead player


@pytest.mark.parametrize("view", ["inspector", "community"])
@pytest.mark.parametrize("lang", ["bn", "en"])
def test_committed_audio_files_play_in_the_popover(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, view: str, lang: str
) -> None:
    """The mp3s shipped in app/static/audio match the scripts and the player is rendered."""
    import importlib

    catalogue = importlib.import_module(f"app.strings_{lang}")
    at = _run(tmp_path, monkeypatch, view, lang)
    assert not _has_error_card(at)
    assert any(f"**{catalogue.LISTEN_TO_THE_GUIDE}**" == m.value for m in at.markdown)
    assert len(at.get("audio")) >= 1


@pytest.mark.parametrize("view", ["inspector", "community"])
def test_with_a_matching_audio_file_the_player_appears_in_the_popover(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, view: str
) -> None:
    import importlib

    sys.path.insert(0, str(ROOT / "app"))
    import voice as app_voice

    catalogue = importlib.import_module("app.strings_en")
    script = catalogue.VOICE_COMMUNITY_SCRIPT if view == "community" else catalogue.VOICE_INSPECTOR_SCRIPT
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    (audio_dir / app_voice.audio_name(view, "en")).write_bytes(b"ID3\x03\x00\x00\x00\x00\x00\x00")
    (audio_dir / app_voice.MANIFEST).write_text(json.dumps({app_voice.audio_name(view, "en"): app_voice.script_hash(script)}))
    monkeypatch.setattr(app_voice, "AUDIO_DIR", audio_dir)
    monkeypatch.setattr(app_voice.current_audio, "__defaults__", (audio_dir,))
    at = _run(tmp_path, monkeypatch, view, "en")
    assert not _has_error_card(at)
    assert any(f"**{catalogue.LISTEN_TO_THE_GUIDE}**" == m.value for m in at.markdown)
    assert len(at.get("audio")) >= 1


def test_missing_component_folder_gives_a_message_not_a_blank_box(tmp_path: Path) -> None:
    assert voice.component_available() is True
    assert voice.component_available(tmp_path) is False
