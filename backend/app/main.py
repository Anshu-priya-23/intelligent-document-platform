import logging
import hashlib
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException
from backend.app.core.database import Base, engine
from backend.app.core.logging import configure_logging
from backend.app.api.routes.documents import router
from backend.app.utils.exceptions import AppError

configure_logging()
log = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]

@asynccontextmanager
async def lifespan(app):
    Base.metadata.create_all(engine)
    yield

app = FastAPI(title="Document Intelligence API", version="1.0.0", lifespan=lifespan)
app.include_router(router)
app.mount("/static", StaticFiles(directory=ROOT / "frontend/static"), name="static")
templates = Jinja2Templates(directory=ROOT / "frontend/templates")


def frontend_page(request, template):
    # Revisions get new asset URLs, even if a browser retained a prior stylesheet.
    versions = {name: hashlib.sha256((ROOT / "frontend/static" / name).read_bytes()).hexdigest()[:16]
                for name in ("css/app.css", "js/app.js")}
    return templates.TemplateResponse(request=request, name=template,
                                      context={"asset_versions": versions},
                                      headers={"Cache-Control": "no-cache"})

@app.get("/", include_in_schema=False)
def dashboard(request: Request):
    return frontend_page(request, "dashboard.html")

@app.get("/document", include_in_schema=False)
def detail(request: Request):
    return frontend_page(request, "document_result.html")

@app.exception_handler(AppError)
async def app_error(request: Request, exc: AppError):
    log.warning("request_failed code=%s", exc.code)
    return JSONResponse({"error": {"code": exc.code, "message": exc.message}}, status_code=exc.status)

@app.exception_handler(RequestValidationError)
async def invalid_request(request: Request, exc):
    return JSONResponse({"error": {"code": "INVALID_REQUEST", "message": "Supply a file and a supported document_type."}}, status_code=422)

@app.exception_handler(HTTPException)
async def http_error(request: Request, exc):
    return JSONResponse({"error": {"code": "HTTP_ERROR", "message": "The requested resource or method is unavailable."}}, status_code=exc.status_code)

@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, exc):
    log.error("database_failed exception_type=%s", type(exc).__name__)
    return JSONResponse({"error": {"code": "DATABASE_ERROR", "message": "Database unavailable; retry later."}}, status_code=503)

@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc):
    log.error("unexpected_failure exception_type=%s", type(exc).__name__)
    return JSONResponse({"error": {"code": "INTERNAL_ERROR", "message": "Processing failed unexpectedly."}}, status_code=500)
