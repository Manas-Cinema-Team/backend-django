from rest_framework import status
from rest_framework.response import Response


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
