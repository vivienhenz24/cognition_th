from django.contrib import admin
from django.contrib.auth.decorators import login_not_required
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import include, path


urlpatterns = [
    path(
        "login/",
        login_not_required(
            LoginView.as_view(template_name="registration/login.html")
        ),
        name="login",
    ),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("admin/", admin.site.urls),
    path("", include("kyc.urls")),
]
