from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api import error_response, validation_error_response

from .serializers import BookingConfirmSerializer, BookingCreateSerializer, BookingResponseSerializer
from .services import BookingWorkflowError, cancel_booking, confirm_booking, create_booking_hold, get_booking_for_user


def booking_workflow_error_response(exc: BookingWorkflowError) -> Response:
    return error_response(
        error=exc.error,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
    )


def serialize_booking_response(booking, *, status_code=status.HTTP_200_OK) -> Response:
    serializer = BookingResponseSerializer(
        booking,
        context={'server_time': timezone.now()},
    )
    return Response(serializer.data, status=status_code)


class BookingCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = BookingCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        try:
            booking = create_booking_hold(
                user=request.user,
                session_id=serializer.validated_data['session_id'],
                seats=serializer.validated_data['seats'],
            )
        except BookingWorkflowError as exc:
            return booking_workflow_error_response(exc)

        return serialize_booking_response(booking, status_code=status.HTTP_201_CREATED)


class BookingDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk: int):
        try:
            booking = get_booking_for_user(pk, request.user)
        except BookingWorkflowError as exc:
            return booking_workflow_error_response(exc)

        return serialize_booking_response(booking)

    def delete(self, request, pk: int):
        try:
            cancel_booking(booking_id=pk, user=request.user)
        except BookingWorkflowError as exc:
            return booking_workflow_error_response(exc)

        return Response({'message': 'Cancelled'}, status=status.HTTP_200_OK)


class BookingConfirmView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk: int):
        serializer = BookingConfirmSerializer(data=request.data or {})
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        try:
            booking = confirm_booking(booking_id=pk, user=request.user)
        except BookingWorkflowError as exc:
            return booking_workflow_error_response(exc)

        return serialize_booking_response(booking, status_code=status.HTTP_200_OK)
