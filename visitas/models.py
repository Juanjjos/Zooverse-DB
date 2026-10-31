from django.db import models
from django.db.models import Count, Q


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
