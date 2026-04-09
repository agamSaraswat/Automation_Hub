"""
Planner → Generator → Evaluator Adversarial Harness

Reference: adversarial-dev (Cole Medin)
Pattern: Planner decides strategy, Generator produces output, Evaluator challenges.
Sprint contracts define minimum acceptable fields per pipeline.

This Python implementation adapts the TS adversarial-dev pattern for AKTIVIQ skills.
"""

import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from src.agent.claude_client import ClaudeClient

logger = logging.getLogger(__name__)


class HarnessPhase(Enum):
    """Harness execution phases."""
    PLANNING = "planning"
    GENERATION = "generation"
    EVALUATION = "evaluation"
    RESOLUTION = "resolution"


@dataclass
class SprintContract:
    """
    Defines the minimum acceptable output fields and constraints for a harness run.
    
    Example:
        SprintContract(
            name="resume_tailoring",
            required_fields=["tailored_resume", "harness_trace"],
            max_iterations=3,
            evaluator_strictness="high"
        )
    """
    name: str
    required_fields: list[str]
    max_iterations: int = 3
    evaluator_strictness: str = "medium"  # "low", "medium", "high"
    skip_evaluator: bool = False  # If True, trust Generator output


@dataclass
class PlannerOutput:
    """Strategy decided by Planner."""
    strategy: dict[str, Any]
    rationale: str
    extracted_context: dict[str, Any]


@dataclass
class GeneratorOutput:
    """Output produced by Generator."""
    output: dict[str, Any]
    reasoning: str
    constraints_satisfied: dict[str, bool]


@dataclass
class EvaluatorOutput:
    """Evaluation result from Evaluator."""
    verdict: str  # "pass", "fail", "needs_revision"
    score: float  # 0–1
    challenges: list[dict[str, Any]]
    approved_claims: list[dict[str, Any]]
    suggestions: list[str]
    confidence: float  # How sure the Evaluator is


@dataclass
class HarnessTrace:
    """Full execution trace of Planner → Generator → Evaluator."""
    phase: HarnessPhase
    planner_output: Optional[PlannerOutput] = None
    generator_output: Optional[GeneratorOutput] = None
    evaluator_output: Optional[EvaluatorOutput] = None
    iteration: int = 0
    tokens_used: int = 0


