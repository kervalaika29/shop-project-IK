from django import template

register = template.Library()


@register.filter
def is_owned_by(product, user):
    """
    შაბლონში: {% if product|is_owned_by:user %} ... {% endif %}
    ეუბნება შაბლონს, რომ Edit/Delete ღილაკები მხოლოდ პროდუქტის მფლობელს აჩვენოს.
    """
    return product.is_owned_by(user)


@register.inclusion_tag("shop/includes/pagination.html", takes_context=True)
def pagination(context, page_obj):
    """
    შაბლონში: {% pagination page_obj %}
    ხატავს გვერდების ნავიგაციას (« 1 2 3 … 9 »). ყველა სიის გვერდზე ერთი და იგივე ბლოკია,
    ამიტომ ცალკე ტეგია და არა დაკოპირებული HTML.

    ორი რამ, რასაც შაბლონი თავისით ვერ გააკეთებდა:
    - querystring: მიმდინარე ძიების პარამეტრები (?q=...&category=...) გვერდის გარეშე, რომ
      მეორე გვერდზე გადასვლისას ძიება არ დაიკარგოს (?q=sony&category=3&page=2);
    - pages: გვერდების ნომრები "…"-ით შემოკლებული (get_elided_page_range), რომ 50 გვერდის
      შემთხვევაში 50 ღილაკი არ გამოჩნდეს.
    """
    params = context["request"].GET.copy()  # request-ს context processor აძლევს შაბლონს
    params.pop("page", None)

    paginator = page_obj.paginator
    pages = []
    for number in paginator.get_elided_page_range(
        page_obj.number, on_each_side=2, on_ends=1
    ):
        if number == paginator.ELLIPSIS:
            pages.append({"gap": True})
        else:
            pages.append({"number": number, "current": number == page_obj.number})

    return {"page_obj": page_obj, "pages": pages, "querystring": params.urlencode()}
