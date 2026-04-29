from django.shortcuts import render
from django.shortcuts import redirect


def no_access_view(request):
    return render(request, 'errors/no_access.html')


def handler403(request, exception=None):
    return redirect('/no-access/?code=403')


def handler404(request, exception=None):
    return redirect('/no-access/?code=404')