from source.Model.answerData import EvaluationInput
from source.Model.evaluationData import Interpretation, RecordedReview
from source.service.evaluationErrors import EvaluationError
from source.service.providers.evidenceInterpreter import inputDigest


class RecordedInterpreter:
    providerName = "recorded"
    modelName = "Dữ liệu diễn giải có sẵn; không phải AI đang chấm"
    promptVersion = "recorded/1"

    def __init__(self, recording: RecordedReview):
        self.recording = recording

    def interpret(self, inputs: EvaluationInput) -> Interpretation:
        if self.recording.inputHash != inputDigest(inputs):
            raise EvaluationError("recordingMismatch", "Bản diễn giải không thuộc đúng câu hỏi, rubric và bài gốc này.")
        return self.recording.interpretation
