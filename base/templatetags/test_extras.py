# templatetags/test_extras.py
from django import template

register = template.Library()

@register.filter
def to_cyrillic_letter(option_letter):
    """Преобразует латинскую букву в кириллическую"""
    mapping = {
        'a': 'А', 'b': 'Б', 'c': 'В', 'd': 'Г',
        '1': 'А', '2': 'Б', '3': 'В', '4': 'Г',
        'A': 'А', 'B': 'Б', 'C': 'В', 'D': 'Г',
    }
    if option_letter is None:
        return ''
    return mapping.get(str(option_letter).lower(), option_letter)

@register.filter
def to_cyrillic_options(question):
    """Возвращает варианты ответов с кириллическими префиксами"""
    options = [
        ('А', question.option_a),
        ('Б', question.option_b),
        ('В', question.option_c),
        ('Г', question.option_d),
    ]
    return options

@register.filter
def to_cyrillic_answer(option_letter):
    """Преобразует латинскую букву в кириллическую с точкой"""
    mapping = {
        'a': 'А.', 'b': 'Б.', 'c': 'В.', 'd': 'Г.',
        'A': 'А.', 'B': 'Б.', 'C': 'В.', 'D': 'Г.',
    }
    if option_letter is None:
        return ''
    return mapping.get(str(option_letter), option_letter)