from django import template

register = template.Library()

@register.filter
def lookup(form, field_name):
    """Lookup a field by name from a form"""
    return getattr(form, field_name, None)

