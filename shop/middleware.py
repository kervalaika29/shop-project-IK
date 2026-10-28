from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.urls import reverse


class MaintenanceModeMiddleware:
    """
    ტექნიკური სამუშაოების რეჟიმი (HW42).

    თუ settings.py-ში წერია MAINTENANCE_MODE = True, ყველა request-ზე (ნებისმიერი გვერდი,
    ფორმა, POST და ა.შ.) ჩვენ ვაბრუნებთ "Site is under maintenance" გვერდს. გამონაკლისია
    მხოლოდ /admin/: ადმინისტრატორი ჩვეულებრივ მუშაობს, რომ საიტის მართვა შეძლოს.
    MAINTENANCE_MODE = False-ზე (ან თუ პარამეტრი საერთოდ არ არის) საიტი ჩვეულებრივ მუშაობს.

    როგორ მუშაობს middleware: Django ყოველ request-ს თანმიმდევრულად ატარებს settings.py-ის
    MIDDLEWARE სიაში. __call__-ში ან თვითონ ვაბრუნებთ პასუხს (მაშინ view საერთოდ არ
    სრულდება), ან get_response(request)-ით request-ს შემდეგ ფენას ვაწვდით.
    """

    def __init__(self, get_response):
        # get_response: სიაში შემდეგი middleware (ან თვითონ view, თუ ეს ბოლოა)
        self.get_response = get_response

    def __call__(self, request):
        # პარამეტრს ყოველ request-ზე ვკითხულობთ (და არა __init__-ში), რომ settings.py-ის
        # ცვლილება (და ტესტებში override_settings) მაშინვე ამოქმედდეს.
        if getattr(settings, "MAINTENANCE_MODE", False) and not self.is_admin(request):
            # 503 Service Unavailable: "საიტი დროებით მიუწვდომელია". რენდერი request-ის გარეშე
            # ხდება, ამიტომ context processor-ები (და მათი ბაზის მოთხოვნები) არ სრულდება:
            # ტექნიკური სამუშაოებისას ბაზა შეიძლება მიუწვდომელიც კი იყოს.
            html = render_to_string("shop/maintenance.html")
            return HttpResponse(html, status=503)
        return self.get_response(request)

    @staticmethod
    def is_admin(request):
        """True, თუ მისამართი /admin/-ით იწყება (ან ზუსტად /admin-ია, ხაზის გარეშე)."""
        admin_url = reverse("admin:index")  # "/admin/"; აქედან ვიღებთ, რომ მისამართი ორჯერ არ ვწეროთ
        return request.path.startswith(admin_url) or request.path == admin_url.rstrip("/")
