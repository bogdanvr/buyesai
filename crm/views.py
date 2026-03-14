from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render


@staff_member_required
def crm_dashboard(request):
    return render(request, "crm.html")
