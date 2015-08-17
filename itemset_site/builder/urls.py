from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    # ex: /builder/na/game_id/
    url(r'^(?P<region>[a-z]+)/(?P<game_id>[0-9]+)/(?P<user_id>[0-9]+)/$', views.game_builder, name='results'),
    ]

