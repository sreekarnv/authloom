from email.message import EmailMessage
from pathlib import Path
from smtplib import SMTP
from typing import Annotated

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi_csrf_protect import CsrfProtect
from fastapi_csrf_protect.exceptions import CsrfProtectError
from pydantic import ValidationError
from pydantic_settings import BaseSettings

from app.config import settings
from app.database import AsyncSessionLocal
from authloom import AuthLoom, create_auth_router
from authloom.db import User
from authloom.dtos import (
    ChangePasswordReqDto,
    PasswordResetHttpReqDto,
    SigninHttpReqDto,
    SigninSrvInputDto,
    SignupHttpReqDto,
    SignupSrvInputDto,
)
from authloom.exceptions import (
    InvalidCredentialsException,
    InvalidEmailVerificationTokenException,
    InvalidPasswordResetTokenException,
    PasswordPolicyException,
    UserAlreadyExistsException,
)
from authloom.settings import (
    AuthLoomConfig,
    AuthLoomCookieSessionConfig,
    AuthLoomHooks,
)


class CsrfSettings(BaseSettings):
    secret_key: str
    cookie_samesite: str = "lax"
    token_location: str = "body"  # noqa: S105
    token_key: str = "csrf_token"  # noqa: S105


@CsrfProtect.load_config
def get_csrf_config() -> CsrfSettings:
    return CsrfSettings(secret_key=settings.csrf_secret_key)


csrf_protect_dependency = Depends()


async def verify_csrf(
    request: Request,
    csrf_protect: CsrfProtect = csrf_protect_dependency,
) -> None:
    await csrf_protect.validate_csrf(request)


csrf_dependency = Depends(verify_csrf)
app = FastAPI()
templates = Jinja2Templates(directory=Path(__file__).resolve().parents[1] / "templates")


def send_email(*, recipient: str, subject: str, body: str) -> None:
    message = EmailMessage()
    message["From"] = settings.email_from
    message["To"] = recipient
    message["Subject"] = subject
    message.set_content(body)

    with SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        smtp.send_message(message)


def send_password_reset_email(email: str, token: str) -> None:
    link = f"{settings.app_base_url}/reset-password?token={token}"
    send_email(
        recipient=email,
        subject="Reset your AuthLoom password",
        body=(
            "Use the following link to reset your password:\n\n"
            f"{link}\n\n"
            "This link expires in 15 minutes."
        ),
    )


def send_email_verification_email(email: str, token: str) -> None:
    link = f"{settings.app_base_url}/auth/email-verification?token={token}"
    send_email(
        recipient=email,
        subject="Verify your AuthLoom email address",
        body=(
            "Use the following link to verify your email address:\n\n"
            f"{link}\n\n"
            "This link expires in 15 minutes."
        ),
    )


auth = AuthLoom(
    config=AuthLoomConfig(
        session_factory=AsyncSessionLocal,
        cookie_session=AuthLoomCookieSessionConfig(
            cookie_name="authloom.auth",
            http_only=True,
            samesite="lax",
            secure=False,
        ),
        hooks=AuthLoomHooks(
            on_request_password_reset=send_password_reset_email,
            on_request_email_verification=send_email_verification_email,
        ),
    )
)

app.include_router(
    create_auth_router(
        auth,
        unsafe_route_dependencies=(csrf_dependency,),
    )
)


@app.exception_handler(CsrfProtectError)
async def csrf_exception_handler(request: Request, exc: CsrfProtectError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )


@app.get("/csrf")
def get_csrf_token(csrf_protect: CsrfProtect = csrf_protect_dependency):
    csrf_token, signed_token = csrf_protect.generate_csrf_tokens()
    response = JSONResponse({"csrf_token": csrf_token})
    csrf_protect.set_csrf_cookie(signed_token, response)
    return response


@app.get("/me")
async def get_me(user: Annotated[User, Depends(auth.require_current_user)]):
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "email_verified_at": user.email_verified_at,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }


@app.get("/optional-auth")
async def optional_auth(
    user: Annotated[User | None, Depends(auth.optional_current_user)],
):
    if user is None:
        return {"authenticated": False, "user": None}

    return {
        "authenticated": True,
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "email_verified_at": user.email_verified_at,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        },
    }


@app.post("/example-mutation", dependencies=[csrf_dependency])
async def example_mutation():
    return {"status": "changed"}


def render_page(
    request: Request,
    template_name: str,
    csrf_protect: CsrfProtect,
    *,
    status_code: int = 200,
    **context,
) -> HTMLResponse:
    csrf_token, signed_token = csrf_protect.generate_csrf_tokens()
    response = templates.TemplateResponse(
        request=request,
        name=template_name,
        context={"csrf_token": csrf_token, "user": None, **context},
        status_code=status_code,
    )
    csrf_protect.set_csrf_cookie(signed_token, response)
    return response


