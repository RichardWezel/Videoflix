from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core import mail

class RegisterViewTest(APITestCase):
    """Tests for the user registration endpoint (POST /api/register/)."""

    def test_register_user_successfully(self):
        """Verifies that a new user is created with valid data and account is inactive by default."""
        url = reverse('register')
        data = {
            'email': 'test@test.com',
            'password': 'HansImGlück1987&',
            'confirmed_password': 'HansImGlück1987&'
        }
        User = get_user_model()
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('user', response.data)
        self.assertIn('token', response.data)
        self.assertEqual(response.data['user']['email'], data['email'])
        self.assertTrue(User.objects.filter(email=data['email']).exists())
        user = User.objects.get(email=data['email'])
        self.assertFalse(user.is_active)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['test@test.com'])

    def test_register_missing_mail(self):
        """Verifies that registration fails with 400 when the email field is missing."""
        url = reverse('register')
        data = {
            'password': 'HansImGlück1987&',
            'confirmed_password': 'HansImGlück1987&'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_password_mismatch(self):
        """Verifies that registration fails when password and confirmed_password do not match."""
        url = reverse('register')
        data = {
            'email': 'test@test.de',
            'password': 'HansImGlück1987',
            'confirmed_password': 'HansImGlück1987&'
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)
        self.assertIn("Passwords do not match.", response.data['non_field_errors'])

    def test_register_weak_password(self):
        """Verifies that registration fails when the password does not meet strength requirements."""
        url = reverse('register')
        data = {
            'email': 'test@test.de',
            'password': 'weak',
            'confirmed_password': 'weak'
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)     

    def test_register_already_existing_email(self):
        """Verifies that registration fails with 400 when the email is already in use."""
        User = get_user_model()
        User.objects.create_user(
            email='test@test.de',
            password='HansImGlück1987&'
        )
        url = reverse('register')
        data = {
            'email': 'test@test.de',
            'password': 'HansImGlück1987&',
            'confirmed_password': 'HansImGlück1987&'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_wrong_email_format(self):
        """Verifies that registration fails with 400 when the email format is invalid."""
        url = reverse('register')
        data = {
            'email': 'invalid-email',
            'password': 'HansImGlück1987&',
            'confirmed_password': 'HansImGlück1987&'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

class ActivateViewTest(APITestCase):
    """Tests for the account activation endpoint (GET /api/activate/<uid>/<token>/)."""

    def test_activate_user_successfully(self):
        """Verifies that a user can be activated with a valid uid and token."""
        # Create a user and generate an activation token
        User = get_user_model()
        user = User.objects.create_user(
            email='test@test.com',
            password='HansImGlück1987&'
        )
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        url = reverse('activate', kwargs={'uid': uid, 'token': token})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.is_active)

    def test_activate_user_invalid_token(self):
        """Verifies that activation fails with 400 when the token is invalid."""
        User = get_user_model()
        user = User.objects.create_user(
            email='test@test.com',
            password='HansImGlück1987&'
        )
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = 'invalid-token'
        url = reverse('activate', kwargs={'uid': uid, 'token': token})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        user.refresh_from_db()
        self.assertFalse(user.is_active)

    def test_activate_user_invalid_uid(self):
        """Verifies that activation fails with 400 when the uid is invalid."""
        token = 'valid-token'
        url = reverse('activate', kwargs={'uid': 'invalid-uid', 'token': token})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

class LoginViewTest(APITestCase):
    """Tests for the user login endpoint (POST /api/login/)."""

    def test_login_user_successfully(self):
        """Verifies that a user can log in with valid credentials and receives a token."""
        User = get_user_model()
        User.objects.create_user(
            email='test@test.com',
            password='HansImGlück1987&',
            is_active=True
        )   
        url = reverse('login')
        data = {
            'email': 'test@test.com',
            'password': 'HansImGlück1987&'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertEqual(response.data['user']['email'], data['email'])
        self.assertIn('access_token', response.cookies)
        self.assertIn('refresh_token', response.cookies)
        self.assertTrue(response.cookies['access_token']['httponly'])

    def test_login_user_inactive(self):
        """Verifies that login fails with 400 when the user account is inactive."""
        User = get_user_model()
        user = User.objects.create_user(
            email='test@test.com',
            password='HansImGlück1987&',
            is_active=False
        )
        url = reverse('login')
        data = {
            'email': 'test@test.com',
            'password': 'HansImGlück1987&'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_user_wrong_password(self):
        """Verifies that login fails with 400 when the password is incorrect."""
        User = get_user_model()
        user = User.objects.create_user(    
            email='test@test.com',
            password='HansImGlück1987&'
        )
        url = reverse('login')
        data = {
            'email': 'test@test.com',
            'password': 'wrong-password'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_user_nonexistent_email(self):
        """Verifies that login fails with 400 when the email does not exist."""
        url = reverse('login')
        data = {
            'email': 'nonexistent@test.com',
            'password': 'HansImGlück1987&'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

class LogoutViewTest(APITestCase):
    """Tests for the user logout endpoint (POST /api/logout/)."""

    def test_logout_user_successfully(self):
        """Verifies that a user can log out successfully and the token is invalidated."""
        User = get_user_model()
        user = User.objects.create_user(
            email='test@test.com',
            password='HansImGlück1987&'
        )
        url = reverse('login')
        data = {
            'email': 'test@test.com',
            'password': 'HansImGlück1987&'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        token = response.data['token']

        url = reverse('logout')
        data = {
            'token': token
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)  
        # Verify that the token is invalidated (e.g., by trying to access a protected endpoint)
        protected_url = reverse('protected-endpoint')  # Replace with an actual protected endpoint
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + token)
        response = self.client.get(protected_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)    
    
class TokenRefreshViewTest(APITestCase):
    """Tests for the token refresh endpoint (POST /api/token/refresh/)."""

    def test_refresh_token_successfully(self):
        """Verifies that a new access token is issued with a valid refresh token."""
        User = get_user_model()
        user = User.objects.create_user(
            email='test@test.com',
            password='HansImGlück1987&'
        )
        url = reverse('login')
        data = {
            'email': 'test@test.com',
            'password': 'HansImGlück1987&'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        refresh_token = response.data['refresh']

        url = reverse('token_refresh')
        data = {
            'refresh': refresh_token
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertNotEqual(response.data['access'], refresh_token)
