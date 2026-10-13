from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.generics import GenericAPIView
from rest_framework_simplejwt.views import (
    TokenBlacklistView,
    TokenObtainPairView,
    TokenRefreshView,
)

from users.serializers.user import (
    CsrfTokenSerializer,
    EmptySerializer,
    LoginSerializer,
    UserProfileSerializer,
    UserProfileUpdateSerializer,
)
from dina_shop.api.schema import ErrorResponseSerializer


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(GenericAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    serializer_class = CsrfTokenSerializer

    def get(self, request):
        return Response({"csrf_token": get_token(request)})


@method_decorator(csrf_protect, name="dispatch")
class LoginView(GenericAPIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"
    serializer_class = LoginSerializer

    @extend_schema(
        request=LoginSerializer,
        responses={
            200: UserProfileSerializer,
            400: ErrorResponseSerializer,
            403: ErrorResponseSerializer,
        },
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request=request,
            username=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )
        if user is None or not user.is_active:
            return Response(
                {
                    "error": {
                        "code": "invalid_credentials",
                        "message": "The email or password is incorrect.",
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        login(request, user)
        return Response(UserProfileSerializer(user).data)


class LogoutView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = EmptySerializer

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserMeView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserProfileSerializer

    def get(self, request):
        return Response(UserProfileSerializer(request.user).data)

    def patch(self, request):
        serializer = UserProfileUpdateSerializer(
            request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserProfileSerializer(request.user).data)


class TokenThrottleMixin:
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "token"


class OwnerTokenObtainPairView(TokenThrottleMixin, TokenObtainPairView):
    pass


class OwnerTokenRefreshView(TokenThrottleMixin, TokenRefreshView):
    pass


class OwnerTokenBlacklistView(TokenThrottleMixin, TokenBlacklistView):
    pass
