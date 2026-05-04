from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.api.schemas import GenerateModelResponse, HealthResponse, ProjectHistoryItem, ProjectRequest
from backend.services.calculation_service import generate_project
from backend.services.project_storage import find_excel_file, get_project_result, list_projects


router = APIRouter(prefix="/api", tags=["api"])


@router.get("/health", response_model=HealthResponse)
def api_health() -> HealthResponse:
    return HealthResponse()


@router.post("/generate-model", response_model=GenerateModelResponse)
def api_generate_model(project_input: ProjectRequest) -> dict:
    try:
        return generate_project(project_input)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Не удалось выполнить расчёт проекта. Проверьте вводные данные и попробуйте ещё раз.") from exc


@router.get("/projects", response_model=list[ProjectHistoryItem])
def api_projects() -> list[dict]:
    return list_projects()


@router.get("/projects/{project_id}")
def api_project(project_id: str) -> dict:
    try:
        result = get_project_result(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Проект не найден.")
    return result


@router.get("/download/{filename}")
def api_download(filename: str) -> FileResponse:
    path = find_excel_file(filename)
    if path is None:
        raise HTTPException(status_code=404, detail="Excel-файл не найден.")
    return FileResponse(
        path,
        filename=path.name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
