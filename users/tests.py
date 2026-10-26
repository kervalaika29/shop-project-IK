from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from shop.models import Category, Product
from shop.tests import TempMediaMixin, make_image

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
class FullScenarioTests(TempMediaMixin, TestCase):
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
