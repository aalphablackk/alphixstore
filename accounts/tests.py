from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Role, UserProfile


User = get_user_model()


class AccountsModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPassword123!",
        )


    def test_user_creation(self):
        self.assertEqual(
            self.user.username,
            "testuser",
        )

        self.assertEqual(
            self.user.email,
            "test@example.com",
        )

        self.assertTrue(
            self.user.check_password(
                "TestPassword123!"
            )
        )


    def test_user_profile_created_automatically(self):
        profile = UserProfile.objects.get(
            user=self.user
        )

        self.assertEqual(
            profile.user,
            self.user
        )


    def test_customer_role_created_automatically(self):
        role = Role.objects.get(
            name="CUSTOMER"
        )

        self.assertTrue(
            self.user.profile.role.filter(
                pk=role.pk
            ).exists()
        )


    def test_user_profile_defaults(self):
        profile = self.user.profile

        self.assertEqual(
            profile.address,
            ""
        )

        self.assertEqual(
            profile.phone_number,
            ""
        )

        self.assertIsNone(
            profile.gender
        )


    def test_role_creation(self):
        role = Role.objects.create(
            name="VENDOR"
        )

        self.assertEqual(
            role.name,
            "VENDOR"
        )

        self.assertEqual(
            str(role),
            "VENDOR"
        )


    def test_user_profile_string(self):
        profile = self.user.profile

        self.assertEqual(
            str(profile),
            "testuser"
        )

from django.urls import reverse


class LoginTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="james",
            email="james@example.com",
            password="TestPassword123!",
        )

        self.login_url = reverse("login")


    def test_login_with_username(self):
        response = self.client.post(
            self.login_url,
            {
                "username": "james",
                "password": "TestPassword123!",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertTrue(
            response.wsgi_request.user.is_authenticated
        )


    def test_login_with_email(self):
        response = self.client.post(
            self.login_url,
            {
                "username": "james@example.com",
                "password": "TestPassword123!",
            },
        )

        self.assertEqual(
            response.status_code,
            302,
        )

        self.assertTrue(
            response.wsgi_request.user.is_authenticated
        )


    def test_login_with_wrong_password_fails(self):
        response = self.client.post(
            self.login_url,
            {
                "username": "james",
                "password": "WrongPassword123!",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertFalse(
            response.wsgi_request.user.is_authenticated
        )


    def test_login_with_unknown_identifier_fails(self):
        response = self.client.post(
            self.login_url,
            {
                "username": "doesnotexist@example.com",
                "password": "TestPassword123!",
            },
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertFalse(
            response.wsgi_request.user.is_authenticated
        )