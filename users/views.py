from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import LoginForm, RegisterForm, UserPasswordResetForm, UserSetPasswordForm


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


# ---------------------------------------------------------------------------------------------
# პაროლის აღდგენა (HW44). ოთხი ნაბიჯი, თითოეული Django-ს მზა view-ზეა აგებული:
#   1) /users/password-reset/                 email-ის შეყვანა            (UserPasswordResetView)
#   2) /users/password-reset/done/            "შეამოწმეთ ფოსტა"           (UserPasswordResetDoneView)
#   3) /users/reset/<uidb64>/<token>/         ახალი პაროლი (ბმული email-იდან) (UserPasswordResetConfirmView)
#   4) /users/reset/done/                     "პაროლი შეიცვალა"           (UserPasswordResetCompleteView)
# ჩვენ მხოლოდ შაბლონებს (საიტის დიზაინით) და ფორმებს (Bootstrap სტილით) ვცვლით, ლოგიკა Django-სია.
# ---------------------------------------------------------------------------------------------


class UserPasswordResetView(PasswordResetView):
    """
    1-ლი ნაბიჯი: email-ის ფორმა. სწორი ფორმის შემდეგ Django ქმნის ერთჯერად ტოკენიან ბმულს და
    აგზავნის email-ს (settings.py-ში MAILERS = console, ამიტომ წერილი runserver-ის ტერმინალში
    იბეჭდება). ყოველთვის ერთსა და იმავე "done" გვერდზე გადავდივართ, მაშინაც, როცა ასეთი
    email ბაზაში არ არის, რომ გვერდიდან ვერავინ გაიგოს, ვინ არის დარეგისტრირებული.
    """

    template_name = "users/password_reset_form.html"
    email_template_name = "users/password_reset_email.txt"  # წერილის ტექსტი
    subject_template_name = "users/password_reset_subject.txt"  # წერილის თემა
    form_class = UserPasswordResetForm
    success_url = reverse_lazy("password_reset_done")


class UserPasswordResetDoneView(PasswordResetDoneView):
    """მე-2 ნაბიჯი: "წერილი გაგზავნილია" (მხოლოდ შეტყობინების გვერდი)."""

    template_name = "users/password_reset_done.html"


class UserPasswordResetConfirmView(PasswordResetConfirmView):
    """
    მე-3 ნაბიჯი: ბმული email-იდან. Django ამოწმებს ბმულს (uidb64 = მომხმარებლის id, token =
    ერთჯერადი ტოკენი): თუ ბმული სწორია, `validlink=True` და ჩანს ახალი პაროლის ფორმა; თუ
    ვადაგასულია ან უკვე გამოყენებულია, `validlink=False` და შაბლონი შეცდომას აჩვენებს.
    ტოკენი პაროლის შეცვლისთანავე ძალას კარგავს, ამიტომ ერთი ბმულით პაროლს ორჯერ ვერ შეცვლიან.
    """

    template_name = "users/password_reset_confirm.html"
    form_class = UserSetPasswordForm
    success_url = reverse_lazy("password_reset_complete")


class UserPasswordResetCompleteView(PasswordResetCompleteView):
    """მე-4 ნაბიჯი: "პაროლი შეიცვალა" + ღილაკი შესვლის გვერდზე."""

    template_name = "users/password_reset_complete.html"
