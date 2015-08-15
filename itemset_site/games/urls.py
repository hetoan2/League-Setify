from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    # ex: /games/musouka/
    url(r'^(?P<username>[\w]+)/$', views.results, name='results'),
    # ex: /games/musouka/Lulu/
    url(r'^(?P<username>[\w]+)/(?P<champion>[a-zA-Z]+)/$', views.champ_results, name='champ_results'),
    # # ex: /polls/5/vote/
    # url(r'^(?P<question_id>[0-9]+)/vote/$', views.vote, name='vote'),
    ]

