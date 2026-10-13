from django.urls import path

from users.views.user import (
    CsrfView,
    LoginView,
    LogoutView,
    OwnerTokenBlacklistView,
    OwnerTokenObtainPairView,
    OwnerTokenRefreshView,
    UserMeView,
)

app_name = "user"

urlpatterns = [
    path("csrf/", CsrfView.as_view(), name="csrf"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", UserMeView.as_view(), name="me"),
    path("token/", OwnerTokenObtainPairView.as_view(), name="token"),
    path("token/refresh/", OwnerTokenRefreshView.as_view(), name="token-refresh"),
    path(
        "token/blacklist/",
        OwnerTokenBlacklistView.as_view(),
        name="token-blacklist",
    ),
]
