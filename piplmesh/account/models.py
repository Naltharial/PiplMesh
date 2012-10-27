import datetime, hashlib, urllib, uuid

from django.conf import settings
from django.contrib.auth import hashers, models as auth_models
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core import mail
from django.db import models
from django.test import client
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

import mongoengine
from mongoengine.django import auth

from missing import timezone as timezone_missing

from . import fields, utils
from .. import panels as piplmesh_panels

LOWER_DATE_LIMIT = 366 * 120 # days
USERNAME_REGEX = r'[\w.@+-]+'
CONFIRMATION_TOKEN_VALIDITY = 5 # days

def upper_birthdate_limit():
    return timezone_missing.to_date(timezone.now())

def lower_birthdate_limit():
    return timezone_missing.to_date(timezone.now() - datetime.timedelta(days=LOWER_DATE_LIMIT))

def generate_channel_id():
    return uuid.uuid4()

class Connection(mongoengine.EmbeddedDocument):
    http_if_none_match = mongoengine.StringField()
    http_if_modified_since = mongoengine.StringField()
    channel_id = mongoengine.StringField()

class EmailConfirmationToken(mongoengine.EmbeddedDocument):
    value = mongoengine.StringField(max_length=20, required=True)
    created_time = mongoengine.DateTimeField(default=lambda: timezone.now(), required=True)

    def check_token(self, confirmation_token):
        if confirmation_token != self.value:
            return False
        elif (timezone.now() - self.created_time).days > CONFIRMATION_TOKEN_VALIDITY:
            return False
        else:
            return True

class TwitterAccessToken(mongoengine.EmbeddedDocument):
    key = mongoengine.StringField(max_length=150)
    secret = mongoengine.StringField(max_length=150)

class PanelState(mongoengine.EmbeddedDocument):
    collapsed = mongoengine.BooleanField(default=False)
    column = mongoengine.IntField()
    order = mongoengine.IntField()
    
class Panel(mongoengine.EmbeddedDocument):
    """
    This class holds panel instances for a user, their properties and layouts.
    """
    
    # Mapping of count of displayed columns (string) to PanelState objects, controlling display for the panel at that number of columns
    layout = mongoengine.MapField(mongoengine.EmbeddedDocumentField(PanelState))
    
    def get_layout(self, columns_count):
        # Transparently provide either existing or default values
        return self.layout.get(columns_count, PanelState())

