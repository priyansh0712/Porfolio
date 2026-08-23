from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Template filter to look up a key dynamically in a dictionary.
    Usage: {{ my_dict|get_item:key }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None
