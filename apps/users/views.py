from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (
    LoginSerializer,
    LoginUserResponseSerializer,
    UserRegistrationSerializer,
    UserResponseSerializer,
)

User = get_user_model()


def token_response(user, status_code=status.HTTP_200_OK, user_serializer_class=UserResponseSerializer):
    refresh = RefreshToken.for_user(user)

    return Response(
        {
            'user': user_serializer_class(user).data,
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
        },
        status=status_code,
    )


def validation_error_response(details):
    return Response(
        {
            'error': 'VALIDATION_ERROR',
            'message': 'Ошибка валидации данных.',
            'details': details,
        },
        status=status.HTTP_400_BAD_REQUEST,
    )


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = str(request.data.get('email', '')).strip().lower()
        if email and User.objects.filter(email=email).exists():
            return Response(
                {'error': 'EMAIL_TAKEN', 'message': 'Email уже используется'},
                status=status.HTTP_409_CONFLICT,
            )

        serializer = UserRegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        try:
            user = serializer.save()
        except IntegrityError:
            return Response(
                {'error': 'EMAIL_TAKEN', 'message': 'Email уже используется'},
                status=status.HTTP_409_CONFLICT,
            )

        return token_response(user, status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return validation_error_response(serializer.errors)

        user = authenticate(
            request=request,
            username=serializer.validated_data['email'].lower(),
            password=serializer.validated_data['password'],
        )

        if user is None:
            return Response(
                {'error': 'INVALID_CREDENTIALS', 'message': 'Неверный email или пароль'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        return token_response(user, user_serializer_class=LoginUserResponseSerializer)
