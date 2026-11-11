from pathlib import Path

from source.Model.questionBankData import QuestionCatalog


class JsonQuestionRepository:
    def __init__(self, catalogPath: Path):
        self.catalogPath = catalogPath

    def loadCatalog(self) -> QuestionCatalog:
        return QuestionCatalog.model_validate_json(self.catalogPath.read_bytes())
