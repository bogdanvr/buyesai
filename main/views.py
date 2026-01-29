from django.shortcuts import render


def mainview(request):
    # request_context = RequestContext(request.get_host)
    return render(request, 'index.html')