class PlannerGeneratorEvaluator:
    """
    Adversarial harness implementing Planner → Generator → Evaluator pattern.
    
    Usage:
        harness = PlannerGeneratorEvaluator(contract=SprintContract(...))
        result = harness.run(
            planner_prompt=...,
            generator_prompt=...,
            evaluator_prompt=...,
            context={...}
        )
    """

    def __init__(self, contract: SprintContract):
        self.contract = contract
        self.client = ClaudeClient()
        self.traces: list[HarnessTrace] = []
        self.total_tokens = 0

    def run(
        self,
        planner_prompt: str,
        generator_prompt: str,
        evaluator_prompt: str,
        context: dict[str, Any],
        system_prompt: str = "",
    ) -> dict[str, Any]:
        """
        Execute full harness: Planner → Generator → Evaluator.
        
        Args:
            planner_prompt: Prompt for Planner phase
            generator_prompt: Prompt for Generator phase
            evaluator_prompt: Prompt for Evaluator phase (receives Generator output)
            context: Shared context (resume, JD, etc.)
            system_prompt: System prompt for Claude
            
        Returns:
            Final result with trace, verdict, tokens_used
        """
        iteration = 0
        generator_output = None

        while iteration < self.contract.max_iterations:
            iteration += 1
            logger.info(f"[{self.contract.name}] Iteration {iteration}/{self.contract.max_iterations}")

            # Phase 1: Planner
            logger.info(f"[{self.contract.name}] Phase: PLANNING")
            planner_result = self._phase_planner(planner_prompt, context, system_prompt)
            self.total_tokens += planner_result.get("tokens_used", 0)

            # Phase 2: Generator
            logger.info(f"[{self.contract.name}] Phase: GENERATION")
            generator_result = self._phase_generator(
                generator_prompt,
                context,
                planner_result.get("planner_output", {}),
                system_prompt,
            )
            self.total_tokens += generator_result.get("tokens_used", 0)
            generator_output = generator_result.get("generator_output", {})

            # Skip Evaluator if contract says so
            if self.contract.skip_evaluator:
                logger.info(f"[{self.contract.name}] Evaluator skipped (contract)")
                break

            # Phase 3: Evaluator
            logger.info(f"[{self.contract.name}] Phase: EVALUATION")
            evaluator_result = self._phase_evaluator(
                evaluator_prompt,
                context,
                generator_output,
                system_prompt,
            )
            self.total_tokens += evaluator_result.get("tokens_used", 0)

            verdict = evaluator_result.get("evaluator_output", {}).get("verdict", "fail")
            logger.info(f"[{self.contract.name}] Evaluator verdict: {verdict}")

            # Check verdict
            if verdict == "pass":
                logger.info(f"[{self.contract.name}] ✓ Harness passed on iteration {iteration}")
                return {
                    "success": True,
                    "verdict": "pass",
                    "output": generator_output,
                    "harness_trace": {
                        "planner": planner_result.get("planner_output", {}),
                        "generator": generator_result.get("generator_output", {}),
                        "evaluator": evaluator_result.get("evaluator_output", {}),
                        "iterations": iteration,
                    },
                    "tokens_used": self.total_tokens,
                }
            elif verdict == "needs_revision":
                # Feed Evaluator feedback back to Generator
                feedback = evaluator_result.get("evaluator_output", {}).get("suggestions", [])
                logger.info(f"[{self.contract.name}] Evaluator suggests revision: {feedback}")
                # Optionally: update generator_prompt with feedback and re-run
                # For now, continue to next iteration
                continue
            else:
                # verdict == "fail"
                logger.warning(f"[{self.contract.name}] Evaluator failed hard")
                continue

        # Max iterations reached
        logger.warning(f"[{self.contract.name}] Max iterations ({self.contract.max_iterations}) reached")
        return {
            "success": False,
            "verdict": "max_iterations_reached",
            "output": generator_output or {},
            "harness_trace": self._build_trace_dict(),
            "tokens_used": self.total_tokens,
            "error": f"Harness did not converge within {self.contract.max_iterations} iterations",
        }

    def _phase_planner(
        self,
        prompt: str,
        context: dict[str, Any],
        system_prompt: str,
    ) -> dict[str, Any]:
        """Execute Planner phase: decide strategy."""
        try:
            full_prompt = f"""
You are the Planner in a Planner-Generator-Evaluator harness.

TASK: Analyze the context and decide on a strategy for the following task.

CONTEXT:
{json.dumps(context, indent=2)}

TASK:
{prompt}

Respond with JSON:
{{
  "strategy": {{"goal": "...", "approach": "...", "key_decisions": [...]}},
  "rationale": "...",
  "extracted_context": {{"key_point_1": "...", "key_point_2": "..."}}
}}
"""
            response = self.client.complete(full_prompt, system=system_prompt, temperature=0.3)
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]
            planner_output = json.loads(response.strip())

            return {
                "planner_output": planner_output,
                "tokens_used": self.client.last_token_count(),
            }
        except Exception as exc:
            logger.error(f"Planner phase failed: {exc}")
            return {
                "planner_output": {"strategy": {}, "rationale": f"Error: {exc}"},
                "tokens_used": 0,
            }

    def _phase_generator(
        self,
        prompt: str,
        context: dict[str, Any],
        planner_output: dict[str, Any],
        system_prompt: str,
    ) -> dict[str, Any]:
        """Execute Generator phase: produce output following Planner's strategy."""
        try:
            full_prompt = f"""
You are the Generator in a Planner-Generator-Evaluator harness.

PLANNER STRATEGY:
{json.dumps(planner_output, indent=2)}

CONTEXT:
{json.dumps(context, indent=2)}

TASK:
{prompt}

Generate the output following the Planner's strategy exactly. Respond with JSON containing:
{{
  "output": {{"...": "...", "required_field_1": "...", "required_field_2": "..."}},
  "reasoning": "Why you made these choices",
  "constraints_satisfied": {{"constraint_1": true, "constraint_2": false}}
}}

Constraints to satisfy:
{', '.join(self.contract.required_fields)}
"""
            response = self.client.complete(full_prompt, system=system_prompt, temperature=0.5)
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]
            generator_output = json.loads(response.strip())

            return {
                "generator_output": generator_output,
                "tokens_used": self.client.last_token_count(),
            }
        except Exception as exc:
            logger.error(f"Generator phase failed: {exc}")
            return {
                "generator_output": {"output": {}, "reasoning": f"Error: {exc}"},
                "tokens_used": 0,
            }

    def _phase_evaluator(
        self,
        prompt: str,
        context: dict[str, Any],
        generator_output: dict[str, Any],
        system_prompt: str,
    ) -> dict[str, Any]:
        """Execute Evaluator phase: challenge Generator's output with explainable reasoning."""
        try:
            full_prompt = f"""
You are the Evaluator in a Planner-Generator-Evaluator harness.

STRICTNESS LEVEL: {self.contract.evaluator_strictness}

GENERATOR OUTPUT:
{json.dumps(generator_output, indent=2)}

CONTEXT:
{json.dumps(context, indent=2)}

EVALUATION TASK:
{prompt}

Evaluate the Generator's output critically. Respond with JSON:
{{
  "verdict": "pass|needs_revision|fail",
  "score": 0.0–1.0,
  "challenges": [
    {{"claim": "...", "issue": "...", "severity": "critical|warning"}},
    ...
  ],
  "approved_claims": [
    {{"claim": "...", "reason": "..."}},
    ...
  ],
  "suggestions": ["suggestion_1", "suggestion_2"],
  "confidence": 0.0–1.0
}}

Verdicts:
- pass: Output meets all requirements, ready to use
- needs_revision: Can be fixed with suggestions
- fail: Fundamental issues, cannot be fixed in next iteration
"""
            response = self.client.complete(full_prompt, system=system_prompt, temperature=0.3)
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]
            evaluator_output = json.loads(response.strip())

            return {
                "evaluator_output": evaluator_output,
                "tokens_used": self.client.last_token_count(),
            }
        except Exception as exc:
            logger.error(f"Evaluator phase failed: {exc}")
            return {
                "evaluator_output": {"verdict": "fail", "challenges": [{"issue": str(exc)}]},
                "tokens_used": 0,
            }

    def _build_trace_dict(self) -> dict[str, Any]:
        """Convert traces to dict for JSON serialization."""
        return {
            "traces": [t.__dict__ for t in self.traces],
            "total_iterations": len(self.traces),
        }


# ── Utility: simple test harness ──────────────────────────────────────

def test_harness_simple():
    """Quick test of harness pattern."""
    contract = SprintContract(
        name="test_harness",
        required_fields=["summary", "recommendation"],
        max_iterations=2,
    )

    harness = PlannerGeneratorEvaluator(contract)
    result = harness.run(
        planner_prompt="Analyze this text and plan a summary strategy.",
        generator_prompt="Write a concise 1-line summary.",
        evaluator_prompt="Is the summary accurate and helpful?",
        context={"text": "The quick brown fox jumps over the lazy dog."},
    )

    print(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_harness_simple()
