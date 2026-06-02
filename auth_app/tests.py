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