"""Model access: a mock provider (fixed answers from fixtures/) and the real Claude API.

Both providers return the model's *raw text*. Parsing and validation happen in one
place (``parse_text_answer`` / ``parse_category_answer``), so the mock exercises exactly
the same checks as the real API.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import threading
from dataclasses import InitVar, dataclass, field
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field, ValidationError

from . import config, prompts


class TextAnswer(BaseModel):
    titel: str = Field(max_length=400)
    kurzbeschreibung: str = Field(max_length=2000)
    fehlende_angaben: list[str] = Field(default_factory=list, max_length=20)


@dataclass
class ModelCall:
    """Outcome of one model request. ``text`` is None when nothing usable came back."""

    text: str | None
    error: str = ""
    input_tokens: int = 0
    output_tokens: int = 0


class Provider(Protocol):
    name: str

    def write_copy(self, sku: str, facts: dict) -> ModelCall: ...

    def classify(self, sku: str, fields: dict) -> ModelCall: ...


def parse_text_answer(raw: str | None) -> tuple[TextAnswer | None, str]:
    if raw is None:
        return None, "keine Antwort"
    try:
        return TextAnswer.model_validate_json(raw), ""
    except ValidationError as exc:
        first = exc.errors()[0]
        return None, f"Antwort passt nicht ins Schema ({first['type']})"


def parse_category_answer(raw: str | None) -> str:
    """Return a taxonomy category, or ``config.CATEGORY_UNCLEAR`` for anything else."""
    if raw is None:
        return config.CATEGORY_UNCLEAR
    try:
        value = json.loads(raw).get("kategorie")
    except (json.JSONDecodeError, AttributeError):
        return config.CATEGORY_UNCLEAR
    # a list or object would raise TypeError in the membership test: only strings count
    if isinstance(value, str) and value in config.CATEGORIES:
        return value
    return config.CATEGORY_UNCLEAR


# --- Mock ------------------------------------------------------------------------


class MockProvider:
    """Replays recorded answers from fixtures/llm/*.json. No network, no cost."""

    name = "mock"

    def __init__(self, fixtures_dir: Path):
        self.texts = self._load(fixtures_dir / "texts.json")
        self.categories = self._load(fixtures_dir / "categories.json")

    @staticmethod
    def _load(path: Path) -> dict:
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        return {k: v for k, v in data.items() if not k.startswith("_")}

    def write_copy(self, sku: str, facts: dict) -> ModelCall:
        entry = self.texts.get(sku)
        if entry is None:
            return ModelCall(None, "kein Mock-Text für diese Artikelnummer hinterlegt")
        return ModelCall(entry["raw"])

    def classify(self, sku: str, fields: dict) -> ModelCall:
        entry = self.categories.get(sku)
        if entry is None:
            return ModelCall(None, "keine Mock-Einordnung hinterlegt")
        return ModelCall(entry["raw"])


# --- Claude API -------------------------------------------------------------------


@dataclass
class ClaudeProvider:
    """Real mode. Reads the key only from the local .env file passed in by the CLI.

    The key is handed to the SDK client and not kept on this object (``InitVar``), so it
    cannot show up in a repr, a log line or a traceback with local variables.

    Answers are cached on disk by (model, prompt version, input), so a second run over
    the same list costs nothing.
    """

    api_key: InitVar[str | None]
    cache_dir: Path
    client: object = field(default=None, repr=False)  # injectable for tests
    name: str = "claude"
    usage: dict = field(default_factory=lambda: {"input_tokens": 0, "output_tokens": 0, "calls": 0})
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def __post_init__(self, api_key: str | None) -> None:
        if self.client is None:
            import anthropic

            self.client = anthropic.Anthropic(api_key=api_key, max_retries=3, timeout=60)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, kind: str, model: str, payload: dict) -> Path:
        key = json.dumps(
            [kind, model, prompts.PROMPT_VERSION, payload], sort_keys=True, ensure_ascii=False
        )
        return self.cache_dir / f"{hashlib.sha256(key.encode()).hexdigest()[:32]}.json"

    def _call(self, kind: str, model: str, payload: dict, request: dict) -> ModelCall:
        import anthropic

        cache = self._cache_path(kind, model, payload)
        if cache.exists():
            try:
                cached = json.loads(cache.read_text(encoding="utf-8"))["text"]
                if isinstance(cached, str):
                    return ModelCall(cached)
            except (OSError, ValueError, KeyError, TypeError):
                pass  # damaged cache entry: ask again instead of failing the whole run
        try:
            if model == config.TEXT_MODEL:
                # Sonnet 5.5: server-side fallback re-runs a declined request on a
                # suitable model inside the same call.
                response = self.client.beta.messages.create(
                    model=model,
                    betas=["server-side-fallback-2026-07-01"],
                    fallbacks="default",
                    **request,
                )
            else:
                response = self.client.messages.create(model=model, **request)
        except anthropic.RateLimitError:
            return ModelCall(None, "Rate-Limit erreicht, später erneut versuchen")
        except anthropic.AuthenticationError:
            return ModelCall(None, "API-Schlüssel ungültig")
        except anthropic.APIStatusError as exc:
            return ModelCall(None, f"API-Fehler {exc.status_code}")
        except anthropic.APIConnectionError:
            return ModelCall(None, "keine Verbindung zur API")
        except anthropic.APIError:  # e.g. APIResponseValidationError: unexpected response
            return ModelCall(None, "unerwartete Antwort der API")

        usage = getattr(response, "usage", None)
        in_tok = getattr(usage, "input_tokens", 0) or 0
        out_tok = getattr(usage, "output_tokens", 0) or 0
        with self._lock:
            self.usage["input_tokens"] += in_tok
            self.usage["output_tokens"] += out_tok
            self.usage["calls"] += 1

        if response.stop_reason == "refusal":
            return ModelCall(None, "Modell hat die Anfrage abgelehnt", in_tok, out_tok)
        if response.stop_reason == "max_tokens":
            return ModelCall(None, "Antwort abgeschnitten (max_tokens)", in_tok, out_tok)
        text = "".join(
            str(getattr(b, "text", ""))
            for b in response.content
            if getattr(b, "type", "") == "text"
        )
        with contextlib.suppress(OSError):  # still usable when the cache cannot be written
            cache.write_text(json.dumps({"text": text}, ensure_ascii=False), encoding="utf-8")
        return ModelCall(text, "", in_tok, out_tok)

    def write_copy(self, sku: str, facts: dict) -> ModelCall:
        data = json.dumps(facts, ensure_ascii=False, sort_keys=True)
        request = {
            "max_tokens": 2048,
            "system": prompts.TEXT_SYSTEM,
            "output_config": {
                "effort": "low",
                "format": {"type": "json_schema", "schema": prompts.TEXT_SCHEMA},
            },
            "messages": [{"role": "user", "content": f"<produktdaten>\n{data}\n</produktdaten>"}],
        }
        return self._call("text", config.TEXT_MODEL, facts, request)

    def classify(self, sku: str, fields: dict) -> ModelCall:
        data = json.dumps(fields, ensure_ascii=False, sort_keys=True)
        request = {
            "max_tokens": 512,
            "system": prompts.CLASSIFY_SYSTEM,
            "output_config": {
                "effort": "low",
                "format": {"type": "json_schema", "schema": prompts.CLASSIFY_SCHEMA},
            },
            "messages": [{"role": "user", "content": f"<artikel>\n{data}\n</artikel>"}],
        }
        return self._call("classify", config.CLASSIFY_MODEL, fields, request)


def load_api_key(env_file: Path) -> str | None:
    """Read ANTHROPIC_API_KEY from the local .env only, never from the process env."""
    from dotenv import dotenv_values

    if not env_file.exists():
        return None
    value = dotenv_values(env_file).get("ANTHROPIC_API_KEY")
    return value.strip() if value else None
