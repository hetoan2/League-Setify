from django.conf.urls import url
from . import views

urlpatterns = [
    # ex: /games/username/
    url(r'^(?P<region>[a-z]+)/(?P<username>[\w ]+)/$', views.results, name='games-results'),
    # ex: /games/username/champion_id/
    url(r'^(?P<region>[a-z]+)/(?P<username>[\w ]+)/(?P<champion>[a-zA-Z]+)/$', views.champ_results, name='games-champ_results'),
    ]

