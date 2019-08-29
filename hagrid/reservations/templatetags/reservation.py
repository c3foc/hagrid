from babel.numbers import format_currency
from django import template

register = template.Library()


def as_currency(value):
    return format_currency(value, 'EUR', locale='de_DE')

register.filter('as_currency', as_currency)
