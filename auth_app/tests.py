from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core import mail
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator

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
            password='HansImGlück1987&',
            is_active=False
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

    def test_activate_user_already_activated(self):
        """Verifies that re-activating an already active account returns 200 without erroring."""
        User = get_user_model()
        user = User.objects.create_user(
            email='test@test.com',
            password='HansImGlück1987&',
            is_active=True
        )
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        url = reverse('activate', kwargs={'uid': uid, 'token': token})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], "Account is already activated")

class LoginViewTest(APITestCase):
    """Tests for the user login endpoint (POST /api/login/)."""

    def test_login_user_successfully(self):
        """Verifies that a user can log in with valid credentials and receives auth cookies."""
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
        self.assertEqual(response.data['detail'], 'Login successfully')
        self.assertEqual(response.data['user']['username'], data['email'])
        self.assertIn('access_token', response.cookies)
        self.assertIn('refresh_token', response.cookies)
        self.assertTrue(response.cookies['access_token']['httponly'])
        self.assertTrue(response.cookies['refresh_token']['httponly'])

    def test_login_user_inactive(self):
        """Verifies that login fails with 401 when the user account is inactive."""
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
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_user_wrong_password(self):
        """Verifies that login fails with 401 when the password is incorrect."""
        User = get_user_model()
        user = User.objects.create_user(
            email='test@test.com',
            password='HansImGlück1987&',
            is_active=True
        )
        url = reverse('login')
        data = {
            'email': 'test@test.com',
            'password': 'wrong-password'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_user_nonexistent_email(self):
        """Verifies that login fails with 401 when the email does not exist."""
        url = reverse('login')
        data = {
            'email': 'nonexistent@test.com',
            'password': 'HansImGlück1987&'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

class LogoutViewTest(APITestCase):
    """Tests for the user logout endpoint (POST /api/logout/)."""

    def _login(self):
        User = get_user_model()
        User.objects.create_user(
            email='test@test.com',
            password='HansImGlück1987&',
            is_active=True
        )
        data = {'email': 'test@test.com', 'password': 'HansImGlück1987&'}
        return self.client.post(reverse('login'), data, format='json')

    def test_logout_user_successfully(self):
        """Verifies that logout clears both auth cookies."""
        self._login()
        response = self.client.post(reverse('logout'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.cookies['access_token'].value, '')
        self.assertEqual(response.cookies['refresh_token'].value, '')

    def test_logout_invalidates_refresh_token(self):
        """Verifies that the blacklisted refresh token can no longer be used to refresh."""
        login_response = self._login()
        refresh_token = login_response.cookies['refresh_token'].value
        self.client.post(reverse('logout'))
        self.client.cookies['refresh_token'] = refresh_token
        response = self.client.post(reverse('token_refresh'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_without_authentication(self):
        """Verifies that logout requires an authenticated user."""
        response = self.client.post(reverse('logout'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_without_refresh_token_cookie(self):
        """Verifies that logout is rejected with 403 when the refresh_token cookie is missing."""
        self._login()
        del self.client.cookies['refresh_token']
        response = self.client.post(reverse('logout'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

class TokenRefreshViewTest(APITestCase):
    """Tests for the token refresh endpoint (POST /api/token/refresh/)."""

    def test_refresh_token_successfully(self):
        """Verifies that a new access token is issued from the refresh_token cookie."""
        User = get_user_model()
        User.objects.create_user(
            email='test@test.com',
            password='HansImGlück1987&',
            is_active=True
        )
        login_data = {'email': 'test@test.com', 'password': 'HansImGlück1987&'}
        login_response = self.client.post(reverse('login'), login_data, format='json')
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        refresh_token = login_response.cookies['refresh_token'].value

        response = self.client.post(reverse('token_refresh'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertNotEqual(response.data['access'], refresh_token)
        self.assertIn('access_token', response.cookies)

    def test_refresh_token_missing(self):
        """Verifies that refreshing without a refresh_token cookie returns 400."""
        response = self.client.post(reverse('token_refresh'))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_refresh_token_invalid(self):
        """Verifies that refreshing with an invalid refresh token returns 401."""
        self.client.cookies['refresh_token'] = 'not-a-valid-token'
        response = self.client.post(reverse('token_refresh'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

class PasswordResetViewTest(APITestCase):
    """Tests for the password reset request endpoint (POST /api/password_reset/)."""

    def test_password_reset_existing_email(self):
        """Verifies that a reset email is sent and a generic 200 response is returned."""
        User = get_user_model()
        User.objects.create_user(
            email='test@test.com',
            password='HansImGlück1987&',
            is_active=True
        )
        url = reverse('password_reset')
        response = self.client.post(url, {'email': 'test@test.com'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['test@test.com'])

    def test_password_reset_nonexistent_email_returns_generic_response(self):
        """Verifies that an unknown email gets the same 200 response as a known one, without sending mail."""
        url = reverse('password_reset')
        response = self.client.post(url, {'email': 'nonexistent@test.com'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)

class PasswordResetConfirmViewTest(APITestCase):
    """Tests for the password reset confirmation endpoint (POST /api/password_confirm/<uid>/<token>/)."""

    def _create_user(self):
        User = get_user_model()
        return User.objects.create_user(
            email='test@test.com',
            password='OldPassword1987&',
            is_active=True
        )

    def test_password_reset_confirm_successfully(self):
        """Verifies that a valid uid/token pair allows setting a new password."""
        user = self._create_user()
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        url = reverse('password_reset_confirm', kwargs={'uid': uid, 'token': token})
        data = {'new_password': 'NewPassword1987&', 'confirm_password': 'NewPassword1987&'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.check_password('NewPassword1987&'))

    def test_password_reset_confirm_invalid_token(self):
        """Verifies that an invalid token is rejected and the password stays unchanged."""
        user = self._create_user()
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        url = reverse('password_reset_confirm', kwargs={'uid': uid, 'token': 'invalid-token'})
        data = {'new_password': 'NewPassword1987&', 'confirm_password': 'NewPassword1987&'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        user.refresh_from_db()
        self.assertTrue(user.check_password('OldPassword1987&'))

    def test_password_reset_confirm_invalid_uid(self):
        """Verifies that an invalid uid is rejected with 400."""
        url = reverse('password_reset_confirm', kwargs={'uid': 'invalid-uid', 'token': 'irrelevant-token'})
        data = {'new_password': 'NewPassword1987&', 'confirm_password': 'NewPassword1987&'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_reset_confirm_password_mismatch(self):
        """Verifies that mismatched new_password/confirm_password fields are rejected."""
        user = self._create_user()
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        url = reverse('password_reset_confirm', kwargs={'uid': uid, 'token': token})
        data = {'new_password': 'NewPassword1987&', 'confirm_password': 'Different1987&'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        user.refresh_from_db()
        self.assertTrue(user.check_password('OldPassword1987&'))

    def test_password_reset_confirm_weak_password(self):
        """Verifies that a password failing strength validation is rejected."""
        user = self._create_user()
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        url = reverse('password_reset_confirm', kwargs={'uid': uid, 'token': token})
        data = {'new_password': 'weak', 'confirm_password': 'weak'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        user.refresh_from_db()
        self.assertTrue(user.check_password('OldPassword1987&'))
