from django.shortcuts import render
from django.views.decorators.cache import cache_page
from .models import dd_version


# cache the landing page daily
@cache_page(60 * 60 * 24)
def index(request):
    context = {'version': dd_version}
    return render(request, 'search/index.html', context)