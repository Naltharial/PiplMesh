import random

from django.conf import settings
from django.contrib.webdesign import lorem_ipsum
from django.utils.translation import ugettext_lazy as _

from piplmesh import panels

class DummyTestPanel(panels.BasePanel):
    dependencies = ('dummy',)
    
    def get_context(self, context):
        context = super(DummyTestPanel, self).get_context(context)

        context.update({
            'header': _("Dummy test panel"),
            'content': '\n\n'.join(lorem_ipsum.paragraphs(random.randint(1, 1))),
        })
        return context

if settings.DEBUG:
    panels.panels_pool.register(DummyTestPanel)
