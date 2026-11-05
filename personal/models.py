from django.db import models

from common.models import SoftDeleteModel


class Guia(SoftDeleteModel):
    nombre = models.CharField(max_length=150, verbose_name="nombre")
    direccion = models.CharField(max_length=255, verbose_name="dirección")
    telefono = models.CharField(max_length=30, verbose_name="teléfono")
    fecha_inicio = models.DateField(verbose_name="fecha de inicio")

    class Meta:
        verbose_name = "guía"
        verbose_name_plural = "guías"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Cuidador(SoftDeleteModel):
    nombre = models.CharField(max_length=150, verbose_name="nombre")
    direccion = models.CharField(max_length=255, verbose_name="dirección")
    telefono = models.CharField(max_length=30, verbose_name="teléfono")
    fecha_ingreso = models.DateField(verbose_name="fecha de ingreso")

    class Meta:
        verbose_name = "cuidador"
        verbose_name_plural = "cuidadores"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class CuidadoEspecie(SoftDeleteModel):
    cuidador = models.ForeignKey(
        Cuidador,
        on_delete=models.PROTECT,
        related_name="cuidados_especies",
        verbose_name="cuidador",
    )
    especie = models.ForeignKey(
        "fauna.Especie",
        on_delete=models.PROTECT,
        related_name="cuidados",
        verbose_name="especie",
    )
    fecha_inicio = models.DateField(verbose_name="fecha de inicio")

    class Meta:
        verbose_name = "asignación de cuidado de especie"
        verbose_name_plural = "asignaciones de cuidado de especies"
        ordering = ["especie", "cuidador"]
        constraints = [
            models.UniqueConstraint(
                fields=["cuidador", "especie"],
                name="cuidado_especie_unico_por_cuidador",
            ),
        ]

    def __str__(self):
        return f"{self.cuidador} - {self.especie}"
