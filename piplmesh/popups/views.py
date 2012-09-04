from django import template
from django.contrib.auth import forms as auth_forms
from django.views.generic import edit as edit_views

class ExternalContextMixin():
    """
    This mixin provides access to external context.
    """
    
    context = None
    
    def get_context_data(self, **kwargs):
        if self.context:
            if not isinstance(self.context, template.Context):
                self.context = template.Context(self.context)
        
            self.context.update(kwargs)
                
            return self.context
        else:
            return template.Context(kwargs)

class LoginPopupView(ExternalContextMixin, edit_views.FormView):
    """
    This view displays the login popup.
    """

    template_name = 'login.html'
    form_class = auth_forms.AuthenticationForm
