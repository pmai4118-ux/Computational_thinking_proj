from typing import Protocol

from source.Model.answerData import EvaluationInput
from source.Model.evaluationData import Interpretation


class EvidenceInterpreter(Protocol):
    providerName: str
    modelName: str
    promptVersion: str
    lastRequestDurationMs: int | None

    def interpret(self, inputs: EvaluationInput) -> Interpretation:
        ...
