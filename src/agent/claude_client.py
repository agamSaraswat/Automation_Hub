"""
Anthropic Claude SDK wrapper with tool-use support.

Provides a unified interface for all modules to call Claude,
with retry logic, token tracking, and structured output parsing.

When the ``ACTIVE_PROVIDER`` environment variable is set to anything other
than ``"anthropic"``, the four core methods (``complete``, ``complete_json``,
``complete_with_tools``, ``last_token_count``) are transparently delegated to
:class:`~src.agent.provider_client.ProviderClient`, which supports Anthropic,
Gemini, Groq, and OpenRouter with automatic fallback.  All existing call sites
continue to work without any changes.
"""

import os
import json
import logging
from typing import Any

import anthropic
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


def _active_provider() -> str:
    return os.getenv("ACTIVE_PROVIDER", "anthropic").strip().lower()


class ClaudeClient:
    """Wrapper around the Anthropic Python SDK (or a multi-provider delegate)."""

    def __init__(
        self,
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> None:
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self._last_usage: anthropic.types.Usage | None = None

        # ── Multi-provider delegation ──────────────────────────────────────────
        if _active_provider() != "anthropic":
            from src.agent.provider_client import ProviderClient  # noqa: PLC0415

            self._delegate: ProviderClient | None = ProviderClient(
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            logger.info(
                "ClaudeClient delegating to ProviderClient (ACTIVE_PROVIDER=%s)",
                _active_provider(),
            )
        else:
            self._delegate = None

        # ── Native Anthropic client ────────────────────────────────────────────
        # Always initialised when a key is present so that run_agent_loop()
        # and other Anthropic-specific methods keep working even when a
        # non-Anthropic provider is the primary.
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if api_key:
            self.client = anthropic.Anthropic(api_key=api_key)
            logger.info("ClaudeClient Anthropic SDK initialised with model=%s", self.model)
        elif _active_provider() == "anthropic":
            raise EnvironmentError(
                "ANTHROPIC_API_KEY is not set. "
                "Add it to your .env file or export it."
            )
        else:
            # Non-Anthropic primary; Anthropic features that require the SDK
            # (run_agent_loop) will raise at call time if the key is absent.
            self.client = None  # type: ignore[assignment]
            logger.warning(
                "ANTHROPIC_API_KEY not set; run_agent_loop() will not be available"
            )

    # ── Simple completion ──────────────────────────────────────────────────────
    def complete(
        self,
        prompt: str,
        system: str = "",
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> str:
        """Send a single user message and return the text response."""
        if self._delegate is not None:
            return self._delegate.complete(
                prompt, system=system, temperature=temperature, max_tokens=max_tokens
            )

        temp = temperature if temperature is not None else self.temperature
        tokens = max_tokens if max_tokens is not None else self.max_tokens

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=tokens,
                temperature=temp,
                system=system if system else anthropic.NOT_GIVEN,
                messages=[{"role": "user", "content": prompt}],
            )
            text = message.content[0].text
            self._last_usage = message.usage
            logger.debug(
                "Completion: %d input tokens, %d output tokens",
                message.usage.input_tokens,
                message.usage.output_tokens,
            )
            return text
        except anthropic.APIError as exc:
            logger.error("Claude API error: %s", exc)
            raise

    # ── Multi-turn conversation ────────────────────────────────────────────────
    def chat(
        self,
        messages: list[dict[str, str]],
        system: str = "",
        temperature: float | None = None,
    ) -> str:
        """Send a multi-turn conversation and return the assistant reply."""
        if self._delegate is not None:
            return self._delegate.chat(messages, system=system, temperature=temperature)

        temp = temperature if temperature is not None else self.temperature

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=temp,
                system=system if system else anthropic.NOT_GIVEN,
                messages=messages,
            )
            return message.content[0].text
        except anthropic.APIError as exc:
            logger.error("Claude API error in chat: %s", exc)
            raise

    # ── Tool-use completion ────────────────────────────────────────────────────
    def complete_with_tools(
        self,
        prompt: str,
        tools: list[dict[str, Any]],
        system: str = "",
        temperature: float | None = None,
    ) -> anthropic.types.Message:
        """
        Send a prompt with tool definitions.
        Returns the full Message object so the caller can
        inspect tool_use blocks and route accordingly.
        """
        if self._delegate is not None:
            return self._delegate.complete_with_tools(
                prompt, tools, system=system, temperature=temperature
            )

        temp = temperature if temperature is not None else self.temperature

        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=temp,
                system=system if system else anthropic.NOT_GIVEN,
                tools=tools,
                messages=[{"role": "user", "content": prompt}],
            )
            logger.debug("Tool completion stop_reason=%s", message.stop_reason)
            return message
        except anthropic.APIError as exc:
            logger.error("Claude API error (tools): %s", exc)
            raise

    # ── Tool-use loop (agentic) ────────────────────────────────────────────────
    def run_agent_loop(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        tool_handler: "callable",
        system: str = "",
        max_iterations: int = 10,
    ) -> str:
        """
        Run an agentic tool-use loop.

        tool_handler(name, input) -> str  is a function that
        executes the tool and returns the result as a string.

        Returns the final text response from Claude.
        """
        if self.client is None:
            raise EnvironmentError(
                "run_agent_loop() requires ANTHROPIC_API_KEY. "
                "Set it even when using a non-Anthropic primary provider."
            )

        temp = self.temperature

        for i in range(max_iterations):
            message = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=temp,
                system=system if system else anthropic.NOT_GIVEN,
                tools=tools,
                messages=messages,
            )

            # If Claude responded with text only, we're done
            if message.stop_reason == "end_turn":
                texts = [b.text for b in message.content if b.type == "text"]
                return "\n".join(texts)

            # Process tool use blocks
            tool_results = []
            assistant_content = message.content

            for block in assistant_content:
                if block.type == "tool_use":
                    logger.info(
                        "Agent loop [%d]: calling tool %s", i, block.name
                    )
                    try:
                        result = tool_handler(block.name, block.input)
                    except Exception as exc:
                        result = f"Error executing {block.name}: {exc}"
                        logger.error(result)

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(result),
                        }
                    )

            # Append assistant message and tool results
            messages.append({"role": "assistant", "content": assistant_content})
            messages.append({"role": "user", "content": tool_results})

        logger.warning("Agent loop hit max iterations (%d)", max_iterations)
        return "I reached my tool-use limit. Please try a simpler request."

    # ── JSON extraction helper ─────────────────────────────────────────────────
    def complete_json(
        self,
        prompt: str,
        system: str = "",
        temperature: float | None = None,
    ) -> dict[str, Any]:
        """Call Claude and parse the response as JSON."""
        if self._delegate is not None:
            return self._delegate.complete_json(
                prompt, system=system, temperature=temperature
            )

        text = self.complete(prompt, system=system, temperature=temperature)
        # Strip markdown fences if present
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()
        return json.loads(cleaned)

    # ── Token tracking ─────────────────────────────────────────────────────────
    def last_token_count(self) -> int:
        """Return total tokens (input + output) used by the most recent complete() call."""
        if self._delegate is not None:
            return self._delegate.last_token_count()
        if self._last_usage is None:
            return 0
        return self._last_usage.input_tokens + self._last_usage.output_tokens


if __name__ == "__main__":
    # Quick smoke test
    logging.basicConfig(level=logging.DEBUG)
    client = ClaudeClient()
    reply = client.complete("Say 'hello' in one word.")
    print(f"Reply: {reply}")
