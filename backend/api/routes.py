from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import FileResponse

from backend.api.schemas import AiChatRequest, AuthUser, GenerateModelResponse, HealthResponse, LoginRequest, LoginResponse, ProjectHistoryItem, ProjectRequest
from backend.auth import authenticate_user, create_access_token, verify_access_token
from backend.api.rate_limit import check_rate_limit
from backend.services.billing_service import billing_overview, check_quota, record_usage, set_user_plan
from backend.services.payment_service import create_payment, handle_webhook, payment_status
from backend.services.calculation_service import generate_project
from backend.services.llm_service import (
    ai_status,
    chat_about_project,
    generate_ai_conclusion,
    load_ai_conclusion,
    save_ai_conclusion,
)
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
    allowed, _remaining = check_rate_limit(current_user["login"], "generate")
    if not allowed:
        raise HTTPException(status_code=429, detail="Превышен лимит расчётов в час. Попробуйте позже.")
    quota_ok, quota = check_quota(current_user["login"], "generate")
    if not quota_ok:
        raise HTTPException(
            status_code=402,
            detail=(
                f"Исчерпана месячная квота расчётов тарифа «{quota['plan']}» ({quota['quota']}). "
                "Оплатите или повысьте тариф в разделе «Тариф»."
            ),
        )
    try:
        result = generate_project(project_input, username=current_user["login"])
        record_usage(current_user["login"], "generate")
        return result
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


@router.get("/ai/status")
def api_ai_status(current_user: dict[str, str] = Depends(get_current_user)) -> dict:
    return ai_status()


@router.get("/projects/{project_id}/ai-conclusion")
def api_get_ai_conclusion(project_id: str, current_user: dict[str, str] = Depends(get_current_user)) -> dict:
    try:
        saved = load_ai_conclusion(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if saved is None:
        raise HTTPException(status_code=404, detail="ИИ-заключение ещё не сформировано.")
    return saved


@router.post("/projects/{project_id}/ai-conclusion")
def api_generate_ai_conclusion(project_id: str, current_user: dict[str, str] = Depends(get_current_user)) -> dict:
    try:
        result = get_project_result(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Проект не найден.")
    allowed, _remaining = check_rate_limit(current_user["login"], "ai")
    if not allowed:
        raise HTTPException(status_code=429, detail="Превышен лимит ИИ-заключений в час. Попробуйте позже.")
    quota_ok, quota = check_quota(current_user["login"], "ai")
    if not quota_ok:
        raise HTTPException(
            status_code=402,
            detail=(
                f"Исчерпана месячная квота ИИ-вызовов тарифа «{quota['plan']}» ({quota['quota']}). "
                "Оплатите или повысьте тариф в разделе «Тариф»."
            ),
        )
    conclusion = generate_ai_conclusion(result)
    if conclusion.get("status") == "ok":
        save_ai_conclusion(project_id, conclusion)
        record_usage(current_user["login"], "ai")
    return conclusion


@router.post("/projects/{project_id}/ai-chat")
def api_ai_chat(project_id: str, request: AiChatRequest, current_user: dict[str, str] = Depends(get_current_user)) -> dict:
    try:
        result = get_project_result(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Проект не найден.")
    allowed, _remaining = check_rate_limit(current_user["login"], "ai")
    if not allowed:
        raise HTTPException(status_code=429, detail="Превышен лимит обращений к ИИ в час. Попробуйте позже.")
    quota_ok, quota = check_quota(current_user["login"], "ai")
    if not quota_ok:
        raise HTTPException(
            status_code=402,
            detail=(
                f"Исчерпана месячная квота ИИ-вызовов тарифа «{quota['plan']}» ({quota['quota']}). "
                "Оплатите или повысьте тариф в разделе «Тариф»."
            ),
        )
    answer = chat_about_project(
        result,
        request.question,
        [message.model_dump() for message in request.history],
    )
    if answer.get("status") == "ok":
        record_usage(current_user["login"], "ai")
    return answer


@router.get("/billing")
def api_billing(current_user: dict[str, str] = Depends(get_current_user)) -> dict:
    return {**billing_overview(current_user["login"]), "payment": payment_status()}


@router.post("/billing/create-payment")
def api_create_payment(body: dict, current_user: dict[str, str] = Depends(get_current_user)) -> dict:
    plan_code = str(body.get("plan") or "")
    return_url = body.get("return_url")
    result = create_payment(current_user["login"], plan_code, return_url)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error") or "Не удалось создать платёж.")
    return result


@router.post("/payments/yookassa-webhook")
def api_yookassa_webhook(event: dict) -> dict:
    # Без авторизации (вебхук провайдера); тело не считается доверенным —
    # платёж перепроверяется запросом к API ЮKassa внутри handle_webhook.
    return handle_webhook(event)


@router.post("/admin/users/{login}/plan")
def api_admin_set_plan(login: str, body: dict, current_user: dict[str, str] = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Требуется роль admin.")
    plan_code = str(body.get("plan") or "")
    months = int(body.get("months") or 1)
    try:
        return set_user_plan(login, plan_code, months)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
