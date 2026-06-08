from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import FileResponse

from backend.api.schemas import AiChatRequest, AuthUser, GenerateModelResponse, HealthResponse, LoginRequest, LoginResponse, ProjectHistoryItem, ProjectRequest, RegisterRequest
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
from backend.services.project_storage import find_excel_file, get_excel_bytes, get_project_result, list_projects


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
    from backend.auth import is_user_blocked

    if is_user_blocked(user["login"]):
        raise HTTPException(status_code=403, detail="Аккаунт заблокирован.")
    return user


@router.post("/auth/login", response_model=LoginResponse)
def api_login(credentials: LoginRequest) -> LoginResponse:
    user = authenticate_user(credentials.login, credentials.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Неверный логин или пароль.")
    from backend.services import email_service
    from backend.auth import is_email_verified

    if email_service.email_enabled() and not is_email_verified(user["login"]):
        raise HTTPException(status_code=403, detail="Подтвердите email по ссылке из письма, затем войдите. Если письма нет — запросите отправку повторно.")
    return LoginResponse(
        access_token=create_access_token(user),
        user=AuthUser(**user),
    )


@router.post("/auth/register")
def api_register(credentials: RegisterRequest, request: Request) -> dict:
    import os

    if os.getenv("ALLOW_SELF_REGISTRATION", "true").strip().lower() not in {"1", "true", "yes", "on"}:
        raise HTTPException(status_code=403, detail="Самостоятельная регистрация временно отключена.")
    forwarded = request.headers.get("x-forwarded-for")
    client_ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
    allowed, _remaining = check_rate_limit(f"register:{client_ip}", "register")
    if not allowed:
        raise HTTPException(status_code=429, detail="Слишком много регистраций с вашего адреса. Попробуйте позже.")

    from backend.services import email_service
    from backend.services.user_admin import create_user
    from backend.auth import create_email_token

    verify = email_service.email_enabled()
    email = (credentials.email or "").strip()
    if verify and "@" not in email:
        raise HTTPException(status_code=400, detail="Укажите корректный email — на него придёт письмо подтверждения.")

    try:
        create_user(
            login=credentials.login,
            password=credentials.password,
            role="user",
            email=email or None,
            email_verified=not verify,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if verify:
        try:
            email_service.send_verification_email(email, create_email_token(credentials.login))
        except Exception as exc:  # noqa: BLE001
            import traceback

            print("SMTP_DEBUG:", type(exc).__name__, repr(exc), flush=True)
            traceback.print_exc()
            from backend.services.user_admin import delete_user

            try:
                delete_user(credentials.login)
            except Exception:  # noqa: BLE001
                pass
            raise HTTPException(status_code=502, detail="Не удалось отправить письмо подтверждения. Попробуйте позже.") from exc
        return {"status": "verification_sent", "email": email}

    user = authenticate_user(credentials.login, credentials.password)
    if user is None:
        raise HTTPException(status_code=500, detail="Не удалось войти после регистрации.")
    return {"status": "verified", "access_token": create_access_token(user), "token_type": "bearer", "user": user}


@router.get("/auth/verify")
def api_verify_email(token: str):
    import os

    from fastapi.responses import RedirectResponse

    from backend.auth import verify_email_token

    base = os.getenv("APP_BASE_URL", "https://construction-budget-agent-v3.onrender.com").rstrip("/")
    login = verify_email_token(token)
    if login is None:
        return RedirectResponse(url=f"{base}/?verify=invalid", status_code=303)
    from backend.services.user_admin import mark_email_verified

    mark_email_verified(login)
    return RedirectResponse(url=f"{base}/?verified=1", status_code=303)


@router.post("/auth/resend-verification")
def api_resend_verification(body: dict, request: Request) -> dict:
    from backend.services import email_service

    if not email_service.email_enabled():
        raise HTTPException(status_code=400, detail="Подтверждение email сейчас не используется.")
    forwarded = request.headers.get("x-forwarded-for")
    client_ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
    allowed, _remaining = check_rate_limit(f"resend:{client_ip}", "register")
    if not allowed:
        raise HTTPException(status_code=429, detail="Слишком часто. Попробуйте позже.")

    from backend.auth import create_email_token, load_users

    login = str(body.get("login") or "").strip().lower()
    target = None
    for user in load_users():
        if str(user.get("login") or "").strip().lower() == login:
            target = user
            break
    if target and not bool(target.get("email_verified", True)) and target.get("email"):
        try:
            email_service.send_verification_email(str(target["email"]), create_email_token(str(target["login"])))
        except Exception:  # noqa: BLE001
            pass
    return {"status": "ok"}


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


@router.get("/admin/users")
def api_admin_list_users(current_user: dict[str, str] = Depends(get_current_user)) -> list[dict]:
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Требуется роль admin.")
    from backend.services.user_admin import list_all_users

    return list_all_users()


@router.post("/admin/users")
def api_admin_create_user(body: dict, current_user: dict[str, str] = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Требуется роль admin.")
    from backend.services.user_admin import create_user

    plan = body.get("plan")
    try:
        return create_user(
            login=str(body.get("login") or ""),
            password=str(body.get("password") or ""),
            role=str(body.get("role") or "user"),
            plan=str(plan) if plan else None,
            months=int(body.get("months") or 1),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/admin/users/{login}/block")
def api_admin_block_user(login: str, body: dict, current_user: dict[str, str] = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Требуется роль admin.")
    from backend.services.user_admin import set_blocked

    try:
        return set_blocked(login, bool(body.get("blocked")))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/admin/users/{login}")
def api_admin_delete_user(login: str, current_user: dict[str, str] = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Требуется роль admin.")
    from backend.services.user_admin import delete_user

    try:
        return delete_user(login)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/download/{filename}")
def api_download(filename: str, current_user: dict[str, str] = Depends(get_current_user)):
    from fastapi.responses import Response
    from backend.services.billing_service import export_allowed

    if not export_allowed(current_user["login"]):
        raise HTTPException(status_code=402, detail="Excel-выгрузка доступна на платном тарифе. Оформите тариф в разделе «Тариф».")
    content = get_excel_bytes(filename)
    if content is None:
        raise HTTPException(status_code=404, detail="Excel-файл не найден.")
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