def set_session_cookie(response: RedirectResponse, session) -> None:
    response.set_cookie(
        key=auth.config.cookie_session.cookie_name,
        value=session.token_raw,
        httponly=auth.config.cookie_session.http_only,
        expires=session.expires_at,
        domain=auth.config.cookie_session.domain,
        path=auth.config.cookie_session.path,
        samesite=auth.config.cookie_session.samesite,
        secure=auth.config.cookie_session.secure,
    )


@app.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    user: Annotated[User | None, Depends(auth.optional_current_user)],
):
    return RedirectResponse("/account" if user else "/signin", status_code=303)


@app.get("/signup", response_class=HTMLResponse)
async def signup_page(
    request: Request,
    csrf_protect: CsrfProtect = csrf_protect_dependency,
):
    return render_page(request, "auth/signup.jinja2", csrf_protect, form={})


@app.post("/signup", response_class=HTMLResponse, dependencies=[csrf_dependency])
async def signup_form(
    request: Request,
    name: str = Form(),
    email: str = Form(),
    password: str = Form(),
    password_confirm: str = Form(),
    csrf_protect: CsrfProtect = csrf_protect_dependency,
):
    form = {"name": name, "email": email}
    try:
        input_dto = SignupHttpReqDto(
            name=name,
            email=email,
            password=password,
            password_confirm=password_confirm,
        )
        user, session = await auth.signup(
            input=SignupSrvInputDto(**input_dto.model_dump())
        )
    except ValidationError as exc:
        return render_page(
            request,
            "auth/signup.jinja2",
            csrf_protect,
            status_code=422,
            form=form,
            error=exc.errors()[0]["msg"],
        )
    except PasswordPolicyException as exc:
        return render_page(
            request,
            "auth/signup.jinja2",
            csrf_protect,
            status_code=422,
            form=form,
            error=exc.message,
        )
    except UserAlreadyExistsException:
        return render_page(
            request,
            "auth/signup.jinja2",
            csrf_protect,
            status_code=409,
            form=form,
            error="An account with that email already exists.",
        )

    token = await auth.request_email_verification(email=user.email)
    if token is not None:
        send_email_verification_email(user.email, token)

    response = RedirectResponse("/account", status_code=303)
    set_session_cookie(response, session)
    return response


@app.get("/signin", response_class=HTMLResponse)
async def signin_page(
    request: Request,
    csrf_protect: CsrfProtect = csrf_protect_dependency,
):
    return render_page(request, "auth/signin.jinja2", csrf_protect, form={})


@app.post("/signin", response_class=HTMLResponse, dependencies=[csrf_dependency])
async def signin_form(
    request: Request,
    email: str = Form(),
    password: str = Form(),
    csrf_protect: CsrfProtect = csrf_protect_dependency,
):
    form = {"email": email}
    try:
        input_dto = SigninHttpReqDto(email=email, password=password)
        user, session = await auth.signin(
            input=SigninSrvInputDto(**input_dto.model_dump())
        )
    except (ValidationError, InvalidCredentialsException):
        return render_page(
            request,
            "auth/signin.jinja2",
            csrf_protect,
            status_code=401,
            form=form,
            error="Invalid email or password.",
        )

    response = RedirectResponse("/account", status_code=303)
    set_session_cookie(response, session)
    return response


@app.post("/signout", dependencies=[csrf_dependency])
async def signout_form(request: Request):
    token = request.cookies.get(auth.config.cookie_session.cookie_name)
    if token:
        await auth.signout(token_raw=token)

    response = RedirectResponse("/signin", status_code=303)
    response.delete_cookie(
        key=auth.config.cookie_session.cookie_name,
        domain=auth.config.cookie_session.domain,
        path=auth.config.cookie_session.path,
        samesite=auth.config.cookie_session.samesite,
        secure=auth.config.cookie_session.secure,
    )
    return response


@app.get("/account", response_class=HTMLResponse)
async def account_page(
    request: Request,
    user: Annotated[User, Depends(auth.require_current_user)],
    csrf_protect: CsrfProtect = csrf_protect_dependency,
):
    return render_page(request, "account.jinja2", csrf_protect, user=user)


@app.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(
    request: Request,
    csrf_protect: CsrfProtect = csrf_protect_dependency,
):
    return render_page(request, "auth/forgot_password.jinja2", csrf_protect, form={})


