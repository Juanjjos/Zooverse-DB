from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render

from reportes.consultas import construir_datos_reportes
from reportes.forms import FiltroReportesForm


@login_required(login_url="/admin/login/")
def inicio(request):
    if not (
        request.user.is_superuser
        or request.user.groups.filter(name="Administrador").exists()
    ):
        raise PermissionDenied

    formulario = FiltroReportesForm(request.GET if request.GET else {})
    datos_reportes = {}
    if formulario.is_valid():
        filtros = formulario.cleaned_data
        datos_reportes = construir_datos_reportes(
            fecha_inicio=filtros["fecha_inicio"],
            fecha_fin=filtros["fecha_fin"],
            especie_id=filtros["especie"].pk if filtros["especie"] else None,
        )

    return render(
        request,
        "reportes/inicio.html",
        {
            "formulario": formulario,
            "datos_reportes": datos_reportes,
        },
    )
