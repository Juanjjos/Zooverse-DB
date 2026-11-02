from datetime import timedelta

from django.db.models import Count, F, Sum
from django.utils import timezone

from operaciones.models import InventarioAlimento, Mantenimiento, RevisionVeterinaria, Vacuna
from visitas.models import Boleto, Itinerario, Reserva


def obtener_alertas(hoy=None):
    hoy = hoy or timezone.localdate()
    limite_vacunas = hoy + timedelta(days=15)

    vacunas = list(
        Vacuna.objects.select_related("especie")
        .filter(fecha_proxima__lte=limite_vacunas)
        .order_by("fecha_proxima", "especie__nombre_espanol")
    )
    revisiones_pendientes = list(
        RevisionVeterinaria.objects.select_related("especie")
        .filter(fecha_proxima_revision__lte=hoy)
        .order_by("fecha_proxima_revision", "especie__nombre_espanol")
    )
    inventarios_bajos = list(
        InventarioAlimento.objects.select_related("tipo_alimento")
        .filter(cantidad_disponible__lt=F("umbral_minimo"))
        .order_by("tipo_alimento__nombre")
    )
    mantenimientos_vencidos = list(
        Mantenimiento.objects.select_related("zona", "habitat")
        .filter(fecha_proximo_mantenimiento__lte=hoy)
        .order_by("fecha_proximo_mantenimiento")
    )

    personas_por_reserva = dict(
        Reserva.objects.filter(fecha=hoy)
        .values("itinerario_id")
        .annotate(total=Sum("cantidad_personas"))
        .values_list("itinerario_id", "total")
    )
    boletos_sin_reserva_por_itinerario = dict(
        Boleto.objects.filter(fecha=hoy, reserva__isnull=True)
        .values("itinerario_id")
        .annotate(total=Count("id"))
        .values_list("itinerario_id", "total")
    )
    itinerarios_llenos = []
    for itinerario in Itinerario.objects.order_by("codigo"):
        personas = personas_por_reserva.get(itinerario.pk, 0)
        boletos_sin_reserva = boletos_sin_reserva_por_itinerario.get(
            itinerario.pk,
            0,
        )
        ocupacion = personas + boletos_sin_reserva
        if ocupacion >= itinerario.cupo_maximo:
            itinerarios_llenos.append(
                {
                    "itinerario": itinerario,
                    "personas": ocupacion,
                    "cupo_maximo": itinerario.cupo_maximo,
                }
            )

    return {
        "hoy": hoy,
        "vacunas": vacunas,
        "revisiones_pendientes": revisiones_pendientes,
        "inventarios_bajos": inventarios_bajos,
        "mantenimientos_vencidos": mantenimientos_vencidos,
        "itinerarios_llenos": itinerarios_llenos,
    }
