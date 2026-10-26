from django import template

register = template.Library()


@register.filter
def is_owned_by(product, user):
    """
    შაბლონში: {% if product|is_owned_by:user %} ... {% endif %}
    ეუბნება შაბლონს, რომ Edit/Delete ღილაკები მხოლოდ პროდუქტის მფლობელს აჩვენოს.
    """
    return product.is_owned_by(user)
