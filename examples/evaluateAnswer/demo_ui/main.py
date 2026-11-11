from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from source.service.evaluationErrors import EvaluationError
from source.service.providers.interpreterFactory import InterpreterFactory
from source.service.providers.antigravityInterpreter import AntigravityInterpreter
from examples.evaluateAnswer.demo_ui.configuration import DEFAULT_MODEL, LOCAL_SETTINGS_PATH, loadDemoSettings, loadAntigravitySettings, selectedProvider
from examples.evaluateAnswer.demo_ui.controller import DEFAULT_QUESTION_ID, DemoController


STATIC_DIRECTORY = Path(__file__).resolve().parent / "static"
class ExampleRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    caseName: str = Field(min_length=1, max_length=40)


class PreviewRequest(ExampleRequest):
    answerText: str = Field(max_length=40000)
    questionId: str = Field(default=DEFAULT_QUESTION_ID, min_length=1, max_length=120)


class EvaluationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answerText: str = Field(min_length=1, max_length=40000)
    questionId: str = Field(default=DEFAULT_QUESTION_ID, min_length=1, max_length=120)


def create_app(controller: DemoController | None = None, settingsPath: Path = LOCAL_SETTINGS_PATH, providerName: str | None = None) -> FastAPI:
    providerName = providerName or (controller.providerName if controller is not None else selectedProvider())
    if providerName not in {"gemini", "antigravity"}:
        raise EvaluationError("providerConfig", "Unsupported demo provider.")
    # The dormant API-key settings are not even read while Antigravity is selected.
    settings = loadDemoSettings(settingsPath) if providerName == "gemini" else None
    antigravitySettings = loadAntigravitySettings() if providerName == "antigravity" else None
    demoController = controller or DemoController(interpreterFactory=InterpreterFactory(settings, antigravitySettings), providerName=providerName)
    app = FastAPI(title="Interview Practice PoC Demo", docs_url=None, redoc_url=None)
    app.mount("/static", StaticFiles(directory=STATIC_DIRECTORY), name="static")

    @app.get("/", include_in_schema=False)
    def home() -> FileResponse:
        return FileResponse(STATIC_DIRECTORY / "index.html")

    @app.get("/api/question")
    def question(questionId: str = DEFAULT_QUESTION_ID) -> dict:
        try:
            return demoController.getQuestionDetails(questionId)
        except EvaluationError as error:
            raise HTTPException(status_code=404, detail=error.message) from error

    @app.get("/api/questions")
    def questions() -> list[dict]:
        return demoController.listQuestions()

    @app.get("/api/examples")
    def examples(questionId: str = DEFAULT_QUESTION_ID) -> list[dict]:
        try:
            items = demoController.listExamples(questionId)
        except EvaluationError as error:
            raise HTTPException(status_code=404, detail=error.message) from error
        if questionId == DEFAULT_QUESTION_ID:
            return [{**item, "name": item["caseName"]} for item in items]
        return items

    @app.get("/api/status")
    def status() -> dict:
        return {
            "liveEvaluationConfigured": bool(AntigravityInterpreter(antigravitySettings).executablePath()) if antigravitySettings else settings is not None,
            "providerName": providerName,
            "modelName": antigravitySettings.modelName if antigravitySettings else settings.modelName if settings else DEFAULT_MODEL,
        }

    @app.get("/api/examples/{case_name}")
    def example(case_name: str, questionId: str = DEFAULT_QUESTION_ID) -> dict[str, str | bool]:
        try:
            sample = demoController.getExampleData(case_name, questionId)
        except EvaluationError as error:
            raise HTTPException(status_code=404, detail=error.message) from error
        # Keep the original recorded-preview request shape for the default case.
        if questionId == DEFAULT_QUESTION_ID:
            return {"caseName": sample["caseName"], "answerText": sample["answerText"]}
        return {"questionId": questionId, "caseName": sample["caseName"], "answerText": sample["answerText"]}

    @app.post("/api/preview")
    def preview(request: PreviewRequest) -> dict:
        try:
            report = demoController.evaluateRecordedExample(request.caseName, request.answerText, request.questionId)
        except EvaluationError as error:
            statusCode = 409 if error.code in {"exampleChanged", "recordingUnavailable"} else 404 if error.code in {"unknownExample", "unknownQuestion"} else 400
            raise HTTPException(status_code=statusCode, detail=error.message) from error
        return report.model_dump(mode="json")

    @app.post("/api/evaluate")
    def evaluate(request: EvaluationRequest) -> dict:
        try:
            report = demoController.evaluateAnswer(request.answerText, request.questionId)
        except EvaluationError as error:
            if error.code in {"unknownExample", "unknownQuestion"}:
                raise HTTPException(status_code=404, detail=error.message) from error
            if error.code == "invalidEvidence":
                raise HTTPException(
                    status_code=502,
                    detail="AI trả về đánh giá chưa khớp với rubric hoặc bằng chứng trong câu trả lời. Nội dung của bạn vẫn được giữ lại; hãy thử lại hoặc mở một kết quả ghi sẵn.",
                ) from error
            statusCode = {
                "providerBilling": 402,
                "providerQuota": 429,
                "providerConfig": 503,
                "providerNetwork": 503,
                "providerTimeout": 504,
                "providerHttp": 502,
                "providerOutput": 502,
                "providerSchema": 502,
                "providerRefusal": 502,
                "providerIncomplete": 502,
            }.get(error.code, 422)
            raise HTTPException(status_code=statusCode, detail=error.message) from error
        return report.model_dump(mode="json")

    return app


app = create_app()
