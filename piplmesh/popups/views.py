from django.contrib.auth import forms as auth_forms
from django.views.generic import edit as edit_views

class LoginPopupView(edit_views.FormView):
    """
    This view displays the login popup.
    """

    template_name = 'login.html'
    form_class = auth_forms.AuthenticationForm
