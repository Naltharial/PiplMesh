from django import template

from piplmesh.popups import views

register = template.Library()

class PopupNode(template.base.Node):
    def __init__(self, popup):
        self.popup = popup

    def render(self, context):
        view_object = self.popup()
        view_object.request = context['request']
        popup_template = view_object.render_to_response(context).render()
        return popup_template.content

@register.tag('popup')
def do_popup(parser, token):
    """
    Finds the view we need to include in the popup and passes it to the PopupNode.
    """
    
    bits = token.split_contents()[1:]
    
    if hasattr(views, bits[0]):
        return PopupNode(getattr(views, bits[0]))
    
    return '' # Fail silently for invalid popup views.