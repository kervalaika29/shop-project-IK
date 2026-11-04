from django.urls import path

from . import views

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="register"),
    path("login/", views.UserLoginView.as_view(), name="login"),
    path("logout/", views.UserLogoutView.as_view(), name="logout"),
    # პაროლის აღდგენა (HW44). სახელები (password_reset...) Django-ს სტანდარტულია: წერილის
    # შაბლონში {% url 'password_reset_confirm' ... %} ამ სახელით იძებნება.
    path("password-reset/", views.UserPasswordResetView.as_view(), name="password_reset"),
    path(
        "password-reset/done/",
        views.UserPasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        views.UserPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        views.UserPasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
]
