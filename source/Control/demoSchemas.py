from typing import Annotated

from pydantic import Field, StrictInt

from source.Model.answerData import FrozenData


class DemoRequest(FrozenData):
    questionId: Annotated[str, Field(min_length=1, max_length=120)]
    questionVersion: Annotated[StrictInt, Field(ge=1)]
    rubricVersions: dict[str, Annotated[StrictInt, Field(ge=1)]]
    answerText: Annotated[str, Field(min_length=1, max_length=40000)]


class LiveRequest(DemoRequest):
    answerId: Annotated[str, Field(pattern=r"^answer\.[a-zA-Z0-9.-]{1,100}$")] | None = None
    revision: Annotated[StrictInt, Field(ge=1)] = 1


class PreviewRequest(DemoRequest):
    caseName: Annotated[str, Field(min_length=1, max_length=40)]
