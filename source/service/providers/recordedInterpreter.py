from source.Model.answerData import EvaluationInput
from source.Model.evaluationData import Interpretation, RecordedReview
from source.service.evaluationErrors import EvaluationError
from source.service.providers.evidenceInterpreter import inputDigest


class RecordedInterpreter:
    providerName = "recorded"
    modelName = "Recorded interpretation; no live AI assessment"
    promptVersion = "recorded/1"

    def __init__(self, recording: RecordedReview):
        self.recording = recording

    def interpret(self, inputs: EvaluationInput) -> Interpretation:
        if self.recording.inputHash != inputDigest(inputs):
            raise EvaluationError("recordingMismatch", "The recorded interpretation does not match this question, rubric, and original answer.")
        return self.recording.interpretation
