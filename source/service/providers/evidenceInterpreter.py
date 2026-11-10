import hashlib
import json
from typing import Protocol

from source.Model.answerData import EvaluationInput
from source.Model.evaluationData import Interpretation


class EvidenceInterpreter(Protocol):
    providerName: str
    modelName: str
    promptVersion: str

    def interpret(self, inputs: EvaluationInput) -> Interpretation:
        ...


def inputDigest(inputs: EvaluationInput) -> str:
    payload = json.dumps(inputs.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
