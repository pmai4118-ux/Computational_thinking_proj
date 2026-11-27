"""Present the Java self-study flow using the existing app template system."""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from source.view.pages import create_template_environment


def build_learning_pages_router(*, demo_mode_label: str | None = None) -> APIRouter:
    router = APIRouter(tags=["pages"])
    template = create_template_environment().get_template("learning_path.html")

    @router.get("/learning-path", response_class=HTMLResponse)
    def learning_path_page() -> HTMLResponse:
        return HTMLResponse(template.render(demo_mode_label=demo_mode_label))

    return router
