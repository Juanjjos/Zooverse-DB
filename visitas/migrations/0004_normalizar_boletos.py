from django.db import migrations


def asignar_reserva_a_boletos(apps, schema_editor):
    Boleto = apps.get_model("visitas", "Boleto")
    Reserva = apps.get_model("visitas", "Reserva")
    alias = schema_editor.connection.alias

    boletos = (
        Boleto.objects.using(alias)
        .select_related("reserva")
        .order_by("pk")
    )
    for boleto in boletos.iterator():
        if boleto.reserva_id is not None:
            if (
                boleto.reserva.itinerario_id != boleto.itinerario_id
                or boleto.reserva.fecha != boleto.fecha
            ):
                raise RuntimeError(
                    "No se puede normalizar el boleto "
                    f"{boleto.pk}: no coincide con su reserva."
                )
            continue

        reserva = Reserva.objects.using(alias).create(
            itinerario_id=boleto.itinerario_id,
            fecha=boleto.fecha,
            cantidad_personas=1,
        )
        Boleto.objects.using(alias).filter(pk=boleto.pk).update(
            reserva_id=reserva.pk
        )


class Migration(migrations.Migration):

    dependencies = [
        ("visitas", "0003_boleto_reserva_boleto_boleto_tipo_valido"),
    ]

    operations = [
        migrations.RunPython(
            asignar_reserva_a_boletos,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
