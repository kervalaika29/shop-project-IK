import re

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from shop.models import Category, Product
from shop.tests import SilentStdoutMixin, TempMediaMixin, make_image

User = get_user_model()
PASSWORD = "Str0ng-pass-123"

# პაროლის ჰეშირება განზრახ ნელია, ტესტებში კი სწრაფი ჰეშერი გვჭირდება
fast_hashing = override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"]
)


def is_logged_in(client):
    return "_auth_user_id" in client.session


@fast_hashing
class RegisterTests(TestCase):
    url = "/users/register/"

    def data(self, **extra):
        data = {
            "username": "newuser",
            "email": "new@example.com",
            "password1": PASSWORD,
            "password2": PASSWORD,
        }
        data.update(extra)
        return data

    def test_url_name(self):
        self.assertEqual(reverse("register"), self.url)

    def test_get_shows_form_with_all_fields(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(response.context["form"].fields),
            ["username", "email", "password1", "password2"],
        )
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_valid_post_creates_user_with_hashed_password(self):
        self.client.post(self.url, self.data())
        user = User.objects.get(username="newuser")
        self.assertEqual(user.email, "new@example.com")
        self.assertNotEqual(user.password, PASSWORD)  # ჩვეულებრივი ტექსტით არ ინახება
        self.assertTrue(user.check_password(PASSWORD))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_user_is_logged_in_and_redirected_home_after_registration(self):
        response = self.client.post(self.url, self.data(), follow=True)
        self.assertRedirects(response, reverse("home"))
        self.assertTrue(is_logged_in(self.client))
        self.assertContains(response, "Welcome, newuser!")

    def test_passwords_must_match(self):
        response = self.client.post(self.url, self.data(password2="Different-pass-456"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("password2", response.context["form"].errors)
        self.assertFalse(User.objects.exists())
        self.assertFalse(is_logged_in(self.client))

    def test_weak_passwords_are_rejected(self):
        for label, password in {
            "too short": "Ab1!",
            "too common": "password123",
            "only digits": "83749201657",
            "same as username": "newuser",
        }.items():
            with self.subTest(case=label):
                response = self.client.post(
                    self.url, self.data(password1=password, password2=password)
                )
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].errors)
                self.assertFalse(User.objects.exists())

    def test_username_must_be_unique(self):
        User.objects.create_user("newuser", "first@example.com", PASSWORD)
        response = self.client.post(self.url, self.data())
        self.assertIn("username", response.context["form"].errors)
        self.assertEqual(User.objects.count(), 1)

    def test_email_is_required_and_must_be_valid(self):
        for label, email in {"empty": "", "not an email": "abc"}.items():
            with self.subTest(case=label):
                response = self.client.post(self.url, self.data(email=email))
                self.assertIn("email", response.context["form"].errors)
                self.assertFalse(User.objects.exists())

    def test_email_must_be_unique_ignoring_case(self):
        User.objects.create_user("first", "New@Example.com", PASSWORD)
        response = self.client.post(self.url, self.data())
        self.assertIn("already exists", str(response.context["form"].errors["email"]))
        self.assertEqual(User.objects.count(), 1)

    def test_username_is_required(self):
        response = self.client.post(self.url, self.data(username=""))
        self.assertIn("username", response.context["form"].errors)

    def test_logged_in_user_is_redirected_away_from_register_page(self):
        user = User.objects.create_user("someone", "s@example.com", PASSWORD)
        self.client.force_login(user)
        self.assertRedirects(self.client.get(self.url), reverse("home"))

    def test_post_without_csrf_token_is_rejected(self):
        strict_client = Client(enforce_csrf_checks=True)
        self.assertEqual(strict_client.post(self.url, self.data()).status_code, 403)
        self.assertFalse(User.objects.exists())


