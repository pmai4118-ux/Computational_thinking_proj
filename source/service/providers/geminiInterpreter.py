import json
import os
import re
import socket
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import ValidationError

from source.Model.answerData import EvaluationInput
from source.Model.evaluationData import Interpretation
from source.service.evaluationErrors import EvaluationError
from source.service.providers.evaluationPrompt import promptPayload, promptVersion, systemPrompt


class GeminiInterpreter:
    providerName = "gemini"
    promptVersion = promptVersion

    def __init__(self, apiKey: str, modelName: str, timeoutSeconds: float = 45):
        if not apiKey.strip() or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,119}", modelName):
            raise EvaluationError("providerConfig", "Cần GEMINI_API_KEY và GEMINI_MODEL hợp lệ, không thêm models/.")
        if not 1 <= timeoutSeconds <= 120:
            raise EvaluationError("providerConfig", "Timeout phải từ 1 đến 120 giây.")
        self.apiKey = apiKey
        self.modelName = modelName
        self.timeoutSeconds = timeoutSeconds

    @classmethod
    def fromEnvironment(cls):
        try:
            timeoutSeconds = float(os.environ.get("EVALUATION_TIMEOUT", "45"))
        except ValueError as error:
            raise EvaluationError("providerConfig", "EVALUATION_TIMEOUT phải là số giây.") from error
        return cls(os.environ.get("GEMINI_API_KEY", ""), os.environ.get("GEMINI_MODEL", ""), timeoutSeconds)

    def buildRequest(self, inputs: EvaluationInput) -> Request:
        payload = {
            "systemInstruction": {"parts": [{"text": systemPrompt()}]},
            "contents": [{"role": "user", "parts": [{"text": json.dumps(promptPayload(inputs), ensure_ascii=False)}]}],
            "generationConfig": {
                "candidateCount": 1,
                "maxOutputTokens": 16384,
                "responseMimeType": "application/json",
                "responseJsonSchema": Interpretation.model_json_schema(),
            },
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        if len(body) > 250000:
            raise EvaluationError("inputLimit", "Dữ liệu gửi AI vượt giới hạn 250 KB của PoC.")
        return Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.modelName}:generateContent",
            data=body,
            headers={"Content-Type": "application/json", "x-goog-api-key": self.apiKey},
            method="POST",
        )

    def interpret(self, inputs: EvaluationInput) -> Interpretation:
        request = self.buildRequest(inputs)
        try:
            with urlopen(request, timeout=self.timeoutSeconds) as response:
                rawBody = response.read(1000001)
            if len(rawBody) > 1000000:
                raise EvaluationError("providerOutput", "Phản hồi AI vượt giới hạn 1 MB.")
            return self.parseResponse(rawBody)
        except HTTPError as error:
            error.close()
            if error.code == 429:
                raise EvaluationError("providerQuota", "Dịch vụ AI giới hạn lượt gọi; chưa tạo kết quả chấm.", True) from error
            retryable = error.code >= 500 or error.code == 408
            raise EvaluationError("providerHttp", f"Dịch vụ AI trả HTTP {error.code}; kiểm tra model/cấu hình hoặc thử lại.", retryable) from error
        except (TimeoutError, socket.timeout) as error:
            raise EvaluationError("providerTimeout", "Dịch vụ AI quá thời gian; câu trả lời gốc được giữ nguyên.", True) from error
        except URLError as error:
            raise EvaluationError("providerNetwork", "Không kết nối được dịch vụ AI; chưa tạo điểm.", True) from error
        except OSError as error:
            raise EvaluationError("providerNetwork", "Kết nối dịch vụ AI bị gián đoạn; chưa tạo điểm.", True) from error

    def parseResponse(self, rawBody: bytes) -> Interpretation:
        try:
            response = json.loads(rawBody)
            if response.get("promptFeedback", {}).get("blockReason"):
                raise EvaluationError("providerRefusal", "Dịch vụ AI từ chối xử lý; đây không phải kết quả học tập.")
            candidates = response.get("candidates", [])
            if len(candidates) != 1 or candidates[0].get("finishReason") != "STOP":
                raise EvaluationError("providerIncomplete", "Dịch vụ AI chưa trả một kết quả hoàn chỉnh; chưa tạo điểm.")
            parts = candidates[0]["content"]["parts"]
            content = "".join(part["text"] for part in parts if "text" in part and not part.get("thought", False))
            return Interpretation.model_validate_json(content)
        except (ValueError, KeyError, TypeError, AttributeError, ValidationError) as error:
            raise EvaluationError("providerOutput", "JSON từ AI sai cấu trúc; chưa tạo kết quả chấm.") from error
