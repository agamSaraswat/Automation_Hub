"""
Multi-provider LLM client with automatic fallback.

Supports Anthropic, Gemini, Groq, and OpenRouter backends
behind a single ClaudeClient-compatible interface.

Environment variables
---------------------
ACTIVE_PROVIDER      Primary provider (default: anthropic).
                     Supported: anthropic | gemini | groq | openrouter
FALLBACK_CHAIN       Comma-separated fallback order, tried after the primary
                     fails.  Example: "gemini,groq,openrouter"
                     If unset, all remaining providers are tried in the default
                     order above.

PLANNER_PROVIDER     Override provider for the harness planner phase.
GENERATOR_PROVIDER   Override provider for the harness generator phase.
EVALUATOR_PROVIDER   Override provider for the harness evaluator phase.

ANTHROPIC_API_KEY    Anthropic secret key.
GEMINI_API_KEY       Google Gemini secret key.
GROQ_API_KEY         Groq secret key.
OPENROUTER_API_KEY   OpenRouter secret key.
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any

import anthropic
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

# ── Provider constants ─────────────────────────────────────────────────────────

SUPPORTED_PROVIDERS = frozenset({"anthropic", "gemini", "groq", "openrouter"})

DEFAULT_MODELS: dict[str, str] = {
    "anthropic": "claude-sonnet-4-6",
    "gemini": "gemini-2.0-flash",
    "groq": "llama-3.3-70b-versatile",
    "openrouter": "openai/gpt-4o-mini",
}

_OPENROUTER_BASE = "https://openrouter.ai/api/v1"

_ROLE_ENV: dict[str, str] = {
    "planner": "PLANNER_PROVIDER",
    "generator": "GENERATOR_PROVIDER",
    "evaluator": "EVALUATOR_PROVIDER",
}

# Expected JSON shape when simulating tool calls for non-Anthropic providers.
_SIM_JSON_TEMPLATE = (
    '{"jobs": [{"title": "...", "company": "...", "url": "...", '
    '"location": "...", "jd_snippet": "..."}]}'
)


# ── Minimal message-like types for non-Anthropic completions ──────────────────

@dataclass
class _TextBlock:
    """Mirrors the text variant of anthropic.types.ContentBlock."""
    type: str = "text"
    text: str = ""


@dataclass
class _ToolUseBlock:
    """Mirrors the tool_use variant of anthropic.types.ContentBlock."""
    type: str = "tool_use"
    id: str = "simulated_tool_0"
    name: str = ""
    input: dict = field(default_factory=dict)


@dataclass
class _SimulatedMessage:
    """
    Minimal stand-in for anthropic.types.Message.

    Used when a non-Anthropic provider services a complete_with_tools() call
    so that callers (e.g. run_agent_loop) can treat the return value uniformly.
    """
    content: list = field(default_factory=list)
    stop_reason: str = "end_turn"


# ── Internal sentinel ─────────────────────────────────────────────────────────

class _RateLimitError(Exception):
    """Raised internally when a provider signals rate limiting."""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _format_tools_as_text(tools: list[dict]) -> str:
    """Render Anthropic-style tool definitions as human-readable text."""
    lines: list[str] = []
    for t in tools:
        name = t.get("name", "unknown")
        desc = t.get("description", "No description provided.")
        params = t.get("input_schema", {}).get("properties", {})
        param_names = ", ".join(params.keys()) if params else "none"
        lines.append(f"  • {name}({param_names}): {desc}")
    return "\n".join(lines)


def _extract_json(text: str) -> dict[str, Any]:
    """
    Try multiple strategies to extract a JSON object from *text*.

    Strategy order
    --------------
    1. Direct parse of the stripped text.
    2. Strip one layer of markdown fences (``` or ```json).
    3. Slice from the first ``{`` to the last ``}``.
    4. Regex search for the outermost ``{...}`` block.

    Raises ``json.JSONDecodeError`` if all strategies fail.
    """
    cleaned = text.strip()

    # Strategy 1 — direct
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Strategy 2 — strip markdown fences
    fence_stripped = cleaned
    if fence_stripped.startswith("```"):
        fence_stripped = fence_stripped.split("\n", 1)[-1]
    if fence_stripped.endswith("```"):
        fence_stripped = fence_stripped.rsplit("```", 1)[0]
    fence_stripped = fence_stripped.strip()
    try:
        return json.loads(fence_stripped)
    except json.JSONDecodeError:
        pass

    # Strategy 3 — first { to last }
    first = cleaned.find("{")
    last = cleaned.rfind("}")
    if first != -1 and last != -1 and last > first:
        try:
            return json.loads(cleaned[first : last + 1])
        except json.JSONDecodeError:
            pass

    # Strategy 4 — regex outermost object
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    raise json.JSONDecodeError("No valid JSON object found", text, 0)


def _resolve_provider(role: str | None) -> str:
    """Return the effective provider name for the given (optional) role."""
    if role and role in _ROLE_ENV:
        override = os.getenv(_ROLE_ENV[role], "").strip().lower()
        if override and override in SUPPORTED_PROVIDERS:
            return override
    default = os.getenv("ACTIVE_PROVIDER", "anthropic").strip().lower()
    if default not in SUPPORTED_PROVIDERS:
        raise ValueError(
            f"ACTIVE_PROVIDER={default!r} is not supported. "
            f"Choose from: {', '.join(sorted(SUPPORTED_PROVIDERS))}"
        )
    return default


def _build_chain(primary: str) -> list[str]:
    """Return the full ordered provider chain starting with *primary*."""
    raw = os.getenv("FALLBACK_CHAIN", "").strip()
    if raw:
        fallbacks = [p.strip().lower() for p in raw.split(",") if p.strip().lower() in SUPPORTED_PROVIDERS]
    else:
        fallbacks = [p for p in ("anthropic", "gemini", "groq", "openrouter") if p != primary]
    # Primary is always first; deduplicate while preserving order.
    seen: set[str] = {primary}
    chain = [primary]
    for p in fallbacks:
        if p not in seen:
            seen.add(p)
            chain.append(p)
    return chain


def _is_rate_limit(exc: Exception) -> bool:
    """Return True if *exc* represents a rate-limit/quota error."""
    if isinstance(exc, anthropic.RateLimitError):
        return True
    if isinstance(exc, _RateLimitError):
        return True
    try:
        from groq import RateLimitError as _GroqRLE  # type: ignore[import]
        if isinstance(exc, _GroqRLE):
            return True
    except ImportError:
        pass
    # Gemini wraps quota errors from google-api-core
    cls_name = type(exc).__qualname__
    if any(tag in cls_name for tag in ("ResourceExhausted", "QuotaExceeded", "TooManyRequests")):
        return True
    # HTTP 429 surfaces as a plain message from some providers
    if "429" in str(exc) or "rate limit" in str(exc).lower():
        return True
    return False


# ── ProviderClient ────────────────────────────────────────────────────────────

class ProviderClient:
    """
    Multi-provider LLM client with automatic fallback.

    Presents the same public interface as ``ClaudeClient`` so all existing
    call sites continue to work without modification:

        complete()            → str
        complete_json()       → dict
        complete_with_tools() → anthropic.types.Message-compatible object
        last_token_count()    → int

    The ``chat()`` method from ``ClaudeClient`` is also supported.

    Parameters
    ----------
    model:
        Model name for the *primary* provider.  Defaults to the built-in
        default for that provider.
    max_tokens:
        Maximum tokens to generate per call.
    temperature:
        Sampling temperature (0–1).
    role:
        One of "planner", "generator", "evaluator".  When set, the client
        reads the matching ``*_PROVIDER`` env var to select the provider.
    """

    def __init__(
        self,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        role: str | None = None,
    ) -> None:
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._last_token_count: int = 0

        self.primary_provider: str = _resolve_provider(role)
        self.model: str = model or DEFAULT_MODELS[self.primary_provider]
        self.provider_chain: list[str] = _build_chain(self.primary_provider)

        # Lazily initialised SDK clients
        self._anthropic_client: anthropic.Anthropic | None = None
        self._gemini_client: Any = None
        self._groq_client: Any = None

        logger.info(
            "ProviderClient ready: primary=%s  chain=%s  model=%s",
            self.primary_provider,
            self.provider_chain,
            self.model,
        )

    # ── Lazy SDK initialisation ───────────────────────────────────────────────

    def _get_anthropic(self) -> anthropic.Anthropic:
        if self._anthropic_client is None:
            key = os.getenv("ANTHROPIC_API_KEY", "")
            if not key:
                raise EnvironmentError("ANTHROPIC_API_KEY is not set.")
            self._anthropic_client = anthropic.Anthropic(api_key=key)
        return self._anthropic_client

    def _get_gemini(self) -> Any:
        if self._gemini_client is None:
            try:
                import google.genai as genai  # type: ignore[import]
            except ImportError as exc:
                raise ImportError(
                    "google-genai is required for the Gemini provider. "
                    "Run: pip install google-genai"
                ) from exc
            key = os.getenv("GEMINI_API_KEY", "")
            if not key:
                raise EnvironmentError("GEMINI_API_KEY is not set.")
            self._gemini_client = genai.Client(api_key=key)
        return self._gemini_client

    def _get_groq(self) -> Any:
        if self._groq_client is None:
            try:
                from groq import Groq  # type: ignore[import]
            except ImportError as exc:
                raise ImportError(
                    "groq is required for the Groq provider. "
                    "Run: pip install groq"
                ) from exc
            key = os.getenv("GROQ_API_KEY", "")
            if not key:
                raise EnvironmentError("GROQ_API_KEY is not set.")
            self._groq_client = Groq(api_key=key)
        return self._groq_client

    # ── Per-provider completions ──────────────────────────────────────────────

    def _complete_anthropic(
        self, prompt: str, system: str, temperature: float, max_tokens: int
    ) -> tuple[str, int]:
        client = self._get_anthropic()
        model = self.model if self.primary_provider == "anthropic" else DEFAULT_MODELS["anthropic"]
        msg = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system if system else anthropic.NOT_GIVEN,
            messages=[{"role": "user", "content": prompt}],
        )
        tokens = msg.usage.input_tokens + msg.usage.output_tokens
        return msg.content[0].text, tokens

    def _complete_gemini(
        self, prompt: str, system: str, temperature: float, max_tokens: int
    ) -> tuple[str, int]:
        import google.genai as genai  # type: ignore[import]
        client = self._get_gemini()
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        response = client.models.generate_content(
            model=DEFAULT_MODELS["gemini"],
            contents=full_prompt,
        )
        text: str = response.text
        try:
            meta = response.usage_metadata
            tokens = meta.prompt_token_count + meta.candidates_token_count
        except Exception:
            tokens = 0
        return text, tokens

    def _complete_groq(
        self, prompt: str, system: str, temperature: float, max_tokens: int
    ) -> tuple[str, int]:
        client = self._get_groq()
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        completion = client.chat.completions.create(
            model=DEFAULT_MODELS["groq"],
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        text = completion.choices[0].message.content or ""
        tokens = completion.usage.prompt_tokens + completion.usage.completion_tokens
        return text, tokens

    def _complete_openrouter(
        self, prompt: str, system: str, temperature: float, max_tokens: int
    ) -> tuple[str, int]:
        import requests as _req  # already in requirements.txt

        key = os.getenv("OPENROUTER_API_KEY", "")
        if not key:
            raise EnvironmentError("OPENROUTER_API_KEY is not set.")
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        resp = _req.post(
            f"{_OPENROUTER_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={
                "model": DEFAULT_MODELS["openrouter"],
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
            timeout=60,
        )
        if resp.status_code == 429:
            raise _RateLimitError(f"OpenRouter rate limit (HTTP 429): {resp.text[:200]}")
        resp.raise_for_status()
        data = resp.json()
        text = data["choices"][0]["message"]["content"] or ""
        usage = data.get("usage") or {}
        tokens = usage.get("prompt_tokens", 0) + usage.get("completion_tokens", 0)
        return text, tokens

    # ── Dispatch table ────────────────────────────────────────────────────────

    _DISPATCH: dict[str, str] = {
        "anthropic": "_complete_anthropic",
        "gemini": "_complete_gemini",
        "groq": "_complete_groq",
        "openrouter": "_complete_openrouter",
    }

    def _call_provider(
        self, provider: str, prompt: str, system: str, temperature: float, max_tokens: int
    ) -> tuple[str, int]:
        method = getattr(self, self._DISPATCH[provider])
        return method(prompt, system, temperature, max_tokens)

    # ── Public interface ──────────────────────────────────────────────────────

    def complete(
        self,
        prompt: str,
        system: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Send a single user message and return the text response."""
        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens if max_tokens is not None else self.max_tokens

        last_exc: Exception | None = None
        for provider in self.provider_chain:
            try:
                text, token_count = self._call_provider(provider, prompt, system, temp, tokens)
                self._last_token_count = token_count
                if provider != self.primary_provider:
                    logger.info("Fallback provider %s succeeded", provider)
                logger.debug(
                    "complete via %s: %d tokens", provider, token_count
                )
                return text
            except Exception as exc:
                logger.warning(
                    "Provider %s failed (%s: %s); trying next in chain",
                    provider,
                    type(exc).__name__,
                    exc,
                )
                last_exc = exc

        raise RuntimeError(
            f"All providers in chain {self.provider_chain} failed. "
            f"Last error: {last_exc}"
        ) from last_exc

    def chat(
        self,
        messages: list[dict[str, str]],
        system: str = "",
        temperature: float | None = None,
    ) -> str:
        """
        Send a multi-turn conversation and return the assistant reply.

        Uses the native messages API when the primary provider is Anthropic;
        for other providers the conversation is flattened into a single prompt.
        """
        temp = temperature if temperature is not None else self.temperature

        if self.primary_provider == "anthropic":
            try:
                client = self._get_anthropic()
                msg = client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    temperature=temp,
                    system=system if system else anthropic.NOT_GIVEN,
                    messages=messages,
                )
                return msg.content[0].text
            except Exception as exc:
                logger.warning("Anthropic chat failed, falling back: %s", exc)

        # Flatten conversation for providers without a native multi-turn API
        conversation = "\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in messages
        )
        return self.complete(conversation, system=system, temperature=temp)

    def complete_with_tools(
        self,
        prompt: str,
        tools: list[dict[str, Any]],
        system: str = "",
        temperature: float | None = None,
    ) -> Any:
        """
        Send a prompt with tool definitions.

        Tool execution path
        -------------------
        1. Always tries Anthropic first — it natively supports the full tool
           schema including ``web_search_20250305``.
        2. If Anthropic is unavailable (no key / rate-limited), falls back to
           a structured JSON simulation: the model is given a textual
           description of the tools and instructed to return ONLY a valid JSON
           object matching the jobs schema — no preamble, no markdown fences,
           no explanation.  The reply is parsed with multi-strategy extraction
           and returned as a ``_SimulatedMessage`` whose interface matches
           ``anthropic.types.Message``.

        Returns an object that supports the same attribute access as
        ``anthropic.types.Message`` (``content``, ``stop_reason``, each block's
        ``type`` / ``text`` / ``name`` / ``input`` / ``id``).
        """
        temp = temperature if temperature is not None else self.temperature

        # ── Step 1: try Anthropic natively ────────────────────────────────────
        if os.getenv("ANTHROPIC_API_KEY"):
            try:
                client = self._get_anthropic()
                native_model = (
                    self.model
                    if self.primary_provider == "anthropic"
                    else DEFAULT_MODELS["anthropic"]
                )
                message = client.messages.create(
                    model=native_model,
                    max_tokens=self.max_tokens,
                    temperature=temp,
                    system=system if system else anthropic.NOT_GIVEN,
                    tools=tools,
                    messages=[{"role": "user", "content": prompt}],
                )
                logger.debug(
                    "complete_with_tools via Anthropic, stop_reason=%s",
                    message.stop_reason,
                )
                return message
            except anthropic.RateLimitError:
                logger.warning(
                    "Anthropic rate-limited on tool call; simulating via fallback"
                )
            except anthropic.APIError as exc:
                logger.warning(
                    "Anthropic API error on tool call (%s); simulating via fallback", exc
                )

        # ── Step 2: simulate via fallback provider ────────────────────────────
        logger.info("Simulating tool call via non-Anthropic provider")
        tool_text = _format_tools_as_text(tools)
        sim_system = (
            (system + "\n\n" if system else "")
            + "You have access to the following tools:\n"
            + tool_text
            + "\n\n"
            + "CRITICAL INSTRUCTION: You MUST return ONLY a valid JSON object.\n"
            + "No preamble. No markdown fences. No explanation. No prose.\n"
            + "Your entire response must be parseable by json.loads().\n"
            + "Return ONLY JSON in this exact format:\n"
            + _SIM_JSON_TEMPLATE
        )

        text = self.complete(prompt, system=sim_system, temperature=temp)

        # Try to extract a JSON object from the response.
        try:
            parsed = _extract_json(text)
            logger.debug("Simulated tool call produced valid JSON")
            return _SimulatedMessage(
                content=[_TextBlock(text=json.dumps(parsed))],
                stop_reason="end_turn",
            )
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning(
                "Simulated tool call: JSON extraction failed (%s); "
                "returning raw text block",
                exc,
            )

        # Last resort — return whatever the model produced as plain text.
        return _SimulatedMessage(
            content=[_TextBlock(text=text)],
            stop_reason="end_turn",
        )

    def complete_json(
        self,
        prompt: str,
        system: str = "",
        temperature: float | None = None,
    ) -> dict[str, Any]:
        """Call the active provider and parse the response as JSON."""
        text = self.complete(prompt, system=system, temperature=temperature)
        return _extract_json(text)

    def last_token_count(self) -> int:
        """Return total tokens (input + output) from the most recent complete()."""
        return self._last_token_count
