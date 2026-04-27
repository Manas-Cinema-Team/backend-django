from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated, PermissionDenied
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


def error_response(error: str, message: str, status_code: int, details: dict | None = None) -> Response:
    payload = {
        'error': error,
        'message': message,
    }

    if details is not None:
        payload['details'] = details

    return Response(payload, status=status_code)


def validation_error_response(details: dict) -> Response:
    return error_response(
        error='VALIDATION_ERROR',
        message='Ошибка валидации данных.',
        status_code=status.HTTP_400_BAD_REQUEST,
        details=details,
    )


def not_found_response(message: str) -> Response:
    return error_response(
        error='NOT_FOUND',
        message=message,
        status_code=status.HTTP_404_NOT_FOUND,
    )


def conflict_response(error: str, message: str, details: dict | None = None) -> Response:
    return error_response(
        error=error,
        message=message,
        status_code=status.HTTP_409_CONFLICT,
        details=details,
    )


def forbidden_response(message: str = 'Недостаточно прав для выполнения операции.') -> Response:
    return error_response(
        error='FORBIDDEN',
        message=message,
        status_code=status.HTTP_403_FORBIDDEN,
    )


def unauthorized_response(message: str = 'Требуется авторизация.') -> Response:
    return error_response(
        error='UNAUTHORIZED',
        message=message,
        status_code=status.HTTP_401_UNAUTHORIZED,
    )


def custom_exception_handler(exc, context):
    if isinstance(exc, (NotAuthenticated, AuthenticationFailed)):
        return unauthorized_response()

    if isinstance(exc, PermissionDenied):
        return forbidden_response()

    return drf_exception_handler(exc, context)
