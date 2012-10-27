from django import forms
from django.core import exceptions
from django.forms.extras import widgets
from django.utils.translation import ugettext_lazy as _

from piplmesh import panels
from piplmesh.account import fields, form_fields, models

class UserUsernameForm(forms.Form):
    """
    Class with username form.
    """

    username = forms.RegexField(
        label=_("Username"),
        max_length=30,
        min_length=4,
        regex=r'^' + models.USERNAME_REGEX + r'$',
        help_text=_("Minimal of 4 characters and maximum of 30. Letters, digits and @/./+/-/_ only."),
        error_messages={
            'invalid': _("This value may contain only letters, numbers and @/./+/-/_ characters."),
        }
    )

    def clean_username(self):
        """
        This method checks whether the username exists in a case-insensitive manner.
        """

        username = self.cleaned_data['username']
        if models.User.objects(username__iexact=username).count():
            raise forms.ValidationError(_("A user with that username already exists."), code='username_exists')
        return username

class UserPasswordForm(forms.Form):
    """
    Class with user password form.
    """

    password1 = forms.CharField(
        label=_("Password"),
        min_length=6,
        widget=forms.PasswordInput,
    )
    password2 = forms.CharField(
        label=_("Password (repeat)"),
        widget=forms.PasswordInput,
        help_text=_("Enter the same password as above, for verification."),
    )

    def clean_password2(self):
        """
        This method checks whether the passwords match.
        """

        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password1 != password2:
            raise forms.ValidationError(_("The two password fields did not match."), code='password_mismatch')
        return password2

class UserCurrentPasswordForm(forms.Form):
    """
    Class with user current password form.
    """

    current_password = forms.CharField(
        label=_("Current password"),
        widget=forms.PasswordInput,
        help_text=_("Enter your current password, for verification."),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(UserCurrentPasswordForm, self).__init__(*args, **kwargs)

    def clean_current_password(self):
        """
        This method checks if user password is correct.
        """

        password = self.cleaned_data['current_password']
        if not self.user.check_password(password):
            raise forms.ValidationError(_("Your current password was incorrect."), code='password_incorrect')
        return password

class UserBasicInfoForm(forms.Form):
    """
    Class with user basic information form.
    """

    # TODO: Language field is missing?

    first_name = forms.CharField(label=_("First name"))
    last_name = forms.CharField(label=_("Last name"))
    email = forms.EmailField(label=_("E-mail"))
    gender = forms.ChoiceField(
        label=_("Gender"),
        choices=fields.GENDER_CHOICES,
        widget=forms.RadioSelect(),
        required=False,
    )
    birthdate = form_fields.LimitedDateTimeField(
        upper_limit=models.upper_birthdate_limit,
        lower_limit=models.lower_birthdate_limit,
        label=_("Birth date"),
        required=False,
        widget=widgets.SelectDateWidget(
            years=[
                y for y in range(
                    models.upper_birthdate_limit().year,
                    models.lower_birthdate_limit().year,
                    -1,
                )
            ],
        ),
    )

class UserAdditionalInfoForm(forms.Form):
    """
    Class with user additional information form.
    """

class RegistrationForm(UserUsernameForm, UserPasswordForm, UserBasicInfoForm):
    """
    Class with registration form.
    """

class AccountChangeForm(UserBasicInfoForm, UserAdditionalInfoForm, UserCurrentPasswordForm):
    """
    Class with form for changing your account settings.
    """

class PasswordChangeForm(UserCurrentPasswordForm, UserPasswordForm):
    """
    Class with form for changing password.
    """

class EmailConfirmationSendTokenForm(forms.Form):
    """
    Form for sending an e-mail address confirmation token.
    """

class EmailConfirmationProcessTokenForm(forms.Form):
    """
    Form for processing an e-mail address confirmation token.
    """

    confirmation_token = forms.CharField(
        label=_("Confirmation token"),
        min_length=20,
        max_length=20,
        required=True,
        help_text=_("Please enter the confirmation token you received to your e-mail address."),
    )

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(EmailConfirmationProcessTokenForm, self).__init__(*args, **kwargs)

    def clean_confirmation_token(self):
        """
        This method checks if user confirmation token is correct.
        """

        confirmation_token = self.cleaned_data['confirmation_token']
        if not self.user.email_confirmation_token.check_token(confirmation_token):
            raise forms.ValidationError(_("The confirmation token is invalid or has expired. Please retry."), code='confirmation_token_incorrect')
        return confirmation_token

class PanelFormMetaclass(forms.Form.__metaclass__):
    def __new__(cls, name, bases, attrs):
        for panel in panels.panels_pool.get_all_panels():
            data_box = panel.get_name()
            display_box = data_box + "_display"
            
            attrs[data_box] = forms.BooleanField(initial=False, widget=forms.HiddenInput(), required=False)
            attrs[display_box] = forms.BooleanField(label=data_box, required=False)
            
            # Connect display checkbox to data field
            attrs[display_box].widget = forms.CheckboxInput(attrs={'data-panel':data_box, 'data-display':'True'})
        
        return super(PanelFormMetaclass, cls).__new__(cls, name, bases, attrs)

class PanelForm(forms.Form):
    """
    Form for selecting homepage panels.
    """
    
    __metaclass__ = PanelFormMetaclass
    
    def clean(self):
        cleaned_data = super(PanelForm, self).clean()
        
        for panel_name, panel_enabled in cleaned_data.items():
            try:
                panel = panels.panels_pool.get_panel(panel_name)
                if not panel_enabled:
                    continue
                
                for dependency in panel.get_dependencies():
                    if not cleaned_data.get(dependency, False):
                        raise exceptions.ValidationError(_("Dependencies not satisfied."))
            except KeyError:
                del cleaned_data[panel_name]
            except panels.exceptions.PanelNotRegistered:
                del cleaned_data[panel_name]
        
        return cleaned_data
