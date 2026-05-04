from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import FileResponse

from backend.api.schemas import AuthUser, GenerateModelResponse, HealthResponse, LoginRequest, LoginResponse, ProjectHistoryItem, ProjectRequest
from backend.auth import authenticate_user, create_access_token, verify_access_token
from backend.services.calculation_service import generate_project
from backend.services.project_storage import find_excel_file, get_project_result, list_projects


router = APIRouter(prefix="/api", tags=["api"])


@router.get("/health", response_model=HealthResponse)
def api_health() -> HealthResponse:
    return HealthResponse()


def get_current_user(authorization: str | None = Header(default=None)) -> dict[str, str]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Требуется авторизация.")
    token = authorization.split(" ", 1)[1].strip()
    user = verify_access_token(token)
    if user is None:
        raise HTTPException(status_code=401, detail="Сессия недействительна или истекла. Войдите снова.")
    return user


@router.post("/auth/login", response_model=LoginResponse)
def api_login(credentials: LoginRequest) -> LoginResponse:
    user = authenticate_user(credentials.login, credentials.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Неверный логин или пароль.")
    return LoginResponse(
        access_token=create_access_token(user),
        user=AuthUser(**user),
    )


@router.get("/auth/me", response_model=AuthUser)
def api_me(current_user: dict[str, str] = Depends(get_current_user)) -> AuthUser:
    return AuthUser(**current_user)


@router.post("/generate-model", response_model=GenerateModelResponse)
def api_generate_model(project_input: ProjectRequest, current_user: dict[str, str] = Depends(get_current_user)) -> dict:
    try:
        return generate_project(project_input, username=current_user["login"])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Не удалось выполнить расчёт проекта. Проверьте вводные данные и попробуйте ещё раз.") from exc


@router.get("/projects", response_model=list[ProjectHistoryItem])
def api_projects(current_user: dict[str, str] = Depends(get_current_user)) -> list[dict]:
    return list_projects()


@router.get("/projects/{project_id}")
def api_project(project_id: str, current_user: dict[str, str] = Depends(get_current_user)) -> dict:
    try:
        result = get_project_result(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Проект не найден.")
    return result


@router.get("/download/{filename}")
def api_download(filename: str, current_user: dict[str, str] = Depends(get_current_user)) -> FileResponse:
    path = find_excel_file(filename)
    if path is None:
        raise HTTPException(status_code=404, detail="Excel-файл не найден.")
    return FileResponse(
        path,
        filename=path.name,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
