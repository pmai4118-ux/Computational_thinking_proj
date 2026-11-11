import logging
import sqlite3
from pathlib import Path

from fastapi import FastAPI, Request, Query, Path as PathParameter
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from source.Control.demoController import DemoController
from source.Control.demoSchemas import LiveRequest, PreviewRequest


class DemoView:
    errorStatus = {"unknownQuestion": 404, "unknownExample": 404, "versionMismatch": 409, "answerConflict": 409, "exampleChanged": 409, "recordingMismatch": 409, "providerConfig": 503, "providerNetwork": 503, "providerTimeout": 504, "providerQuota": 429, "providerBilling": 402, "providerHttp": 502, "providerOutput": 502, "providerSchema": 502, "providerRefusal": 502, "providerIncomplete": 502, "invalidEvidence": 502, "contentUnapproved": 409, "questionBankInvalid": 503}

    def __init__(self, controller: DemoController, staticDirectory: Path):
        self.controller = controller
        self.staticDirectory = staticDirectory
        self.app = FastAPI(title="Answer evaluation PoC", docs_url=None, redoc_url=None)
        self.app.mount("/static", StaticFiles(directory=staticDirectory), name="static")
        self.app.add_api_route("/", self.home, methods=["GET"])
        self.app.add_api_route("/api/questions", controller.listQuestions, methods=["GET"])
        self.app.add_api_route("/api/question", controller.getQuestionDetails, methods=["GET"])
        self.app.add_api_route("/api/examples", controller.listExamples, methods=["GET"])
        self.app.add_api_route("/api/examples/{caseName}", controller.getExampleData, methods=["GET"])
        self.app.add_api_route("/api/status", controller.getStatus, methods=["GET"])
        self.app.add_api_route("/api/preview", self.preview, methods=["POST"])
        self.app.add_api_route("/api/evaluate", self.evaluate, methods=["POST"])
        self.app.add_api_route("/api/reports/{inputHash}", self.downloadReport, methods=["GET"])
        self.app.add_exception_handler(RequestValidationError, self.invalidRequest)
        self.app.add_exception_handler(Exception, self.handleError)
        self.app.middleware("http")(self.limitRequest)

    async def limitRequest(self, request: Request, callNext):
        if request.method == "POST":
            origin = request.headers.get("origin")
            if origin and origin != str(request.base_url).rstrip("/"):
                return JSONResponse({"code": "invalidOrigin", "detail": "Submit from this application page."}, status_code=403)
            body = await request.body()
            if len(body) > 250000:
                return JSONResponse({"code": "inputLimit", "detail": "The request is too large."}, status_code=413)
        try:
            response = await callNext(request)
        except Exception as error:
            response = await self.handleError(request, error)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'"
        return response

    def home(self) -> FileResponse:
        return FileResponse(self.staticDirectory / "index.html")

    def preview(self, request: PreviewRequest) -> dict:
        return self.controller.previewAnswer(request)

    def evaluate(self, request: LiveRequest) -> dict:
        return self.controller.evaluateAnswer(request)

    def downloadReport(self, inputHash: str = PathParameter(pattern="^[a-f0-9]{64}$"), providerName: str = Query(min_length=1, max_length=100), modelName: str = Query(min_length=1, max_length=500), promptVersion: str = Query(min_length=1, max_length=100)) -> JSONResponse:
        report = self.controller.getReport(inputHash, providerName, modelName, promptVersion)
        return JSONResponse(report, headers={"Content-Disposition": f'attachment; filename="evaluation-{inputHash[:12]}.json"'})

    async def invalidRequest(self, request: Request, error: RequestValidationError) -> JSONResponse:
        return JSONResponse({"code": "invalidInput", "detail": "Check the request fields, question version, rubric versions and answer length."}, status_code=422)

    async def handleError(self, request: Request, error: Exception) -> JSONResponse:
        code = getattr(error, "code", "internalError")
        if code in self.errorStatus or code in {"emptyAnswer", "inputLimit", "invalidRubric", "invalidLinks", "unknownReport", "reportConflict", "invalidReport"}:
            detail = getattr(error, "message", "Evaluation could not be completed.")
            statusCode = {"unknownReport": 404, "reportConflict": 409}.get(code, self.errorStatus.get(code, 422))
        elif isinstance(error, (OSError, sqlite3.Error)):
            code, detail, statusCode = "storageUnavailable", "Cannot access local evaluation storage. Check the configured data directory and retry.", 503
        else:
            code, detail, statusCode = "internalError", "Evaluation could not be completed. The answer remains in the editor.", 500
        logging.getLogger("evaluation").warning("Evaluation request failed: %s", code)
        return JSONResponse({"code": code, "detail": detail, "retryable": bool(getattr(error, "retryable", False))}, status_code=statusCode)
