"""Command-line view for the E04 Antigravity report demo."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from pydantic import ValidationError

from source.config import ConfigurationError, load_settings
from source.Control.evaluation_controller import EvaluationController
from source.service.evaluation_service import EvaluationService
from source.service.providers.factory import create_evidence_interpreter
from source.service.providers.interfaces import ProviderFailureError


def run() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate one answer and write a rubric report."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument(
        "--output", type=Path, default=Path(".local/e04-report.json")
    )
    parser.add_argument(
        "--provider", choices=("antigravity", "gemini", "fixture"), default="antigravity"
    )
    parser.add_argument(
        "--antigravity-executable",
        help="Path to agy.exe when it is not on PATH.",
    )
    args = parser.parse_args()

    variables = dict(os.environ)
    variables["EVALUATION_PROVIDER"] = args.provider
    if args.antigravity_executable:
        variables["ANTIGRAVITY_EXECUTABLE"] = args.antigravity_executable
    try:
        settings = load_settings(variables)
        interpreter = create_evidence_interpreter(settings)
        controller = EvaluationController(EvaluationService(), interpreter, settings.provider.value)
        report = controller.evaluate_file(args.input, args.output)
    except (
        ConfigurationError,
        ProviderFailureError,
        ValidationError,
        ValueError,
        OSError,
    ) as error:
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        print(f"Evaluation failed: {error}", file=sys.stderr)
        return 2

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    result = report["result"]
    print(
        f"Evaluation complete: {result['totalScore']}/"
        f"{result['maximumScore']} | model={report['modelId']}"
    )
    for item in report["feedbackItems"]:
        score = "unresolved" if item["score"] is None else str(item["score"])
        print(f"- {item['label']}: {score} | {item['message']}")
    print(f"Report saved: {args.output.resolve()}")
    return 0
