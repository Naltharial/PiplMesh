from django import template
from django.core.serializers import serialize
from django.utils import safestring, simplejson
from django.db.models import query

register = template.Library()

@register.inclusion_tag('user/user_image.html', takes_context=True)
def user_image(context, user=None):
    if user is None:
        user = context['user']

    return {
        'user_image_url': user.get_image_url(),
    }

@register.filter(name='json', is_safe=True)
def json(obj):
    if isinstance(object, query.QuerySet):
        return safestring.mark_safe(serialize('json', obj))
    return safestring.mark_safe(simplejson.dumps(obj))
