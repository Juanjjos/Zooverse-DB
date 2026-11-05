from django.contrib import admin

from common.admin import SoftDeleteAdmin
from personal.models import Cuidador, CuidadoEspecie, Guia
from visitas.models import AsignacionGuia


class CuidadoEspecieInline(admin.TabularInline):
    model = CuidadoEspecie
    extra = 0
    autocomplete_fields = ["especie"]


class AsignacionGuiaInline(admin.TabularInline):
    model = AsignacionGuia
    extra = 0
    autocomplete_fields = ["itinerario"]


@admin.register(Guia)
class GuiaAdmin(SoftDeleteAdmin):
    list_display = ["nombre", "telefono", "fecha_inicio"]
    list_filter = ["fecha_inicio"]
    search_fields = ["nombre", "telefono", "direccion"]
    inlines = [AsignacionGuiaInline]


@admin.register(Cuidador)
class CuidadorAdmin(SoftDeleteAdmin):
    list_display = ["nombre", "telefono", "fecha_ingreso"]
    list_filter = ["fecha_ingreso"]
    search_fields = ["nombre", "telefono", "direccion"]
    inlines = [CuidadoEspecieInline]


@admin.register(CuidadoEspecie)
class CuidadoEspecieAdmin(SoftDeleteAdmin):
    list_display = ["cuidador", "especie", "fecha_inicio"]
    list_filter = ["fecha_inicio"]
    search_fields = [
        "cuidador__nombre",
        "especie__nombre_espanol",
        "especie__nombre_cientifico",
    ]
    autocomplete_fields = ["cuidador", "especie"]
