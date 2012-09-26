from django import template
from django.core import serializers
from django.db.models import query
from django.utils import simplejson

register = template.Library()

@register.filter()
def is_active(current_path, url_path):
    return current_path.startswith(url_path)

@register.filter(name='json', is_safe=True)
def json(object):
    if isinstance(object, query.QuerySet):
        return serializers.serialize('json', object)
    return simplejson.dumps(object)

@register.filter
def lookup(dict, key):
    if key in dict:
        return dict[key]
    else:
        return False
