"""Present the Java self-study flow using the existing app template system."""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from source.view.pages import create_template_environment


def build_learning_pages_router(*, demo_mode_label: str | None = None) -> APIRouter:
    router = APIRouter(tags=["pages"])
    env = create_template_environment()

    @router.get("/learning-path", response_class=HTMLResponse)
    def learning_path_page() -> HTMLResponse:
        template = env.get_template("learning_path.html")
        return HTMLResponse(template.render(demo_mode_label=demo_mode_label))

    return router
