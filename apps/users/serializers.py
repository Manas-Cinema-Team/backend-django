from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ('id', 'email', 'password', 'password_confirm', 'created_at')
        read_only_fields = ('id', 'created_at')

    def validate_email(self, value):
        return value.lower()

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password_confirm'):
            raise serializers.ValidationError({'password_confirm': ['Пароли не совпадают.']})

        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'created_at')
        read_only_fields = fields


class LoginUserResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email')
        read_only_fields = fields


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})


class RefreshTokenSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(write_only=True)
