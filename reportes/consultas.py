from collections import defaultdict
from decimal import Decimal

from django.db.models import Count, F, Sum
from django.db.models.functions import TruncMonth

from fauna.models import Especie
from operaciones.models import EntregaAlimento, RevisionVeterinaria, Vacuna
from visitas.models import Boleto, Reserva


def _filtrar_periodo(consulta, campo_fecha, fecha_inicio, fecha_fin):
    if fecha_inicio:
        consulta = consulta.filter(**{f"{campo_fecha}__gte": fecha_inicio})
    if fecha_fin:
        consulta = consulta.filter(**{f"{campo_fecha}__lte": fecha_fin})
    return consulta


def especies_por_zona_y_habitat():
    return (
        Especie.objects.select_related("zona")
        .prefetch_related("habitats")
        .order_by("zona__nombre", "nombre_espanol")
    )


def itinerarios_mas_solicitados(fecha_inicio=None, fecha_fin=None):
    reservas = _filtrar_periodo(
        Reserva.objects.all(),
        "fecha",
        fecha_inicio,
        fecha_fin,
    )
    return (
        reservas.values("itinerario__codigo")
        .annotate(
            cantidad_reservas=Count("id"),
            personas_reservadas=Sum("cantidad_personas"),
        )
        .order_by("-personas_reservadas", "-cantidad_reservas", "itinerario__codigo")
    )


def ingresos_por_boletos(fecha_inicio=None, fecha_fin=None):
    boletos = _filtrar_periodo(
        Boleto.objects.all(),
        "fecha",
        fecha_inicio,
        fecha_fin,
    )
    por_dia = (
        boletos.values("fecha")
        .annotate(cantidad=Count("id"), ingresos=Sum("precio_pagado"))
        .order_by("-fecha")
    )
    por_mes = (
        boletos.annotate(mes=TruncMonth("fecha"))
        .values("mes")
        .annotate(cantidad=Count("id"), ingresos=Sum("precio_pagado"))
        .order_by("-mes")
    )
    por_tipo = (
        boletos.values("tipo")
        .annotate(cantidad=Count("id"), ingresos=Sum("precio_pagado"))
        .order_by("tipo")
    )
    nombres_tipo = dict(Boleto.Tipo.choices)
    return {
        "por_dia": por_dia,
        "por_mes": por_mes,
        "por_tipo": [
            {**fila, "tipo_display": nombres_tipo[fila["tipo"]]}
            for fila in por_tipo
        ],
    }


def historial_medico(especie_id=None):
    revisiones = RevisionVeterinaria.objects.select_related("especie")
    vacunas = Vacuna.objects.select_related("especie")
    if especie_id:
        revisiones = revisiones.filter(especie_id=especie_id)
        vacunas = vacunas.filter(especie_id=especie_id)

    historial = [
        {
            "fecha": revision.fecha,
            "especie": revision.especie.nombre_espanol,
            "tipo": "Revisión veterinaria",
            "detalle": revision.diagnostico,
            "fecha_proxima": revision.fecha_proxima_revision,
        }
        for revision in revisiones
    ]
    historial.extend(
        {
            "fecha": vacuna.fecha_aplicacion,
            "especie": vacuna.especie.nombre_espanol,
            "tipo": "Vacuna",
            "detalle": vacuna.nombre,
            "fecha_proxima": vacuna.fecha_proxima,
        }
        for vacuna in vacunas
    )
    return sorted(historial, key=lambda evento: (evento["fecha"], evento["especie"]), reverse=True)


def consumo_alimento_por_especie(fecha_inicio=None, fecha_fin=None):
    entregas = _filtrar_periodo(
        EntregaAlimento.objects.all(),
        "fecha",
        fecha_inicio,
        fecha_fin,
    )
    return (
        entregas.values(
            "especie__nombre_espanol",
            "tipo_alimento__nombre",
            "tipo_alimento__unidad",
        )
        .annotate(cantidad_consumida=Sum("cantidad"))
        .order_by("especie__nombre_espanol", "tipo_alimento__nombre")
    )


