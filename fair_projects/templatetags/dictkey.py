from django import template

register = template.Library()


@register.filter
def dictkey(dictionary: dict, key):
    return dictionary.get(key, '')
