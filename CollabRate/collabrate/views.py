from django.shortcuts import render, redirect


def index(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, "collabrate/index.html")

def login(request):
    return render(request, "collabrate/login.html")