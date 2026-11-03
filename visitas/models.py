from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone


class Itinerario(models.Model):
    codigo = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="código",
    )
    duracion_minutos = models.PositiveSmallIntegerField(
        verbose_name="duración (minutos)",
    )
    longitud_km = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name="longitud (km)",
    )
    cupo_maximo = models.PositiveIntegerField(verbose_name="cupo máximo")
    zonas = models.ManyToManyField(
        "fauna.Zona",
        related_name="itinerarios",
        verbose_name="zonas",
    )
    guias = models.ManyToManyField(
        "personal.Guia",
        through="AsignacionGuia",
        related_name="itinerarios",
        verbose_name="guías",
    )

    class Meta:
        verbose_name = "itinerario"
        verbose_name_plural = "itinerarios"
        ordering = ["codigo"]
        constraints = [
            models.CheckConstraint(
                condition=Q(duracion_minutos__gt=0),
                name="itinerario_duracion_mayor_cero",
            ),
            models.CheckConstraint(
                condition=Q(longitud_km__gt=0),
                name="itinerario_longitud_mayor_cero",
            ),
            models.CheckConstraint(
                condition=Q(cupo_maximo__gt=0),
                name="itinerario_cupo_mayor_cero",
            ),
        ]

    @property
    def num_especies_distintas(self):
        return self.zonas.aggregate(
            cantidad=Count("especies", distinct=True),
        )["cantidad"]

    def __str__(self):
        return self.codigo


class AsignacionGuia(models.Model):
    guia = models.ForeignKey(
        "personal.Guia",
        on_delete=models.PROTECT,
        related_name="asignaciones_itinerario",
        verbose_name="guía",
    )
    itinerario = models.ForeignKey(
        Itinerario,
        on_delete=models.CASCADE,
        related_name="asignaciones_guia",
        verbose_name="itinerario",
    )
    hora = models.TimeField(verbose_name="hora")

    class Meta:
        verbose_name = "asignación de guía"
        verbose_name_plural = "asignaciones de guías"
        ordering = ["itinerario", "hora"]
        constraints = [
            models.UniqueConstraint(
                fields=["itinerario", "hora"],
                name="asignacion_guia_unica_por_hora",
            ),
        ]

    def __str__(self):
        return f"{self.guia} - {self.itinerario} ({self.hora:%H:%M})"


class Boleto(models.Model):
    class Tipo(models.TextChoices):
        GENERAL = "general", "General"
        ESTUDIANTE = "estudiante", "Estudiante"
        NINO = "nino", "Niño"

    tipo = models.CharField(
        max_length=12,
        choices=Tipo.choices,
        verbose_name="tipo de boleto",
    )
    reserva = models.ForeignKey(
        "Reserva",
        on_delete=models.PROTECT,
        related_name="boletos",
        verbose_name="reserva asociada",
    )
    precio_pagado = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="precio pagado",
    )

    class Meta:
        verbose_name = "boleto"
        verbose_name_plural = "boletos"
        ordering = ["-reserva__fecha", "tipo"]
        constraints = [
            models.CheckConstraint(
                condition=Q(precio_pagado__gte=0),
                name="boleto_precio_no_negativo",
            ),
            models.CheckConstraint(
                condition=Q(tipo__in=["general", "estudiante", "nino"]),
                name="boleto_tipo_valido",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.reserva_id is None:
            raise ValidationError(
                {"reserva": "Cada boleto debe pertenecer a una reserva."}
            )
        if self.precio_pagado < 0:
            raise ValidationError(
                {"precio_pagado": "El precio pagado no puede ser negativo."}
            )

        with transaction.atomic():
            reserva_guardada_id = self.reserva_id
            update_fields = kwargs.get("update_fields")
            anterior = None
            if self.pk is not None:
                anterior = (
                    type(self).objects.select_for_update()
                    .filter(pk=self.pk)
                    .first()
                )
                if anterior is not None and update_fields is not None:
                    if "reserva" not in update_fields:
                        reserva_guardada_id = anterior.reserva_id

            reserva_asociada = (
                Reserva.objects.select_for_update()
                .get(pk=reserva_guardada_id)
            )

            boletos_asociados = type(self).objects.filter(
                reserva_id=reserva_guardada_id,
            )
            if self.pk is not None:
                boletos_asociados = boletos_asociados.exclude(pk=self.pk)
            if boletos_asociados.count() >= reserva_asociada.cantidad_personas:
                raise ValidationError(
                    {
                        "reserva": (
                            "La reserva ya tiene un boleto por cada persona."
                        )
                    }
                )

            super().save(*args, **kwargs)

    @property
    def itinerario(self):
        return self.reserva.itinerario

    @property
    def fecha(self):
        return self.reserva.fecha

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.itinerario} ({self.fecha})"


class Reserva(models.Model):
    itinerario = models.ForeignKey(
        Itinerario,
        on_delete=models.PROTECT,
        related_name="reservas",
        verbose_name="itinerario",
    )
    cantidad_personas = models.PositiveIntegerField(
        verbose_name="cantidad de personas",
    )
    fecha = models.DateField(
        default=timezone.localdate,
        verbose_name="fecha",
    )

    class Meta:
        verbose_name = "reserva"
        verbose_name_plural = "reservas"
        ordering = ["-fecha", "itinerario"]
        indexes = [
            models.Index(
                fields=["fecha", "itinerario"],
                name="res_fecha_itinerario_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(cantidad_personas__gt=0),
                name="reserva_cantidad_personas_positiva",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.cantidad_personas <= 0:
            raise ValidationError(
                {"cantidad_personas": "La cantidad de personas debe ser mayor que cero."}
            )

        with transaction.atomic():
            itinerario = (
                Itinerario.objects.select_for_update()
                .get(pk=self.itinerario_id)
            )
            fecha_reserva = self.fecha
            personas_reserva = self.cantidad_personas
            reserva_anterior = None
            update_fields = kwargs.get("update_fields")
            if self.pk is not None:
                reserva_anterior = (
                    type(self).objects.select_for_update()
                    .filter(pk=self.pk)
                    .first()
                )
                if reserva_anterior is not None and update_fields is not None:
                    if "fecha" not in update_fields:
                        fecha_reserva = reserva_anterior.fecha
                    if "cantidad_personas" not in update_fields:
                        personas_reserva = reserva_anterior.cantidad_personas

            boletos_asociados = Boleto.objects.filter(
                reserva_id=self.pk,
            ) if self.pk is not None else Boleto.objects.none()
            if boletos_asociados.count() > personas_reserva:
                raise ValidationError(
                    {
                        "cantidad_personas": (
                            "La cantidad no puede ser menor que los boletos ya "
                            "emitidos para esta reserva."
                        )
                    }
                )

            reservas_del_dia = type(self).objects.filter(
                itinerario_id=self.itinerario_id,
                fecha=fecha_reserva,
            )
            if self.pk is not None:
                reservas_del_dia = reservas_del_dia.exclude(pk=self.pk)

            personas_reservadas = reservas_del_dia.aggregate(
                total=Sum("cantidad_personas", default=0),
            )["total"]
            if personas_reservadas + personas_reserva > itinerario.cupo_maximo:
                raise ValidationError(
                    {
                        "cantidad_personas": (
                            "La reserva excede el cupo disponible del itinerario "
                            f"para {fecha_reserva}."
                        )
                    }
                )

            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.itinerario} - {self.cantidad_personas} personas ({self.fecha})"
