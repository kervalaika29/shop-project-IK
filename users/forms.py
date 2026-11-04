from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)
from django.core.exceptions import ValidationError

User = get_user_model()


def style_fields(form, placeholders):
    """ყველა ველს Bootstrap-ის კლასს ვამატებთ, რომ ფორმა საიტის დიზაინს შეესაბამებოდეს."""
    for name, field in form.fields.items():
        field.widget.attrs["class"] = "form-control"
        if name in placeholders:
            field.widget.attrs["placeholder"] = placeholders[name]


class RegisterForm(UserCreationForm):
    """
    რეგისტრაციის ფორმა: Django-ს UserCreationForm + სავალდებულო email.
    UserCreationForm თვითონ ამოწმებს, რომ username თავისუფალია, პაროლები ერთმანეთს
    ემთხვევა და პაროლი AUTH_PASSWORD_VALIDATORS-ის წესებს აკმაყოფილებს, ინახავს კი
    პაროლს დაჰეშილი სახით (არასდროს ჩვეულებრივი ტექსტით).
    """

    email = forms.EmailField(label="Email", required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(
            self,
            {
                "username": "Choose a username",
                "email": "name@example.com",
                "password1": "Create a password",
                "password2": "Repeat the password",
            },
        )

    def clean_email(self):
        """ერთი email-ით ორი ანგარიში არ უნდა შეიქმნას (დიდი/პატარა ასოების გარეშე შედარება)."""
        email = self.cleaned_data["email"].strip()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email


class LoginForm(AuthenticationForm):
    """შესვლის ფორმა: Django-ს AuthenticationForm Bootstrap-ის სტილით."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self, {"username": "Username", "password": "Password"})


class UserPasswordResetForm(PasswordResetForm):
    """
    პაროლის აღდგენის 1-ლი ნაბიჯი (HW44): მომხმარებელი წერს email-ს, რომლითაც დარეგისტრირდა.
    Django-ს PasswordResetForm თვითონ პოულობს ამ email-ის (აქტიურ) მომხმარებელს და მისთვის
    ერთჯერად ბმულს აგზავნის. აქ მხოლოდ Bootstrap-ის სტილს ვამატებთ.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(self, {"email": "name@example.com"})


class UserSetPasswordForm(SetPasswordForm):
    """
    პაროლის აღდგენის მე-3 ნაბიჯი (HW44): ახალი პაროლი ორჯერ. ძველი პაროლი არ სჭირდება
    (ზუსტად ამიტომ არის ბმულში ერთჯერადი ტოკენი). Django ამოწმებს, რომ პაროლები ემთხვევა და
    AUTH_PASSWORD_VALIDATORS-ის წესებს აკმაყოფილებს, ინახავს კი დაჰეშილ სახით.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        style_fields(
            self,
            {
                "new_password1": "Create a new password",
                "new_password2": "Repeat the new password",
            },
        )