@fast_hashing
class LoginTests(TestCase):
    url = "/users/login/"

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("irakli", "irakli@example.com", PASSWORD)

    def test_url_name(self):
        self.assertEqual(reverse("login"), self.url)

    def test_get_shows_login_form(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password"')
        self.assertContains(response, "csrfmiddlewaretoken")

    def test_valid_login_redirects_home_and_logs_in(self):
        response = self.client.post(self.url, {"username": "irakli", "password": PASSWORD}, follow=True)
        self.assertRedirects(response, reverse("home"))
        self.assertTrue(is_logged_in(self.client))
        self.assertContains(response, "Welcome back, irakli!")

    def test_wrong_password_shows_error_and_does_not_log_in(self):
        response = self.client.post(self.url, {"username": "irakli", "password": "wrong"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please enter a correct username and password")
        self.assertFalse(is_logged_in(self.client))

    def test_unknown_user_cannot_log_in(self):
        response = self.client.post(self.url, {"username": "ghost", "password": PASSWORD})
        self.assertContains(response, "Please enter a correct username and password")
        self.assertFalse(is_logged_in(self.client))

    def test_empty_fields_show_errors(self):
        response = self.client.post(self.url, {"username": "", "password": ""})
        self.assertTrue(response.context["form"].errors)
        self.assertFalse(is_logged_in(self.client))

    def test_inactive_user_cannot_log_in(self):
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        self.client.post(self.url, {"username": "irakli", "password": PASSWORD})
        self.assertFalse(is_logged_in(self.client))

    def test_login_returns_to_page_the_user_came_from(self):
        response = self.client.post(
            f"{self.url}?next=/product/add/",
            {"username": "irakli", "password": PASSWORD, "next": "/product/add/"},
        )
        self.assertRedirects(response, "/product/add/")

    def test_full_redirect_cycle_from_protected_page(self):
        response = self.client.get("/product/add/")
        self.assertRedirects(response, "/users/login/?next=/product/add/")
        response = self.client.post(
            "/users/login/?next=/product/add/",
            {"username": "irakli", "password": PASSWORD, "next": "/product/add/"},
        )
        self.assertRedirects(response, "/product/add/")

    def test_unsafe_next_url_is_ignored(self):
        response = self.client.post(
            self.url,
            {"username": "irakli", "password": PASSWORD, "next": "https://evil.example.com/"},
        )
        self.assertRedirects(response, reverse("home"))

    def test_logged_in_user_is_redirected_away_from_login_page(self):
        self.client.force_login(self.user)
        self.assertRedirects(self.client.get(self.url), reverse("home"))

    def test_post_without_csrf_token_is_rejected(self):
        strict_client = Client(enforce_csrf_checks=True)
        response = strict_client.post(self.url, {"username": "irakli", "password": PASSWORD})
        self.assertEqual(response.status_code, 403)


@fast_hashing
class LogoutTests(TestCase):
    url = "/users/logout/"

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("irakli", "irakli@example.com", PASSWORD)

    def test_url_name(self):
        self.assertEqual(reverse("logout"), self.url)

    def test_post_logs_out_and_redirects_home(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, follow=True)
        self.assertRedirects(response, reverse("home"))
        self.assertFalse(is_logged_in(self.client))
        self.assertContains(response, "You have been logged out.")

    def test_get_does_not_log_out(self):
        """გასვლა მხოლოდ POST-ით ხდება (Django 5+): ბმულზე შემთხვევით გადასვლა არაფერს აკეთებს."""
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.assertTrue(is_logged_in(self.client))

    def test_logout_works_when_not_logged_in(self):
        self.assertRedirects(self.client.post(self.url), reverse("home"))

    def test_post_without_csrf_token_is_rejected(self):
        strict_client = Client(enforce_csrf_checks=True)
        strict_client.force_login(self.user)
        self.assertEqual(strict_client.post(self.url).status_code, 403)
        self.assertTrue(is_logged_in(strict_client))

    def test_after_logout_protected_pages_are_closed_again(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get("/product/add/").status_code, 200)
        self.client.post(self.url)
        self.assertEqual(self.client.get("/product/add/").status_code, 302)


@fast_hashing
class NavbarTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("irakli", "irakli@example.com", PASSWORD)

    def test_anonymous_sees_login_and_register_links(self):
        response = self.client.get(reverse("home"))
        self.assertContains(response, reverse("login"))
        self.assertContains(response, reverse("register"))
        self.assertNotContains(response, reverse("logout"))

    def test_logged_in_user_sees_name_and_logout_form(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("home"))
        self.assertContains(response, "irakli")
        self.assertContains(response, f'action="{reverse("logout")}"')
        self.assertNotContains(response, f'href="{reverse("login")}"')
        self.assertNotContains(response, f'href="{reverse("register")}"')


@fast_hashing
class FullScenarioTests(SilentStdoutMixin, TempMediaMixin, TestCase):
    """მთელი სცენარი ბრაუზერის როლში: ორი ადამიანი ერთმანეთის პროდუქტს ვერ ეხება."""

    def register(self, client, username):
        client.post(
            "/users/register/",
            {
                "username": username,
                "email": f"{username}@example.com",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )

    def test_two_users_cannot_touch_each_others_products(self):
        category = Category.objects.create(name="Phones")
        anna, boris = Client(), Client()

        # ანა რეგისტრირდება და სურათიანი პროდუქტი ამატებს
        self.register(anna, "anna")
        response = anna.post(
            "/product/add/",
            {"name": "Anna phone", "category": category.pk, "price": "100", "image": make_image()},
        )
        product = Product.objects.get(name="Anna phone")
        self.assertRedirects(response, product.get_absolute_url())
        self.assertEqual(product.user.username, "anna")
        self.assertTrue(product.image)

        # ბორისი რეგისტრირდება: ანას პროდუქტს ვერ შეცვლის და ვერ წაშლის
        self.register(boris, "boris")
        self.assertEqual(boris.get(f"/product/{product.pk}/edit/").status_code, 403)
        self.assertEqual(boris.post(f"/product/{product.pk}/delete/").status_code, 403)
        self.assertTrue(Product.objects.filter(pk=product.pk).exists())

        # ანა თავისას ცვლის და შემდეგ შლის (სურათის ფაილიც იშლება)
        update = anna.post(
            f"/product/{product.pk}/edit/",
            {"name": "Anna phone 2", "category": category.pk, "price": "120"},
        )
        self.assertRedirects(update, product.get_absolute_url())
        self.assertEqual(len(self.media_files()), 1)
        anna.post(f"/product/{product.pk}/delete/")
        self.assertFalse(Product.objects.filter(pk=product.pk).exists())
        self.assertEqual(self.media_files(), [])


# ---------------------------------------------------------------------------------------------
# HW44: პაროლის აღდგენა
# ტესტებში Django წერილებს რეალურად არ აგზავნის და არც ტერმინალში ბეჭდავს: ისინი mail.outbox-ში
# ინახება, საიდანაც ვკითხულობთ წერილის ტექსტს და მასში არსებულ ბმულს.
# ---------------------------------------------------------------------------------------------

NEW_PASSWORD = "Brand-new-pass-987"
RESET_LINK_RE = re.compile(r"http://testserver(/users/reset/[^\s/]+/[^\s/]+/)")


def reset_link(message=None):
    """წერილის ტექსტიდან იღებს აღდგენის ბმულს (მხოლოდ მისამართს, domain-ის გარეშე)."""
    message = message or mail.outbox[-1]
    match = RESET_LINK_RE.search(message.body)
    assert match, f"reset link not found in:\n{message.body}"
    return match.group(1)


@fast_hashing
class PasswordResetUrlTests(TestCase):
    def test_url_names(self):
        self.assertEqual(reverse("password_reset"), "/users/password-reset/")
        self.assertEqual(reverse("password_reset_done"), "/users/password-reset/done/")
        self.assertEqual(
            reverse("password_reset_confirm", args=["MQ", "abc-123"]),
            "/users/reset/MQ/abc-123/",
        )
        self.assertEqual(reverse("password_reset_complete"), "/users/reset/done/")

    def test_all_public_pages_open_for_anonymous_user(self):
        """აღდგენა იმ ადამიანისთვისაა, ვისაც შესვლა არ შეუძლია, ამიტომ გვერდები ანონიმურს უნდა იღებდეს."""
        for name in ("password_reset", "password_reset_done", "password_reset_complete"):
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_login_page_links_to_password_reset(self):
        response = self.client.get(reverse("login"))
        self.assertContains(response, f'href="{reverse("password_reset")}"')
        self.assertContains(response, "Forgot your password?")

    def test_pages_use_our_templates_not_the_admin_ones(self):
        """admin-ის ჩაშენებული registration/... შაბლონები არ უნდა გამოჩნდეს: საიტის დიზაინი უნდა ჩანდეს."""
        for name, template in (
            ("password_reset", "users/password_reset_form.html"),
            ("password_reset_done", "users/password_reset_done.html"),
            ("password_reset_complete", "users/password_reset_complete.html"),
        ):
            with self.subTest(page=name):
                response = self.client.get(reverse(name))
                self.assertTemplateUsed(response, template)
                self.assertTemplateUsed(response, "shop/base.html")  # მენიუ, footer და ა.შ.

    def test_views_are_django_class_based_views(self):
        from django.contrib.auth import views as auth_views

        from users import views

        self.assertTrue(issubclass(views.UserPasswordResetView, auth_views.PasswordResetView))
        self.assertTrue(issubclass(views.UserPasswordResetDoneView, auth_views.PasswordResetDoneView))
        self.assertTrue(
            issubclass(views.UserPasswordResetConfirmView, auth_views.PasswordResetConfirmView)
        )
        self.assertTrue(
            issubclass(views.UserPasswordResetCompleteView, auth_views.PasswordResetCompleteView)
        )


@fast_hashing
class PasswordResetRequestTests(TestCase):
    """1-ლი ნაბიჯი: email-ის შეყვანა და წერილის გაგზავნა."""

    url = "/users/password-reset/"

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("irakli", "irakli@example.com", PASSWORD)

    def test_get_shows_email_form(self):
        response = self.client.get(self.url)
        self.assertEqual(list(response.context["form"].fields), ["email"])
        self.assertContains(response, "csrfmiddlewaretoken")
        self.assertContains(response, 'class="form-control"')  # Bootstrap სტილი

    def test_valid_email_sends_one_email_and_redirects_to_done_page(self):
        response = self.client.post(self.url, {"email": "irakli@example.com"})
        self.assertRedirects(response, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)

    def test_email_headers(self):
        self.client.post(self.url, {"email": "irakli@example.com"})
        message = mail.outbox[0]
        self.assertEqual(message.to, ["irakli@example.com"])
        self.assertEqual(message.subject, "Password reset on Mini Shop")
        self.assertEqual(message.from_email, settings.DEFAULT_FROM_EMAIL)

    def test_email_body_has_username_and_working_link(self):
        self.client.post(self.url, {"email": "irakli@example.com"})
        body = mail.outbox[0].body
        self.assertIn("Hello irakli,", body)
        self.assertIn("Your username (in case you forgot it): irakli", body)
        link = reset_link()
        self.assertTrue(link.startswith("/users/reset/"))
        self.assertEqual(self.client.get(link).status_code, 302)  # ტოკენი მისაღებია

    def test_email_is_plain_readable_text(self):
        """
        ყველა ხაზი 78 სიმბოლოზე მოკლეა, ამიტომ წერილი quoted-printable-ით არ კოდირდება და
        ტერმინალში (console backend) ბმული "="-ებით არ იჭრება და მთლიანი რჩება.
        """
        self.client.post(self.url, {"email": "irakli@example.com"})
        message = mail.outbox[0]
        self.assertLessEqual(max(len(line) for line in message.body.splitlines()), 78)
        self.assertNotEqual(
            message.message()["Content-Transfer-Encoding"].lower(), "quoted-printable"
        )
        self.assertNotIn("&amp;", message.body)  # autoescape გამორთულია: წერილი ტექსტია და არა HTML

    def test_email_is_found_regardless_of_letter_case(self):
        self.client.post(self.url, {"email": "  IRAKLI@Example.COM "})
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["irakli@example.com"])

    def test_unknown_email_looks_exactly_like_a_known_one_and_sends_nothing(self):
        """უცხოს არ უნდა შეეძლოს გაიგოს, რომელი email არის რეგისტრირებული (ორივე შემთხვევაში იგივე გვერდია)."""
        known = self.client.post(self.url, {"email": "irakli@example.com"}, follow=True)
        mail.outbox.clear()
        unknown = self.client.post(self.url, {"email": "nobody@example.com"}, follow=True)
        self.assertEqual(mail.outbox, [])
        self.assertEqual(known.redirect_chain, unknown.redirect_chain)
        self.assertEqual(known.status_code, unknown.status_code)
        self.assertEqual(known.content.decode(), unknown.content.decode())

    def test_invalid_email_format_shows_error_and_sends_nothing(self):
        for label, value in {"not an email": "irakli", "no domain": "irakli@", "empty": ""}.items():
            with self.subTest(case=label):
                response = self.client.post(self.url, {"email": value})
                self.assertEqual(response.status_code, 200)
                self.assertIn("email", response.context["form"].errors)
                self.assertEqual(mail.outbox, [])

    def test_inactive_user_gets_no_email(self):
        User.objects.filter(pk=self.user.pk).update(is_active=False)
        response = self.client.post(self.url, {"email": "irakli@example.com"})
        self.assertRedirects(response, reverse("password_reset_done"))
        self.assertEqual(mail.outbox, [])

    def test_user_with_unusable_password_gets_no_email(self):
        self.user.set_unusable_password()
        self.user.save()
        self.client.post(self.url, {"email": "irakli@example.com"})
        self.assertEqual(mail.outbox, [])

    def test_each_request_creates_a_fresh_link(self):
        """ორჯერ მოთხოვნა ორ წერილს აგზავნის; ორივე ბმული ჯერ სწორია, სანამ პაროლი არ შეიცვლება."""
        self.client.post(self.url, {"email": "irakli@example.com"})
        self.client.post(self.url, {"email": "irakli@example.com"})
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(self.client.get(reset_link(mail.outbox[0])).status_code, 302)
        self.assertEqual(self.client.get(reset_link(mail.outbox[1])).status_code, 302)

    def test_request_does_not_change_the_password(self):
        self.client.post(self.url, {"email": "irakli@example.com"})
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_post_without_csrf_token_is_rejected(self):
        strict_client = Client(enforce_csrf_checks=True)
        response = strict_client.post(self.url, {"email": "irakli@example.com"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(mail.outbox, [])

    def test_done_page_does_not_reveal_whether_the_email_exists(self):
        response = self.client.get(reverse("password_reset_done"))
        self.assertContains(response, "If an account exists")
        self.assertContains(response, reverse("login"))
        self.assertContains(response, reverse("password_reset"))  # "Try another email"


@fast_hashing
class PasswordResetConfirmTests(TestCase):
    """მე-3 და მე-4 ნაბიჯები: ბმული წერილიდან, ახალი პაროლი, დასრულება."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("irakli", "irakli@example.com", PASSWORD)

    def setUp(self):
        self.client.post("/users/password-reset/", {"email": "irakli@example.com"})
        self.link = reset_link()

    def open_form(self):
        """ბმულზე გადასვლა და გადამისამართების გაყოლა: აბრუნებს ახალი პაროლის გვერდს."""
        return self.client.get(self.link, follow=True)

    def set_password(self, password1=NEW_PASSWORD, password2=None):
        self.open_form()
        set_url = self.link.rsplit("/", 2)[0] + "/set-password/"
        return self.client.post(
            set_url,
            {
                "new_password1": password1,
                "new_password2": password1 if password2 is None else password2,
            },
        )

    def test_link_redirects_to_url_without_the_token(self):
        """ტოკენი სესიაში გადადის და მისამართიდან ქრება, რომ Referer-ით არსად გაჟონოს."""
        response = self.client.get(self.link)
        token = self.link.strip("/").split("/")[-1]
        self.assertEqual(response.status_code, 302)
        self.assertNotIn(token, response["Location"])
        self.assertTrue(response["Location"].endswith("/set-password/"))

    def test_valid_link_shows_new_password_form(self):
        response = self.open_form()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["validlink"])
        self.assertEqual(
            list(response.context["form"].fields), ["new_password1", "new_password2"]
        )
        self.assertContains(response, "csrfmiddlewaretoken")
        self.assertContains(response, 'class="form-control"')
        self.assertTemplateUsed(response, "users/password_reset_confirm.html")

    def test_new_password_is_saved_hashed_and_old_one_stops_working(self):
        response = self.set_password()
        self.assertRedirects(response, reverse("password_reset_complete"))
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.password, NEW_PASSWORD)  # ჩვეულებრივი ტექსტით არ ინახება
        self.assertTrue(self.user.check_password(NEW_PASSWORD))
        self.assertFalse(self.user.check_password(PASSWORD))

    def test_user_is_not_logged_in_automatically(self):
        self.set_password()
        self.assertFalse(is_logged_in(self.client))

    def test_user_can_log_in_with_new_password_only(self):
        self.set_password()
        old = self.client.post("/users/login/", {"username": "irakli", "password": PASSWORD})
        self.assertEqual(old.status_code, 200)
        self.assertFalse(is_logged_in(self.client))
        new = self.client.post("/users/login/", {"username": "irakli", "password": NEW_PASSWORD})
        self.assertRedirects(new, reverse("home"))
        self.assertTrue(is_logged_in(self.client))

    def test_complete_page_links_to_login(self):
        response = self.client.get(self.set_password()["Location"])
        self.assertContains(response, "Your password has been changed")
        self.assertContains(response, f'href="{reverse("login")}"')

    def test_link_works_only_once(self):
        self.set_password()
        response = self.client.get(self.link, follow=True)
        self.assertFalse(response.context["validlink"])
        self.assertContains(response, "Reset link is invalid")
        self.assertNotIn("new_password1", response.context)  # ფორმა აღარ ჩანს
        self.assertContains(response, reverse("password_reset"))  # "Request a new link"

    def test_used_link_cannot_set_another_password(self):
        self.set_password()
        self.client.post(
            self.link.rsplit("/", 2)[0] + "/set-password/",
            {"new_password1": "Another-pass-555", "new_password2": "Another-pass-555"},
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))

    def test_mismatched_passwords_are_rejected(self):
        response = self.set_password(password2="Different-pass-456")
        self.assertEqual(response.status_code, 200)
        self.assertIn("new_password2", response.context["form"].errors)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))  # პაროლი არ შეცვლილა

    def test_weak_passwords_are_rejected(self):
        for label, password in {
            "too short": "Ab1!",
            "too common": "password123",
            "only digits": "83749201657",
            "same as username": "irakli",
        }.items():
            with self.subTest(case=label):
                response = self.set_password(password)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].errors)
                self.user.refresh_from_db()
                self.assertTrue(self.user.check_password(PASSWORD))

    def test_form_can_be_corrected_after_an_error(self):
        """სუსტი პაროლის შემდეგ იმავე ბმულით სწორი პაროლის გაგზავნა მუშაობს."""
        self.set_password("12345")
        response = self.set_password(NEW_PASSWORD)
        self.assertRedirects(response, reverse("password_reset_complete"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(NEW_PASSWORD))

    def test_empty_password_is_rejected(self):
        response = self.set_password("", "")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].errors)

    def test_garbage_and_tampered_links_are_invalid(self):
        uid, token = self.link.strip("/").split("/")[-2:]
        tampered = token[:-1] + ("0" if token[-1] != "0" else "1")
        for label, path in {
            "garbage": "/users/reset/abc/not-a-token/",
            "unknown user": f"/users/reset/MTAwMDA/{token}/",
            "tampered token": f"/users/reset/{uid}/{tampered}/",
        }.items():
            with self.subTest(case=label):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 200)
                self.assertFalse(response.context["validlink"])
                self.assertContains(response, "Reset link is invalid")

    def test_expired_link_is_invalid(self):
        with override_settings(PASSWORD_RESET_TIMEOUT=-1):
            response = self.client.get(self.link)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["validlink"])

    def test_link_dies_when_password_is_changed_another_way(self):
        """ტოკენში პაროლის ჰეშიცაა, ამიტომ პაროლის ნებისმიერი ცვლილება ძველ ბმულებს აუქმებს."""
        self.user.set_password("Changed-elsewhere-777")
        self.user.save()
        response = self.client.get(self.link)
        self.assertFalse(response.context["validlink"])

    def test_old_link_dies_after_a_newer_reset_is_completed(self):
        self.client.post("/users/password-reset/", {"email": "irakli@example.com"})
        first, second = reset_link(mail.outbox[0]), reset_link(mail.outbox[1])
        self.link = second
        self.set_password()
        self.assertFalse(self.client.get(first).context["validlink"])

    def test_post_without_csrf_token_is_rejected(self):
        strict_client = Client(enforce_csrf_checks=True)
        strict_client.get(self.link)  # ტოკენი სესიაში ჩაიწერა
        response = strict_client.post(
            self.link.rsplit("/", 2)[0] + "/set-password/",
            {"new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD},
        )
        self.assertEqual(response.status_code, 403)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(PASSWORD))

    def test_other_users_are_not_affected(self):
        other = User.objects.create_user("anna", "anna@example.com", PASSWORD)
        self.set_password()
        other.refresh_from_db()
        self.assertTrue(other.check_password(PASSWORD))


@fast_hashing
class PasswordResetFullScenarioTests(TestCase):
    """მთელი გზა ბრაუზერის როლში: რეგისტრაცია -> დავიწყდა პაროლი -> წერილი -> ახალი პაროლი -> შესვლა."""

    def test_register_forget_reset_login(self):
        # რეგისტრაცია (email დიდი ასოებით, როგორც ადამიანი წერს)
        self.client.post(
            "/users/register/",
            {
                "username": "tester",
                "email": "Tester@Example.com",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )
        self.client.post("/users/logout/")
        self.assertFalse(is_logged_in(self.client))

        # შესვლის გვერდიდან "Forgot your password?" -> email -> "Check your email"
        login_page = self.client.get("/users/login/")
        self.assertContains(login_page, reverse("password_reset"))
        response = self.client.post(reverse("password_reset"), {"email": "tester@example.com"}, follow=True)
        self.assertRedirects(response, reverse("password_reset_done"))
        self.assertContains(response, "Check your email")

        # წერილი მივიდა; ბმულზე გადასვლა და ახალი პაროლის დაყენება
        self.assertEqual(len(mail.outbox), 1)
        response = self.client.get(reset_link(), follow=True)
        self.assertContains(response, "Choose a new password")
        set_url = response.redirect_chain[-1][0]
        response = self.client.post(
            set_url, {"new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD}, follow=True
        )
        self.assertRedirects(response, reverse("password_reset_complete"))
        self.assertContains(response, "Your password has been changed")

        # ძველი პაროლით ვერ შედის, ახლით შედის
        self.client.post("/users/login/", {"username": "tester", "password": PASSWORD})
        self.assertFalse(is_logged_in(self.client))
        self.client.post("/users/login/", {"username": "tester", "password": NEW_PASSWORD})
        self.assertTrue(is_logged_in(self.client))

    def test_reset_pages_are_closed_in_maintenance_mode(self):
        """HW42-ის ტექნიკური სამუშაოები ახალ გვერდებსაც ეხება (503), /admin/ კი მუშაობს."""
        with override_settings(MAINTENANCE_MODE=True):
            for name in ("password_reset", "password_reset_done", "password_reset_complete"):
                with self.subTest(page=name):
                    response = self.client.get(reverse(name))
                    self.assertEqual(response.status_code, 503)
                    self.assertContains(response, "Site is under maintenance", status_code=503)
