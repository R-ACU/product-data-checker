"""Real-mode client code, tested against a fake Anthropic client (no network, no cost)."""

import json
from types import SimpleNamespace

import anthropic
import httpx2 as httpx
import pytest
from conftest import FIXTURES

from product_data_checker import config, prompts
from product_data_checker.llm import (
    ClaudeProvider,
    MockProvider,
    load_api_key,
    parse_category_answer,
    parse_text_answer,
)

FACTS = {
    "marke": "Nordfels",
    "kategorie": "Bohrer",
    "laenge_mm": 84.0,
    "gewicht_g": 14.0,
    "nennmass_mm": 6.0,
}
GOOD = json.dumps(
    {
        "titel": "Nordfels Bohrer 6 mm",
        "kurzbeschreibung": "Bohrer mit 6 mm Durchmesser.",
        "fehlende_angaben": [],
    }
)


def response(text=GOOD, stop_reason="end_turn"):
    return SimpleNamespace(
        stop_reason=stop_reason,
        content=[
            SimpleNamespace(type="thinking", thinking=""),
            SimpleNamespace(type="text", text=text),
        ],
        usage=SimpleNamespace(input_tokens=300, output_tokens=60),
    )


class FakeMessages:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class FakeClient:
    def __init__(self, result):
        self.messages = FakeMessages(result)
        self.beta = SimpleNamespace(messages=FakeMessages(result))


def provider(tmp_path, result=None):
    return ClaudeProvider(
        api_key="test", cache_dir=tmp_path / "cache", client=FakeClient(result or response())
    )


def test_text_request_shape(tmp_path):
    p = provider(tmp_path)
    call = p.write_copy("X-1", FACTS)
    assert parse_text_answer(call.text)[0].titel == "Nordfels Bohrer 6 mm"
    req = p.client.beta.messages.calls[0]
    assert req["model"] == config.TEXT_MODEL == "claude-sonnet-5-5"
    assert req["fallbacks"] == "default"
    assert "server-side-fallback-2026-07-01" in req["betas"]
    assert req["output_config"]["format"]["schema"] == prompts.TEXT_SCHEMA
    assert req["output_config"]["effort"] == "low"
    assert req["system"] == prompts.TEXT_SYSTEM
    content = req["messages"][0]["content"]
    assert content.startswith("<produktdaten>") and '"laenge_mm": 84.0' in content
    assert "thinking" not in req and "temperature" not in req


def test_classify_uses_haiku_with_enum(tmp_path):
    p = provider(tmp_path, response(json.dumps({"kategorie": "Bohrer"})))
    call = p.classify("X-1", {"bezeichnung": "Metallbohrer 6 mm"})
    assert parse_category_answer(call.text) == "Bohrer"
    req = p.client.messages.calls[0]
    assert req["model"] == config.CLASSIFY_MODEL == "claude-haiku-5-5"
    enum = req["output_config"]["format"]["schema"]["properties"]["kategorie"]["enum"]
    assert set(enum) == set(config.CATEGORIES) | {config.CATEGORY_UNCLEAR}


def test_answers_are_cached(tmp_path):
    p = provider(tmp_path)
    p.write_copy("X-1", FACTS)
    p.write_copy("X-1", FACTS)
    assert len(p.client.beta.messages.calls) == 1
    assert p.usage == {"input_tokens": 300, "output_tokens": 60, "calls": 1}


@pytest.mark.parametrize(
    "stop, message", [("refusal", "abgelehnt"), ("max_tokens", "abgeschnitten")]
)
def test_unusable_stop_reasons(tmp_path, stop, message):
    call = provider(tmp_path, response(stop_reason=stop)).write_copy("X-1", FACTS)
    assert call.text is None and message in call.error


def _error(cls, status):
    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    return cls("fail", response=httpx.Response(status, request=req), body=None)


@pytest.mark.parametrize(
    "exc, message",
    [
        (_error(anthropic.RateLimitError, 429), "Rate-Limit"),
        (_error(anthropic.AuthenticationError, 401), "Schlüssel"),
        (_error(anthropic.InternalServerError, 500), "API-Fehler 500"),
        (
            anthropic.APIConnectionError(
                request=httpx.Request("POST", "https://api.anthropic.com")
            ),
            "Verbindung",
        ),
    ],
)
def test_api_errors_become_review_items(tmp_path, exc, message):
    call = provider(tmp_path, exc).write_copy("X-1", FACTS)
    assert call.text is None and message in call.error


@pytest.mark.parametrize(
    "raw",
    [
        "Gerne! Hier ist der Text.",
        json.dumps({"titel": "x"}),
        json.dumps({"titel": "x", "kurzbeschreibung": "y", "fehlende_angaben": [], "extra": 1})
        + "}",
        None,
    ],
)
def test_bad_text_answers_are_rejected(raw):
    parsed, error = parse_text_answer(raw)
    assert parsed is None and error


@pytest.mark.parametrize(
    "raw", ['{"kategorie": "Handwerkzeug"}', '{"kategorie": "unklar"}', "Bohrer", "[]", None]
)
def test_category_must_be_in_taxonomy(raw):
    assert parse_category_answer(raw) == config.CATEGORY_UNCLEAR


def test_key_comes_only_from_env_file(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "from-process-env")
    assert load_api_key(tmp_path / ".env") is None
    (tmp_path / ".env").write_text("ANTHROPIC_API_KEY=from-file\n")
    assert load_api_key(tmp_path / ".env") == "from-file"


def test_mock_provider_replays_fixtures():
    mock = MockProvider(FIXTURES)
    sku = next(iter(mock.texts))
    assert mock.write_copy(sku, {}).text == mock.texts[sku]["raw"]
    assert mock.write_copy("UNBEKANNT", {}).text is None


@pytest.mark.parametrize(
    "raw",
    [
        '{"kategorie": ["Bohrer"]}',
        '{"kategorie": {}}',
        '{"kategorie": {"Bohrer": 1}}',
        '{"kategorie": 7}',
        '{"kategorie": null}',
        '"Bohrer"',
    ],
)
def test_non_string_category_goes_to_review_instead_of_crashing(raw):
    # used to raise TypeError (unhashable type) and abort the whole run
    assert parse_category_answer(raw) == config.CATEGORY_UNCLEAR


def test_unexpected_api_response_goes_to_review(tmp_path):
    req = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    exc = anthropic.APIResponseValidationError(response=httpx.Response(200, request=req), body=None)
    call = provider(tmp_path, exc).write_copy("X-1", FACTS)
    assert call.text is None and "unerwartete" in call.error


@pytest.mark.parametrize("content", ["{kaputt", '{"anders": 1}', '{"text": ["x"]}', ""])
def test_damaged_cache_entry_is_ignored(tmp_path, content):
    p = provider(tmp_path)
    p.write_copy("X-1", FACTS)
    cache_files = list((tmp_path / "cache").glob("*.json"))
    assert len(cache_files) == 1
    cache_files[0].write_text(content, encoding="utf-8")
    call = p.write_copy("X-1", FACTS)
    assert parse_text_answer(call.text)[0] is not None
    assert len(p.client.beta.messages.calls) == 2  # asked again instead of crashing


def test_api_key_is_not_kept_on_the_provider(tmp_path):
    p = ClaudeProvider(
        api_key="sk-ant-DUMMY", cache_dir=tmp_path / "cache", client=FakeClient(response())
    )
    assert "sk-" not in repr(p)
    assert "sk-" not in repr(vars(p))