@app.post(
    "/forgot-password",
    response_class=HTMLResponse,
    dependencies=[csrf_dependency],
)
async def forgot_password_form(
    request: Request,
    email: str = Form(),
    csrf_protect: CsrfProtect = csrf_protect_dependency,
):
    token = await auth.request_password_reset(email=email)
    if token is not None:
        send_password_reset_email(email, token)

    return render_page(
        request,
        "check_email.jinja2",
        csrf_protect,
        message=(
            "If an account exists for that email, a password-reset link has been "
            "created."
        ),
    )


@app.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(
    request: Request,
    token: str = "",
    csrf_protect: CsrfProtect = csrf_protect_dependency,
):
    if not token:
        return render_page(
            request,
            "verify_email.jinja2",
            csrf_protect,
            status_code=400,
            message="The password-reset link is invalid.",
        )
    return render_page(
        request,
        "auth/reset_password.jinja2",
        csrf_protect,
        token=token,
    )


@app.post(
    "/reset-password",
    response_class=HTMLResponse,
    dependencies=[csrf_dependency],
)
async def reset_password_form(
    request: Request,
    token: str = Form(),
    password: str = Form(),
    password_confirm: str = Form(),
    csrf_protect: CsrfProtect = csrf_protect_dependency,
):
    try:
        input_dto = PasswordResetHttpReqDto(
            password=password,
            password_confirm=password_confirm,
        )
        await auth.verify_token_reset_password(
            token_raw=token,
            new_password=input_dto.password,
        )
    except InvalidPasswordResetTokenException:
        return render_page(
            request,
            "auth/reset_password.jinja2",
            csrf_protect,
            status_code=400,
            token=token,
            error="The password-reset link is invalid or expired.",
        )
    except (ValidationError, PasswordPolicyException) as exc:
        error = (
            exc.message
            if isinstance(exc, PasswordPolicyException)
            else exc.errors()[0]["msg"]
        )
        return render_page(
            request,
            "auth/reset_password.jinja2",
            csrf_protect,
            status_code=422,
            token=token,
            error=error,
        )

    return RedirectResponse("/signin", status_code=303)


@app.get("/account/password", response_class=HTMLResponse)
async def change_password_page(
    request: Request,
    user: Annotated[User, Depends(auth.require_current_user)],
    csrf_protect: CsrfProtect = csrf_protect_dependency,
):
    return render_page(request, "auth/change_password.jinja2", csrf_protect, user=user)


@app.post(
    "/account/password",
    response_class=HTMLResponse,
    dependencies=[csrf_dependency],
)
async def change_password_form(
    request: Request,
    user: Annotated[User, Depends(auth.require_current_user)],
    current_password: str = Form(),
    new_password: str = Form(),
    new_password_confirm: str = Form(),
    csrf_protect: CsrfProtect = csrf_protect_dependency,
):
    try:
        input_dto = ChangePasswordReqDto(
            current_password=current_password,
            new_password=new_password,
            new_password_confirm=new_password_confirm,
        )
        await auth.change_password(
            user_id=user.id,
            current_password=input_dto.current_password,
            new_password=input_dto.new_password,
            preserve_session_token_raw=request.cookies.get(
                auth.config.cookie_session.cookie_name
            ),
        )
    except InvalidCredentialsException:
        return render_page(
            request,
            "auth/change_password.jinja2",
            csrf_protect,
            status_code=401,
            user=user,
            error="The current password is incorrect.",
        )
    except (ValidationError, PasswordPolicyException) as exc:
        error = (
            exc.message
            if isinstance(exc, PasswordPolicyException)
            else exc.errors()[0]["msg"]
        )
        return render_page(
            request,
            "auth/change_password.jinja2",
            csrf_protect,
            status_code=422,
            user=user,
            error=error,
        )

    return RedirectResponse("/account", status_code=303)


@app.post(
    "/account/email-verification",
    response_class=HTMLResponse,
    dependencies=[csrf_dependency],
)
async def request_email_verification_form(
    user: Annotated[User, Depends(auth.require_current_user)],
):
    token = await auth.request_email_verification(email=user.email)
    if token is not None:
        send_email_verification_email(user.email, token)
    return RedirectResponse("/account", status_code=303)


@app.get("/verify-email", response_class=HTMLResponse)
async def verify_email(request: Request, token: str = ""):
    if not token:
        return templates.TemplateResponse(
            request=request,
            name="verify_email.jinja2",
            context={"user": None, "message": "The verification link is invalid."},
            status_code=400,
        )

    try:
        await auth.verify_email(token_raw=token)
    except InvalidEmailVerificationTokenException:
        return templates.TemplateResponse(
            request=request,
            name="verify_email.jinja2",
            context={
                "user": None,
                "message": "The verification link is invalid or expired.",
            },
            status_code=400,
        )

    return templates.TemplateResponse(
        request=request,
        name="verify_email.jinja2",
        context={"user": None, "message": "Your email has been verified."},
    )
