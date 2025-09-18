from django import template

register = template.Library()

@register.filter
def times(number):
    """
    Returns a range from 0 to the given number.
    Usage in template:
        {% for i in some_number|times %}
    """
    try:
        return range(int(number))
    except (ValueError, TypeError):
        return []
    
@register.filter
def get_item(sequence, index):
    try:
        return sequence[int(index)]
    except (IndexError, ValueError, TypeError):
        return None

@register.filter
def get_option(likert, val):
    return getattr(likert, f"option_{val}", "")

@register.filter
def get_color(course_form, val):
    """Pick course_form.color_0…color_4 based on the integer val."""
    return getattr(course_form, f"color_{val}", "")

@register.filter
def dict_get(d, key):
    """Safely return d.get(key) or None if missing."""
    try:
        return d.get(key)
    except Exception:
        return None

@register.filter
def for_member(responses, member):
    return responses.filter(evaluee=member)