from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import LoginForm, RegisterForm


class RegisterView(CreateView):
    """
    რეგისტრაცია. CreateView ამოწმებს RegisterForm-ს და ინახავს ახალ User-ს;
    შემდეგ form_valid-ში მომხმარებელს ავტომატურად ვაშვებთ სისტემაში (login),
    რომ რეგისტრაციის მერე ცალკე შესვლა აღარ დასჭირდეს.
    """

    form_class = RegisterForm
    template_name = "users/register.html"
    success_url = reverse_lazy("home")

    def dispatch(self, request, *args, **kwargs):
        # უკვე შესულ მომხმარებელს რეგისტრაციის გვერდი არ სჭირდება
        if request.user.is_authenticated:
            return redirect("home")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)  # აქ შეინახა და self.object = ახალი User
        login(self.request, self.object)
        messages.success(
            self.request, f"Welcome, {self.object.username}! Your account was created."
        )
        return response


class UserLoginView(LoginView):
    """
    შესვლა. Django-ს LoginView ამოწმებს username/პაროლს და ხსნის სესიას.
    თუ მომხმარებელი დაცული გვერდიდან მოვიდა (?next=...), შესვლის შემდეგ იქ დაბრუნდება,
    სხვა შემთხვევაში გადადის LOGIN_REDIRECT_URL-ზე (settings.py).
    """

    template_name = "users/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        messages.success(self.request, f"Welcome back, {form.get_user().username}!")
        return super().form_valid(form)


class UserLogoutView(LogoutView):
    """
    გასვლა. Django 5+ -ში LogoutView მხოლოდ POST-ს იღებს (ბმულზე გადასვლით
    გასვლა არ ხდება, CSRF-ისგან დასაცავად), ამიტომ ღილაკი ფორმაშია.
    გადამისამართება: LOGOUT_REDIRECT_URL (settings.py).
    """

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        messages.info(request, "You have been logged out.")
        return response
