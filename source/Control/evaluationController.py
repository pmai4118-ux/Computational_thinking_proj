from collections.abc import Mapping

from pydantic import ValidationError

from source.Control.evaluationSchemas import EvaluationFailure, EvaluationRequest, EvaluationResponse
from source.service.evaluationErrors import EvaluationError
from source.service.evaluationService import EvaluationService


class EvaluationController:
    def __init__(self, service: EvaluationService):
        self.service = service

    def submitAnswer(self, requestData: Mapping[str, object]) -> EvaluationResponse:
        try:
            request = EvaluationRequest.model_validate(requestData)
            report, outputPath = self.service.evaluateFiles(
                request.inputPath, request.providerName, request.recordingPath,
                request.answerPath, request.outputPath,
            )
            return EvaluationResponse(report=report, outputPath=outputPath)
        except EvaluationError as error:
            failure = EvaluationFailure(code=error.code, message=error.message, retryable=error.retryable)
        except ValidationError as error:
            fields = tuple(".".join(str(part) for part in issue["loc"]) for issue in error.errors(include_input=False))
            failure = EvaluationFailure(code="invalidInput", message="Invalid request structure or values.", fields=fields)
        except FileExistsError:
            failure = EvaluationFailure(code="outputExists", message="The report already exists. Choose a new path to preserve it.")
        except UnicodeError:
            failure = EvaluationFailure(code="invalidEncoding", message="The input file must use UTF-8 encoding.")
        except OSError:
            failure = EvaluationFailure(code="fileError", message="Cannot read or write the UTF-8 file. Check its path, permissions, and size.")
        return EvaluationResponse(error=failure)
