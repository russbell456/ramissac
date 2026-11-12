from __future__ import annotations

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def _field_name(loc: tuple) -> str:
    parts = [str(part) for part in loc if part not in ("body", "query", "path")]
    return ".".join(parts) if parts else "entrada"


def _format_error(err: dict) -> str:
    field = _field_name(err.get("loc", ()))
    err_type = err.get("type", "")
    ctx = err.get("ctx", {})

    if err_type == "value_error":
        msg = str(err.get("msg", f"El campo '{field}' es inválido"))
        if field == "email" or "email" in msg.lower():
            return "El email debe tener un formato válido (incluir @)"
        return msg

    if err_type == "missing":
        return f"El campo '{field}' es obligatorio"

    if err_type == "string_too_short":
        min_len = ctx.get("min_length", "")
        return f"El campo '{field}' debe tener al menos {min_len} caracteres"

    if err_type == "string_too_long":
        max_len = ctx.get("max_length", "")
        return f"El campo '{field}' no puede superar {max_len} caracteres"

    if err_type == "string_pattern_mismatch":
        if field == "dni":
            return "El DNI debe tener exactamente 8 dígitos numéricos"
        return f"El campo '{field}' tiene un formato inválido"

    if err_type == "value_error.email":
        return "El email debe tener un formato válido (incluir @)"

    if err_type == "greater_than":
        return f"El campo '{field}' debe ser mayor que {ctx.get('gt', 0)}"

    if err_type == "int_parsing":
        return f"El campo '{field}' debe ser un número entero"

    return str(err.get("msg", f"El campo '{field}' es inválido"))


async def request_validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    messages = [_format_error(error) for error in exc.errors()]
    detail = messages[0] if len(messages) == 1 else messages

    return JSONResponse(
        status_code=400,
        content={"detail": detail},
    )
