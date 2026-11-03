import django.db.models.deletion
from django.db import migrations, models


def restaurar_campos_derivados(apps, schema_editor):
    Boleto = apps.get_model("visitas", "Boleto")
    alias = schema_editor.connection.alias

    for boleto in (
        Boleto.objects.using(alias)
        .select_related("reserva")
        .order_by("pk")
        .iterator()
    ):
        Boleto.objects.using(alias).filter(pk=boleto.pk).update(
            itinerario_id=boleto.reserva.itinerario_id,
            fecha=boleto.reserva.fecha,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("visitas", "0004_normalizar_boletos"),
    ]

    operations = [
        migrations.RunPython(
            migrations.RunPython.noop,
            reverse_code=restaurar_campos_derivados,
        ),
        migrations.AlterField(
            model_name="boleto",
            name="reserva",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="boletos",
                to="visitas.reserva",
                verbose_name="reserva asociada",
            ),
        ),
        migrations.RemoveField(
            model_name="boleto",
            name="fecha",
        ),
        migrations.RemoveField(
            model_name="boleto",
            name="itinerario",
        ),
        migrations.AddIndex(
            model_name="reserva",
            index=models.Index(
                fields=["fecha", "itinerario"],
                name="res_fecha_itinerario_idx",
            ),
        ),
    ]
