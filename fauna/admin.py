from django.contrib import admin

from common.admin import SoftDeleteAdmin
from fauna.models import Continente, Especie, Habitat, Zona
from operaciones.models import (
    Dieta,
    EntregaAlimento,
    Mantenimiento,
    RevisionVeterinaria,
    Vacuna,
)
from personal.models import CuidadoEspecie


class ContinentesInline(admin.TabularInline):
    model = Habitat.continentes.through
    extra = 1


class HabitatsInline(admin.TabularInline):
    model = Especie.habitats.through
    extra = 1


class CuidadosInline(admin.TabularInline):
    model = CuidadoEspecie
    extra = 0
    autocomplete_fields = ["cuidador"]


class RevisionesInline(admin.TabularInline):
    model = RevisionVeterinaria
    extra = 0
    fields = ["fecha", "diagnostico", "fecha_proxima_revision"]


class VacunasInline(admin.TabularInline):
    model = Vacuna
    extra = 0
    fields = ["nombre", "fecha_aplicacion", "fecha_proxima"]


class DietasInline(admin.TabularInline):
    model = Dieta
    extra = 0
    autocomplete_fields = ["tipo_alimento"]


class EntregasInline(admin.TabularInline):
    model = EntregaAlimento
    extra = 0
    autocomplete_fields = ["cuidador", "tipo_alimento"]


class MantenimientosZonaInline(admin.TabularInline):
    model = Mantenimiento
    fk_name = "zona"
    extra = 0
    fields = ["fecha", "descripcion", "fecha_proximo_mantenimiento"]


class MantenimientosHabitatInline(admin.TabularInline):
    model = Mantenimiento
    fk_name = "habitat"
    extra = 0
    fields = ["fecha", "descripcion", "fecha_proximo_mantenimiento"]


@admin.register(Continente)
class ContinenteAdmin(SoftDeleteAdmin):
    list_display = ["nombre"]
    search_fields = ["nombre"]
    inlines = [ContinentesInline]


@admin.register(Habitat)
class HabitatAdmin(SoftDeleteAdmin):
    list_display = ["nombre", "clima", "vegetacion"]
    list_filter = ["clima"]
    search_fields = ["nombre", "clima", "vegetacion"]
    filter_horizontal = ["continentes"]
    inlines = [MantenimientosHabitatInline]


@admin.register(Zona)
class ZonaAdmin(SoftDeleteAdmin):
    list_display = ["nombre", "extension_hectareas"]
    search_fields = ["nombre"]
    inlines = [MantenimientosZonaInline]


@admin.register(Especie)
class EspecieAdmin(SoftDeleteAdmin):
    list_display = ["nombre_espanol", "nombre_cientifico", "zona"]
    list_filter = ["zona", "habitats"]
    search_fields = ["nombre_espanol", "nombre_cientifico", "descripcion"]
    autocomplete_fields = ["zona"]
    filter_horizontal = ["habitats"]
    inlines = [
        CuidadosInline,
        RevisionesInline,
        VacunasInline,
        DietasInline,
        EntregasInline,
    ]
