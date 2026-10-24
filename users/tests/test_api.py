from django.conf import settings
from django.contrib.auth import get_user
from django.test import Client, TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import NotificationReceipt, User


class AuthenticationConfigurationTests(TestCase):
    def setUp(self):
        self.password = "A-secure-test-password-482!"
        self.user = User.objects.create_user(
            email="owner@example.com",
            password=self.password,
        )

    def test_separate_browser_sessions_can_remain_authenticated(self):
        first_device = Client()
        second_device = Client()
        self.assertTrue(first_device.login(email=self.user.email, password=self.password))
        self.assertTrue(second_device.login(email=self.user.email, password=self.password))
        self.assertNotEqual(first_device.session.session_key, second_device.session.session_key)
        first_device.logout()
        self.assertFalse(get_user(first_device).is_authenticated)
        self.assertTrue(get_user(second_device).is_authenticated)

    def test_refresh_tokens_are_independent_per_device(self):
        first_token = RefreshToken.for_user(self.user)
        second_token = RefreshToken.for_user(self.user)
        first_token.blacklist()
        self.assertEqual(BlacklistedToken.objects.count(), 1)
        self.assertFalse(
            BlacklistedToken.objects.filter(token__jti=second_token["jti"]).exists()
        )

    def test_authentication_defaults_are_secure(self):
        classes = settings.REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"]
        self.assertIn("rest_framework.authentication.SessionAuthentication", classes)
        self.assertIn("rest_framework_simplejwt.authentication.JWTAuthentication", classes)
        self.assertTrue(settings.SESSION_COOKIE_HTTPONLY)
        self.assertTrue(settings.SIMPLE_JWT["ROTATE_REFRESH_TOKENS"])
        self.assertTrue(settings.SIMPLE_JWT["BLACKLIST_AFTER_ROTATION"])

    def test_i18n_configuration_declares_supported_languages(self):
        self.assertEqual(settings.LANGUAGE_CODE, "en")
        self.assertEqual(dict(settings.LANGUAGES), {"en": "English", "tet": "Tetum"})
        self.assertIn(settings.BASE_DIR / "locale", settings.LOCALE_PATHS)
        middleware = settings.MIDDLEWARE
        self.assertLess(
            middleware.index("django.middleware.locale.LocaleMiddleware"),
            middleware.index("django.middleware.common.CommonMiddleware"),
        )
        self.assertLess(
            middleware.index("dina_shop.middleware.ConfiguredLanguageMiddleware"),
            middleware.index("django.middleware.common.CommonMiddleware"),
        )

    def test_accept_language_controls_content_language(self):
        client = Client()
        tetum = client.get(
            "/api/users/user/csrf/", HTTP_ACCEPT_LANGUAGE="tet"
        )
        english = client.get(
            "/api/users/user/csrf/", HTTP_ACCEPT_LANGUAGE="en"
        )
        unsupported = client.get(
            "/api/users/user/csrf/", HTTP_ACCEPT_LANGUAGE="zz"
        )
        regional_tetum = client.get(
            "/api/users/user/csrf/", HTTP_ACCEPT_LANGUAGE="tet-TL, en;q=0.8"
        )

        self.assertEqual(tetum.headers["Content-Language"], "tet")
        self.assertEqual(english.headers["Content-Language"], "en")
        self.assertEqual(unsupported.headers["Content-Language"], "en")
        self.assertEqual(regional_tetum.headers["Content-Language"], "tet")


class AuthenticationApiTests(TestCase):
    def setUp(self):
        self.password = "A-secure-test-password-482!"
        self.user = User.objects.create_user(
            email="api-owner@example.com",
            password=self.password,
            first_name="Dina",
        )

    def test_csrf_is_required_for_session_login(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(
            "/api/users/user/login/",
            {"email": self.user.email, "password": self.password},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

        csrf_response = client.get("/api/users/user/csrf/")
        token = csrf_response.json()["csrf_token"]
        response = client.post(
            "/api/users/user/login/",
            {"email": self.user.email, "password": self.password},
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["email"], self.user.email)

    def test_me_exposes_only_safe_profile_fields(self):
        client = APIClient()
        client.force_authenticate(self.user)
        response = client.patch(
            "/api/users/user/me/",
            {"first_name": "Updated", "is_superuser": True},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["first_name"], "Updated")
        self.assertNotIn("password", response.json())
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_superuser)

    def test_jwt_obtain_rotate_and_blacklist(self):
        client = APIClient()
        obtained = client.post(
            "/api/users/user/token/",
            {"email": self.user.email, "password": self.password},
            format="json",
        )
        self.assertEqual(obtained.status_code, 200)
        refreshed = client.post(
            "/api/users/user/token/refresh/",
            {"refresh": obtained.data["refresh"]},
            format="json",
        )
        self.assertEqual(refreshed.status_code, 200)
        self.assertIn("refresh", refreshed.data)
        blacklisted = client.post(
            "/api/users/user/token/blacklist/",
            {"refresh": refreshed.data["refresh"]},
            format="json",
        )
        self.assertEqual(blacklisted.status_code, 200)

    def test_notification_acknowledgement_is_owned_and_idempotent(self):
        client = APIClient()
        client.force_authenticate(self.user)
        payload = {
            "notification_id": "low-stock",
            "fingerprint": "variant:123:4",
            "action": "read",
        }
        first = client.post(
            "/api/users/notification-receipt/acknowledge/", payload, format="json"
        )
        second = client.post(
            "/api/users/notification-receipt/acknowledge/", payload, format="json"
        )
        self.assertIn(first.status_code, (200, 201))
        self.assertEqual(second.status_code, 200)
        self.assertEqual(NotificationReceipt.objects.filter(user=self.user).count(), 1)

    def test_protected_endpoint_rejects_anonymous_request(self):
        response = APIClient().get("/api/users/notification-receipt/")
        self.assertEqual(response.status_code, 401)

    def test_schema_and_docs_are_authenticated(self):
        anonymous = APIClient()
        self.assertEqual(anonymous.get("/api/schema/").status_code, 401)
        self.assertEqual(anonymous.get("/api/docs/").status_code, 401)
        anonymous.force_authenticate(self.user)
        self.assertEqual(anonymous.get("/api/schema/").status_code, 200)
        self.assertEqual(anonymous.get("/api/docs/").status_code, 200)

    def test_validation_errors_use_shared_shape(self):
        response = APIClient().post(
            "/api/users/user/login/", {"email": "not-an-email"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["error"]["code"], "validation_error")
        self.assertIn("fields", response.data["error"])