class User(auth.User):
    username = mongoengine.StringField(
        max_length=30,
        min_length=4,
        regex=r'^' + USERNAME_REGEX + r'$',
        required=True,
        verbose_name=_("username"),
        help_text=_("Minimal of 4 characters and maximum of 30. Letters, digits and @/./+/-/_ only."),
    )
    lazyuser_username = mongoengine.BooleanField(default=True)

    birthdate = fields.LimitedDateTimeField(upper_limit=upper_birthdate_limit, lower_limit=lower_birthdate_limit)
    gender = fields.GenderField()
    language = fields.LanguageField()
    channel_id = mongoengine.UUIDField(default=generate_channel_id)

    facebook_access_token = mongoengine.StringField(max_length=150)
    facebook_profile_data = mongoengine.DictField()

    twitter_access_token = mongoengine.EmbeddedDocumentField(TwitterAccessToken)
    twitter_profile_data = mongoengine.DictField()

    google_access_token = mongoengine.StringField(max_length=150)
    google_profile_data = mongoengine.DictField()

    foursquare_access_token = mongoengine.StringField(max_length=150)
    foursquare_profile_data = mongoengine.DictField()

    browserid_profile_data = mongoengine.DictField()

    connections = mongoengine.ListField(mongoengine.EmbeddedDocumentField(Connection))
    connection_last_unsubscribe = mongoengine.DateTimeField()
    is_online = mongoengine.BooleanField(default=False)

    email_confirmed = mongoengine.BooleanField(default=False)
    email_confirmation_token = mongoengine.EmbeddedDocumentField(EmailConfirmationToken)
    
    # Mapping of panel names (string) to Panel objects which store display data
    panels = mongoengine.MapField(mongoengine.EmbeddedDocumentField(Panel), default=lambda: {panel.get_name(): Panel() for panel in piplmesh_panels.panels_pool.get_all_panels()})
    
    @models.permalink
    def get_absolute_url(self):
        return ('profile', (), {'username': self.username})

    def get_profile_url(self):
        return self.get_absolute_url()

    def is_anonymous(self):
        return not self.is_authenticated()

    def is_authenticated(self):
        # TODO: Check if *_data fields are really false if not linked with third-party authentication
        return self.has_usable_password() or \
            self.facebook_profile_data or \
            self.twitter_profile_data or \
            self.google_profile_data or \
            self.foursquare_profile_data or \
            self.browserid_profile_data

    def check_password(self, raw_password):
        def setter(raw_password):
            self.set_password(raw_password)
        return hashers.check_password(raw_password, self.password, setter)

    def set_unusable_password(self):
        self.password = hashers.make_password(None)
        self.save()
        return self

    def has_usable_password(self):
        return hashers.is_password_usable(self.password)

    def email_user(self, subject, message, from_email=None):
        mail.send_mail(subject, message, from_email, [self.email])

    def get_image_url(self):
        if self.twitter_profile_data and 'profile_image_url' in self.twitter_profile_data:
            return self.twitter_profile_data['profile_image_url']

        elif self.facebook_profile_data:
            return '%s?type=square' % utils.graph_api_url('%s/picture' % self.username)

        elif self.foursquare_profile_data and 'photo' in self.foursquare_profile_data:
            return self.foursquare_profile_data['photo']
        
        elif self.google_profile_data and 'picture' in self.google_profile_data:
            return self.google_profile_data['picture']

        elif self.email:
            request = client.RequestFactory(**settings.DEFAULT_REQUEST).request()
            default_url = request.build_absolute_uri(staticfiles_storage.url(settings.DEFAULT_USER_IMAGE))

            return 'https://secure.gravatar.com/avatar/%(email_hash)s?%(args)s' % {
                'email_hash': hashlib.md5(self.email.lower()).hexdigest(),
                'args': urllib.urlencode({
                    'default': default_url,
                    'size': 50,
                }),
            }

        else:
            return staticfiles_storage.url(settings.DEFAULT_USER_IMAGE)

    def get_user_channel(self):
        """
        User channel is a HTTP push channel dedicated to the user. We make it private by making
        it unguessable and we cycle it regularly (every time user disconnects from all channels).
        """

        return "user/%s" % self.channel_id
 
    @classmethod
    def create_user(cls, username, email=None, password=None):
        now = timezone.now()
        if not username:
            raise ValueError("The given username must be set")
        email = auth_models.UserManager.normalize_email(email)
        user = cls(
            username=username,
            email=email or None,
            is_staff=False,
            is_active=True,
            is_superuser=False,
            last_login=now,
            date_joined=now,
        )
        user.set_password(password)
        user.save()
        return user
    
    def get_layouts(self, columns_count):
        return {name: panel.get_layout(columns_count) for name, panel in self.panels.items()}
    
    def get_panels(self):
        return map(piplmesh_panels.panels_pool.get_panel, self.panels.keys())
    
    def get_all_panels(self):
        return piplmesh_panels.panels_pool.get_all_panels()
    
    def get_collapsed(self, columns_count):
        return {panel: layout.collapsed for panel, layout in self.get_layouts(columns_count).items()}
    
    def set_collapsed(self, columns_count, name, collapsed):
        layout = self.panels[name].get_layout(columns_count)
        layout.collapsed = collapsed
        self.panels[name].layout[columns_count] = layout
    
    def get_columns(self, columns_count):
        panels = []
        for column, order, name in sorted([(panel.column, panel.order, name) for name, panel in self.get_layouts(columns_count).items() if panel.column is not None]):
            assert column >= 0
            while len(panels) <= column:
                panels.append([])
            panels[column].append(name)
           
        return panels
    
    def has_panel(self, name):
        return name in self.panels
    
    def set_panels(self, panels):
        # Preserve prior settings for kept panels
        self.panels = {name: self.panels.get(name, Panel()) for name in panels}
    
    def reorder_panels(self, columns_count, column_ordering):
        """
        This method reorders panels for a user.
        
        :param int columns_count: count of columns for which the layout is changed
        :param dict column_ordering: mapping of panel names to a (column (`int`), order (`int`)) `tuple`
        """
        
        for panel, layout in self.get_layouts(columns_count).items():
            if panel in column_ordering:
                layout.column, layout.order = column_ordering[panel]
                self.panels[panel].layout[columns_count] = layout
