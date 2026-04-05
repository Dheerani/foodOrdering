from django import template

register = template.Library()

@register.filter
def mul(value, arg):
    return value * arg

@register.filter
def calc_total(items):
    return sum(item.price * item.quantity for item in items)
