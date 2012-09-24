from __future__ import absolute_import

import datetime, hashlib, urllib, bisect

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

from . import fields, utils
from .. import panels

LOWER_DATE_LIMIT = 366 * 120
USERNAME_REGEX = r'[\w.@+-]+'
CONFIRMATION_TOKEN_VALIDITY = 5 # days

def upper_birthdate_limit():
    return timezone.now().date()

def lower_birthdate_limit():
    return timezone.now().date() - datetime.timedelta(LOWER_DATE_LIMIT)

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

class Panel(mongoengine.EmbeddedDocument):
    pass

class Layout(mongoengine.EmbeddedDocument):
    collapsed = mongoengine.BooleanField(default=False)
    column = mongoengine.IntField()
    order = mongoengine.IntField()

class PanelLayout(mongoengine.EmbeddedDocument):
    layout = mongoengine.MapField(mongoengine.EmbeddedDocumentField(Layout))
    
class Panels(mongoengine.EmbeddedDocument):
    active = mongoengine.MapField(mongoengine.EmbeddedDocumentField(Panel))
    layouts = mongoengine.MapField(mongoengine.EmbeddedDocumentField(PanelLayout))
    
    def get_panels(self):
        return map(panels.panels_pool.get_panel, self.active.keys())
    
    def get_all_panels(self):
        return panels.panels_pool.get_all_panels()
    
    def get_collapsed(self, number_of_columns):
        if number_of_columns in self.layouts:
            collapsed = [layout[1].collapsed for layout in self.layouts[number_of_columns].layout.iteritems()]
        else:
            collapsed = [False] * len(self.active.keys())
        
        return dict(zip(self.active.keys(), collapsed))
    
    def set_collapsed(self, number_of_columns, name, panel_collapsed):
        pl = PanelLayout()
        if number_of_columns in self.layouts:
            for panel in self.active:
                default = self.layouts[number_of_columns].layout[panel]
                
                pl.layout[panel] = Layout(
                       collapsed = panel_collapsed if panel == name else default.collapsed,
                       column = default.column,
                       order = default.order,
                       )
        else:
            for panel in self.active:
                pl.layout[panel] = Layout(collapsed=panel_collapsed if panel == name else False)
            
        self.layouts[number_of_columns] = pl
    
    def get_columns(self, number_of_columns):
        if not number_of_columns in self.layouts:
            return ''
        layout = self.layouts[number_of_columns].layout
        cols = dict()
        cols_order = dict()
        for key, panel in layout.iteritems():
            c = panel.column
            
            if c == None:
                continue
            if not c in cols:
                cols[c] = []
                cols_order[c] = []

            # Enforce ordering of panels in column, because layout is not ordered
            pos = bisect.bisect_left(cols_order[c], panel.order)
            cols[c].insert(pos, key)
            cols_order[c].insert(pos, panel.order)
        
        # If no order has been saved, return empty to force default ordering
        return cols if cols else ''
    
    def has_panel(self, panel_name):
        return panel_name in self.active
    
    def set_panels(self, panels, *args, **kwargs):
        # Preserve prior settings for kept panels
        for panel in self.active:
            if panel not in panels:
                for key in self.layouts:
                    del self.layouts[key].layout[panel]
        self.active = dict((k,v) for k,v in self.active.items() if k in panels)
        
        for panel in panels:
            if panel not in self.active:
                self.active[panel] = Panel()
        
        # If number of columns was passed as the first argument, we're only reordering a single layout
        if len(args):
            pl = PanelLayout()
            
            for panel in panels:
                # If properties were passed as dicts in kwargs use them, otherwise use existing or default
                pl.layout[panel] = Layout(
                   collapsed = kwargs['collapsed'][panel] if 'collapsed' in kwargs else
                       self.layouts[args[0]].layout[panel].collapsed if args[0] in self.layouts else False,
                   column = kwargs['column'][panel] if 'column' in kwargs else
                       self.layouts[args[0]].layout[panel].column if args[0] in self.layouts else None,
                   order = kwargs['order'][panel] if 'order' in kwargs else
                       self.layouts[args[0]].layout[panel].order if args[0] in self.layouts else None,
                   )
            
            self.layouts[args[0]] = pl
        # Otherwise, we have to restructure the entire set
        else:
            if self.layouts:
                for cols in self.layouts:
                    pl = PanelLayout()
                    
                    for panel in panels:
                        prior = self.layouts[cols].layout
                        pl.layout[panel] = Layout(
                           collapsed = prior[panel].collapsed if panel in prior else False,
                           column = prior[panel].column if panel in prior else None,
                           order = prior[panel].order if panel in prior else None,
                           )
                    
                    self.layouts[cols] = pl
            else:
                pl = PanelLayout()
                
                for panel in panels:
                    pl.layout[panel] = Layout()
                
                for i in range(5):
                    self.layouts[str(i)] = pl
    
    def reset_panels(self):
        for panel in panels.panels_pool.get_all_panels():
            self.active[panel.get_name()] = Panel()

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
    
    panels = mongoengine.EmbeddedDocumentField(Panels)
    
    def __init__(self, *args, **kwargs):
        super(User, self).__init__(*args, **kwargs)
        
        # If the user has not previously saved any panel data, make sure we have an object to query
        if self.panels == None:
            self.panels = Panels()
            self.panels.reset_panels()
            self.save

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
