from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class AuthApiTests(APITestCase):
    def test_register_creates_user_and_returns_tokens(self):
        response = self.client.post(
            '/api/v1/auth/register',
            {
                'email': 'user@example.com',
                'password': 'strongpass123',
                'password_confirm': 'strongpass123',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['user']['email'], 'user@example.com')
        self.assertIn('created_at', response.data['user'])
        self.assertIn('access_token', response.data)
        self.assertIn('refresh_token', response.data)
        self.assertTrue(User.objects.filter(email='user@example.com').exists())

    def test_register_duplicate_email_returns_conflict(self):
        User.objects.create_user(email='user@example.com', password='strongpass123')

        response = self.client.post(
            '/api/v1/auth/register',
            {
                'email': 'USER@example.com',
                'password': 'strongpass123',
                'password_confirm': 'strongpass123',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data['error'], 'EMAIL_TAKEN')

    def test_login_returns_tokens(self):
        user = User.objects.create_user(email='user@example.com', password='strongpass123')

        response = self.client.post(
            '/api/v1/auth/login',
            {'email': 'user@example.com', 'password': 'strongpass123'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['user'], {'id': user.id, 'email': 'user@example.com'})
        self.assertIn('access_token', response.data)
        self.assertIn('refresh_token', response.data)

    def test_login_invalid_credentials_returns_unauthorized(self):
        User.objects.create_user(email='user@example.com', password='strongpass123')

        response = self.client.post(
            '/api/v1/auth/login',
            {'email': 'user@example.com', 'password': 'wrongpass123'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data['error'], 'INVALID_CREDENTIALS')

    def test_refresh_returns_new_access_token(self):
        user = User.objects.create_user(email='user@example.com', password='strongpass123')
        refresh = RefreshToken.for_user(user)

        response = self.client.post(
            '/api/v1/auth/refresh',
            {'refresh_token': str(refresh)},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.data)
        self.assertNotIn('refresh_token', response.data)

    def test_logout_blacklists_refresh_token(self):
        user = User.objects.create_user(email='user@example.com', password='strongpass123')
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        response = self.client.post(
            '/api/v1/auth/logout',
            {'refresh_token': str(refresh)},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        refresh_response = self.client.post(
            '/api/v1/auth/refresh',
            {'refresh_token': str(refresh)},
            format='json',
        )

        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(refresh_response.data['error'], 'INVALID_REFRESH_TOKEN')