def ocupacion_promedio_itinerarios(fecha_inicio=None, fecha_fin=None):
    reservas = _filtrar_periodo(
        Reserva.objects.all(),
        "fecha",
        fecha_inicio,
        fecha_fin,
    )
    reservas_diarias = (
        reservas.values(
            "itinerario_id",
            "itinerario__codigo",
            "itinerario__cupo_maximo",
            "fecha",
        )
        .annotate(personas=Sum("cantidad_personas"))
        .order_by("itinerario__codigo", "fecha")
    )

    porcentajes = []
    ocupacion_por_itinerario = defaultdict(list)
    for fila in reservas_diarias:
        porcentaje = fila["personas"] * 100 / fila["itinerario__cupo_maximo"]
        porcentajes.append(porcentaje)
        ocupacion_por_itinerario[fila["itinerario__codigo"]].append(porcentaje)

    por_itinerario = [
        {
            "codigo": codigo,
            "promedio_porcentaje": sum(valores) / len(valores),
            "dias_con_reservas": len(valores),
        }
        for codigo, valores in ocupacion_por_itinerario.items()
    ]
    por_itinerario.sort(key=lambda fila: (-fila["promedio_porcentaje"], fila["codigo"]))
    promedio_general = sum(porcentajes) / len(porcentajes) if porcentajes else None
    return {
        "por_itinerario": por_itinerario,
        "promedio_general": promedio_general,
    }


def especie_con_mas_revisiones(fecha_inicio=None, fecha_fin=None):
    revisiones = _filtrar_periodo(
        RevisionVeterinaria.objects.all(),
        "fecha",
        fecha_inicio,
        fecha_fin,
    )
    return (
        revisiones.values("especie__nombre_espanol")
        .annotate(cantidad=Count("id"))
        .order_by("-cantidad", "especie__nombre_espanol")
        .first()
    )


def alimentos_mas_consumidos(fecha_inicio=None, fecha_fin=None):
    entregas = _filtrar_periodo(
        EntregaAlimento.objects.all(),
        "fecha",
        fecha_inicio,
        fecha_fin,
    )
    consumos = list(
        entregas.values("tipo_alimento__nombre", "tipo_alimento__unidad")
        .annotate(cantidad_consumida=Sum("cantidad"))
        .order_by("tipo_alimento__nombre")
    )
    conversiones = {
        "kg": ("masa", "kg", Decimal("1")),
        "g": ("masa", "kg", Decimal("0.001")),
        "l": ("volumen", "l", Decimal("1")),
        "ml": ("volumen", "l", Decimal("0.001")),
        "ud": ("unidades", "ud", Decimal("1")),
    }
    mayores_por_dimension = {}
    for consumo in consumos:
        dimension, unidad, factor = conversiones[consumo["tipo_alimento__unidad"]]
        cantidad_normalizada = consumo["cantidad_consumida"] * factor
        registro = {
            "tipo_alimento__nombre": consumo["tipo_alimento__nombre"],
            "tipo_alimento__unidad": consumo["tipo_alimento__unidad"],
            "dimension": dimension,
            "unidad_normalizada": unidad,
            "cantidad_normalizada": cantidad_normalizada,
        }
        anterior = mayores_por_dimension.get(dimension)
        if anterior is None or cantidad_normalizada > anterior["cantidad_normalizada"]:
            mayores_por_dimension[dimension] = registro
    return {
        "totales": consumos,
        "mayores_por_dimension": list(mayores_por_dimension.values()),
    }


def construir_datos_reportes(fecha_inicio=None, fecha_fin=None, especie_id=None):
    ocupacion = ocupacion_promedio_itinerarios(fecha_inicio, fecha_fin)
    alimentos = alimentos_mas_consumidos(fecha_inicio, fecha_fin)
    return {
        "especies": especies_por_zona_y_habitat(),
        "itinerarios_solicitados": itinerarios_mas_solicitados(
            fecha_inicio,
            fecha_fin,
        ),
        "ingresos": ingresos_por_boletos(fecha_inicio, fecha_fin),
        "historial_medico": historial_medico(especie_id),
        "consumo_alimento": consumo_alimento_por_especie(
            fecha_inicio,
            fecha_fin,
        ),
        "ocupacion": ocupacion,
        "especie_mas_revisiones": especie_con_mas_revisiones(
            fecha_inicio,
            fecha_fin,
        ),
        "alimentos_mas_consumidos": alimentos["totales"],
        "alimento_mas_consumido": alimentos["mayores_por_dimension"],
    }
