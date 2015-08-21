from django.conf.urls import url
from . import views

urlpatterns = [
    # ex: /builder/ (default view)
    url(r'^$', views.index, name='builder-default'),
    # ex: /builder/na/game_id/user_id/ (default view filled with game data)
    url(r'^(?P<region>[a-z]+)/(?P<game_id>[0-9]+)/(?P<user_id>[0-9]+)/$', views.game_builder, name='builder-fromgame'),
    # ex: /builder/na/username/champion_id/ (create build from recent games with this champion)
    url(r'^(?P<region>[a-z]+)/(?P<username>[\w ]+)/(?P<champion>[a-zA-Z]+)/$', views.champ_builder, name='builder-fromchamp'),
    # ex: /builder/generate/ (generate json view)
    url(r'^generate/$', views.json_generate, name='builder-generate'),
    ]

