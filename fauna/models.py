from django.db import models
from django.db.models import Q

from common.models import SoftDeleteModel


class Continente(SoftDeleteModel):
    nombre = models.CharField(
        max_length=80,
        unique=True,
        verbose_name="nombre",
    )

    class Meta:
        verbose_name = "continente"
        verbose_name_plural = "continentes"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Habitat(SoftDeleteModel):
    nombre = models.CharField(max_length=120, verbose_name="nombre")
    clima = models.CharField(max_length=100, verbose_name="clima")
    vegetacion = models.CharField(max_length=150, verbose_name="vegetación")
    continentes = models.ManyToManyField(
        Continente,
        related_name="habitats",
        verbose_name="continentes",
    )

    class Meta:
        verbose_name = "hábitat"
        verbose_name_plural = "hábitats"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Zona(SoftDeleteModel):
    nombre = models.CharField(max_length=120, verbose_name="nombre")
    extension_hectareas = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="extensión (hectáreas)",
    )

    class Meta:
        verbose_name = "zona"
        verbose_name_plural = "zonas"
        ordering = ["nombre"]
        constraints = [
            models.CheckConstraint(
                condition=Q(extension_hectareas__gt=0),
                name="zona_extension_mayor_cero",
            ),
        ]

    def __str__(self):
        return self.nombre


class Especie(SoftDeleteModel):
    nombre_espanol = models.CharField(
        max_length=120,
        verbose_name="nombre en español",
    )
    nombre_cientifico = models.CharField(
        max_length=180,
        unique=True,
        verbose_name="nombre científico",
    )
    descripcion = models.TextField(verbose_name="descripción")
    zona = models.ForeignKey(
        Zona,
        on_delete=models.PROTECT,
        related_name="especies",
        verbose_name="zona",
    )
    habitats = models.ManyToManyField(
        Habitat,
        related_name="especies",
        verbose_name="hábitats",
    )

    class Meta:
        verbose_name = "especie"
        verbose_name_plural = "especies"
        ordering = ["nombre_espanol"]

    def __str__(self):
        return f"{self.nombre_espanol} ({self.nombre_cientifico})"
