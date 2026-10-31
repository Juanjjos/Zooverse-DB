from django.contrib import admin

from operaciones.models import (
    Dieta,
    EntregaAlimento,
    InventarioAlimento,
    Mantenimiento,
    RevisionVeterinaria,
    TipoAlimento,
    Vacuna,
)


@admin.register(RevisionVeterinaria)
class RevisionVeterinariaAdmin(admin.ModelAdmin):
    list_display = ["especie", "fecha", "fecha_proxima_revision"]
    list_filter = ["fecha", "fecha_proxima_revision"]
    search_fields = ["especie__nombre_espanol", "especie__nombre_cientifico"]
    autocomplete_fields = ["especie"]
    date_hierarchy = "fecha"


@admin.register(Vacuna)
class VacunaAdmin(admin.ModelAdmin):
    list_display = ["nombre", "especie", "fecha_aplicacion", "fecha_proxima"]
    list_filter = ["fecha_aplicacion", "fecha_proxima", "nombre"]
    search_fields = ["nombre", "especie__nombre_espanol"]
    autocomplete_fields = ["especie"]


@admin.register(TipoAlimento)
class TipoAlimentoAdmin(admin.ModelAdmin):
    list_display = ["nombre", "unidad"]
    list_filter = ["unidad"]
    search_fields = ["nombre"]


@admin.register(Dieta)
class DietaAdmin(admin.ModelAdmin):
    list_display = ["especie", "tipo_alimento", "cantidad_diaria"]
    list_filter = ["tipo_alimento"]
    search_fields = ["especie__nombre_espanol", "tipo_alimento__nombre"]
    autocomplete_fields = ["especie", "tipo_alimento"]


@admin.register(InventarioAlimento)
class InventarioAlimentoAdmin(admin.ModelAdmin):
    list_display = ["tipo_alimento", "cantidad_disponible", "umbral_minimo"]
    list_filter = ["tipo_alimento__unidad"]
    search_fields = ["tipo_alimento__nombre"]
    autocomplete_fields = ["tipo_alimento"]


@admin.register(EntregaAlimento)
class EntregaAlimentoAdmin(admin.ModelAdmin):
    list_display = ["fecha", "cuidador", "especie", "tipo_alimento", "cantidad"]
    list_filter = ["fecha", "tipo_alimento"]
    search_fields = [
        "cuidador__nombre",
        "especie__nombre_espanol",
        "tipo_alimento__nombre",
    ]
    autocomplete_fields = ["cuidador", "especie", "tipo_alimento"]
    date_hierarchy = "fecha"


@admin.register(Mantenimiento)
class MantenimientoAdmin(admin.ModelAdmin):
    list_display = [
        "fecha",
        "ubicacion",
        "fecha_proximo_mantenimiento",
        "descripcion",
    ]
    list_filter = ["fecha", "fecha_proximo_mantenimiento"]
    search_fields = ["descripcion", "zona__nombre", "habitat__nombre"]
    autocomplete_fields = ["zona", "habitat"]
    date_hierarchy = "fecha"

    @admin.display(description="ubicación")
    def ubicacion(self, obj):
        return obj.zona if obj.zona_id else obj.habitat
