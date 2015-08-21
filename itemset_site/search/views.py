from django.shortcuts import render


def index(request):
    context = {'version': '5.15.1'}
    return render(request, 'search/index.html', context)