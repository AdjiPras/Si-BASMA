from django import template
register = template.Library()

@register.filter
def waktu_color(value):
    colors = {
        'PAGI': "#37974F",  # Gold
        'SIANG': '#007BFF', # Primary Blue
        'SORE': "#AC7716",
    }
    return colors.get(value, '#6C757D')