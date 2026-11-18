from typing import Protocol

from source.Model.questionBankData import QuestionCatalog


class QuestionRepository(Protocol):
    def loadCatalog(self) -> QuestionCatalog: ...
