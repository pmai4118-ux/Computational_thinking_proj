import argparse
import json
import sys

from source.Control.evaluationController import EvaluationController
from source.Model.evaluationData import EvaluationReport


class EvaluationView:
    def __init__(self, controller: EvaluationController):
        self.controller = controller

    def renderReport(self, report: EvaluationReport) -> str:
        lines = ["ANSWER EVALUATION - PoC", f"Interpretation source: {report.providerName} / {report.modelName}"]
        if report.inputs.exampleOnly:
            lines.append("This authored example has not been independently reviewed and does not measure AI quality.")
        lines.append("Scope: this answer to this question only; no overall competency claim.")
        rubricMap = {item.rubricId: item for item in report.inputs.rubrics}
        feedbackMap = {item.resultId: item for item in report.feedbackItems}
        for result in report.results:
            rubric = rubricMap[result.rubricId]
            allowedScores = ", ".join(f"{item.value:g}" for item in rubric.scoreLevels)
            scoreLabel = "Insufficient evidence" if result.score is None else f"{result.score:g}"
            lines.extend(["", f"{rubric.competency}: {scoreLabel} | Levels: {allowedScores}"])
            lines.append(feedbackMap[result.resultId].explanation)
            for check in result.criterionChecks:
                for evidence in check.evidence:
                    quote = f'"{evidence.quote}"' if evidence.quote is not None else "[No excerpt: omission observation]"
                    lines.append(f"  [{check.criterionId}] {evidence.location}: {quote}")
        return "\n".join(lines)

    def readArguments(self, arguments: list[str] | None = None) -> argparse.Namespace:
        parser = argparse.ArgumentParser(description="Evaluate an answer using rubric criteria and evidence.")
        parser.add_argument("--input", required=True, help="JSON containing the question, rubrics, and answer.")
        parser.add_argument("--provider", choices=("gemini", "recorded"), default="gemini")
        parser.add_argument("--recording", help="Recorded interpretation, for recorded mode only.")
        parser.add_argument("--answerFile", help="UTF-8 file containing a new original answer.")
        parser.add_argument("--output", help="JSON report path; existing files are never overwritten.")
        parser.add_argument("--format", choices=("text", "json"), default="text")
        return parser.parse_args(arguments)

    def run(self, arguments: list[str] | None = None) -> int:
        args = self.readArguments(arguments)
        for stream in (sys.stdout, sys.stderr):
            if hasattr(stream, "reconfigure"):
                stream.reconfigure(encoding="utf-8")
        response = self.controller.submitAnswer({
            "inputPath": args.input,
            "providerName": args.provider,
            "recordingPath": args.recording,
            "answerPath": args.answerFile,
            "outputPath": args.output,
        })
        if response.error is not None:
            print(json.dumps({"error": response.error.model_dump(mode="json")}, ensure_ascii=False), file=sys.stderr)
            return 1
        report = response.report
        print(report.model_dump_json(indent=2) if args.format == "json" else self.renderReport(report))
        print(f"Report saved: {response.outputPath}", file=sys.stderr)
        return 0
