from django.contrib import admin

from visitas.models import (
    AsignacionGuia,
    Boleto,
    Itinerario,
    Reserva,
)


class AsignacionGuiaInline(admin.TabularInline):
    model = AsignacionGuia
    extra = 0
    autocomplete_fields = ["guia"]


class BoletoInline(admin.TabularInline):
    model = Boleto
    extra = 0
    autocomplete_fields = ["reserva"]


class ReservaInline(admin.TabularInline):
    model = Reserva
    extra = 0


@admin.register(Itinerario)
class ItinerarioAdmin(admin.ModelAdmin):
    list_display = [
        "codigo",
        "duracion_minutos",
        "longitud_km",
        "cupo_maximo",
        "num_especies_distintas",
    ]
    search_fields = ["codigo"]
    filter_horizontal = ["zonas"]
    readonly_fields = ["num_especies_distintas"]
    inlines = [AsignacionGuiaInline, ReservaInline, BoletoInline]


@admin.register(AsignacionGuia)
class AsignacionGuiaAdmin(admin.ModelAdmin):
    list_display = ["itinerario", "guia", "hora"]
    list_filter = ["itinerario"]
    search_fields = ["itinerario__codigo", "guia__nombre"]
    autocomplete_fields = ["guia", "itinerario"]


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ["itinerario", "cantidad_personas", "fecha"]
    list_filter = ["fecha", "itinerario"]
    search_fields = ["itinerario__codigo"]
    autocomplete_fields = ["itinerario"]


@admin.register(Boleto)
class BoletoAdmin(admin.ModelAdmin):
    list_display = ["tipo", "itinerario", "fecha", "precio_pagado", "reserva"]
    list_filter = ["tipo", "fecha", "itinerario"]
    search_fields = ["itinerario__codigo"]
    autocomplete_fields = ["itinerario", "reserva"]
