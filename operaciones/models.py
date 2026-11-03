from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.db.models.signals import pre_delete
from django.dispatch import receiver


class RevisionVeterinaria(models.Model):
    especie = models.ForeignKey(
        "fauna.Especie",
        on_delete=models.PROTECT,
        related_name="revisiones_veterinarias",
        db_index=False,
        verbose_name="especie",
    )
    fecha = models.DateField(verbose_name="fecha de revisión")
    diagnostico = models.TextField(verbose_name="diagnóstico")
    fecha_proxima_revision = models.DateField(
        null=True,
        blank=True,
        verbose_name="fecha de próxima revisión",
    )

    class Meta:
        verbose_name = "revisión veterinaria"
        verbose_name_plural = "revisiones veterinarias"
        ordering = ["-fecha"]
        indexes = [
            models.Index(fields=["fecha"], name="revision_fecha_idx"),
            models.Index(
                fields=["especie", "fecha"],
                name="revision_especie_fecha_idx",
            ),
            models.Index(
                fields=["fecha_proxima_revision"],
                name="revision_proxima_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(fecha_proxima_revision__isnull=True)
                    | Q(fecha_proxima_revision__gt=models.F("fecha"))
                ),
                name="revision_fecha_proxima_valida",
            ),
        ]

    def __str__(self):
        return f"Revisión de {self.especie} ({self.fecha})"


class Vacuna(models.Model):
    especie = models.ForeignKey(
        "fauna.Especie",
        on_delete=models.PROTECT,
        related_name="vacunas",
        db_index=False,
        verbose_name="especie",
    )
    nombre = models.CharField(max_length=120, verbose_name="nombre")
    fecha_aplicacion = models.DateField(verbose_name="fecha de aplicación")
    fecha_proxima = models.DateField(verbose_name="fecha próxima")

    class Meta:
        verbose_name = "vacuna"
        verbose_name_plural = "vacunas"
        ordering = ["fecha_proxima"]
        indexes = [
            models.Index(fields=["fecha_proxima"], name="vacuna_proxima_idx"),
            models.Index(
                fields=["especie", "fecha_aplicacion"],
                name="vacuna_especie_fecha_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(fecha_proxima__gt=models.F("fecha_aplicacion")),
                name="vacuna_fecha_proxima_valida",
            ),
        ]

    def __str__(self):
        return f"{self.nombre} - {self.especie}"


class TipoAlimento(models.Model):
    class Unidad(models.TextChoices):
        KILOGRAMO = "kg", "Kilogramo"
        GRAMO = "g", "Gramo"
        LITRO = "l", "Litro"
        MILILITRO = "ml", "Mililitro"
        UNIDAD = "ud", "Unidad"

    nombre = models.CharField(max_length=120, unique=True, verbose_name="nombre")
    unidad = models.CharField(
        max_length=2,
        choices=Unidad.choices,
        verbose_name="unidad de medida",
    )

    class Meta:
        verbose_name = "tipo de alimento"
        verbose_name_plural = "tipos de alimento"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.get_unidad_display()})"


class Dieta(models.Model):
    especie = models.ForeignKey(
        "fauna.Especie",
        on_delete=models.PROTECT,
        related_name="dietas",
        verbose_name="especie",
    )
    tipo_alimento = models.ForeignKey(
        TipoAlimento,
        on_delete=models.PROTECT,
        related_name="dietas",
        verbose_name="tipo de alimento",
    )
    cantidad_diaria = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        verbose_name="cantidad diaria",
    )

    class Meta:
        verbose_name = "dieta"
        verbose_name_plural = "dietas"
        ordering = ["especie", "tipo_alimento"]
        constraints = [
            models.UniqueConstraint(
                fields=["especie", "tipo_alimento"],
                name="dieta_especie_alimento_unica",
            ),
            models.CheckConstraint(
                condition=Q(cantidad_diaria__gt=0),
                name="dieta_cantidad_diaria_positiva",
            ),
        ]

    def __str__(self):
        return f"{self.especie} - {self.tipo_alimento}"


class InventarioAlimento(models.Model):
    tipo_alimento = models.OneToOneField(
        TipoAlimento,
        on_delete=models.PROTECT,
        related_name="inventario",
        verbose_name="tipo de alimento",
    )
    cantidad_disponible = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal("0"),
        verbose_name="cantidad disponible",
    )
    umbral_minimo = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal("0"),
        verbose_name="umbral mínimo",
    )

    class Meta:
        verbose_name = "inventario de alimento"
        verbose_name_plural = "inventarios de alimento"
        ordering = ["tipo_alimento"]
        constraints = [
            models.CheckConstraint(
                condition=Q(cantidad_disponible__gte=0),
                name="inventario_cantidad_no_negativa",
            ),
            models.CheckConstraint(
                condition=Q(umbral_minimo__gte=0),
                name="inventario_umbral_no_negativo",
            ),
        ]

    def __str__(self):
        return f"{self.tipo_alimento}: {self.cantidad_disponible}"


class EntregaAlimento(models.Model):
    cuidador = models.ForeignKey(
        "personal.Cuidador",
        on_delete=models.PROTECT,
        related_name="entregas_alimento",
        verbose_name="cuidador",
    )
    especie = models.ForeignKey(
        "fauna.Especie",
        on_delete=models.PROTECT,
        related_name="entregas_alimento",
        verbose_name="especie",
    )
    tipo_alimento = models.ForeignKey(
        TipoAlimento,
        on_delete=models.PROTECT,
        related_name="entregas",
        verbose_name="tipo de alimento",
    )
    cantidad = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        verbose_name="cantidad",
    )
    fecha = models.DateField(verbose_name="fecha")

    class Meta:
        verbose_name = "entrega de alimento"
        verbose_name_plural = "entregas de alimento"
        ordering = ["-fecha"]
        indexes = [
            models.Index(
                fields=["fecha", "especie"],
                name="entrega_fecha_especie_idx",
            ),
            models.Index(
                fields=["fecha", "tipo_alimento"],
                name="entrega_fecha_tipo_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(cantidad__gt=0),
                name="entrega_cantidad_positiva",
            ),
        ]

    def __str__(self):
        return f"{self.especie} - {self.tipo_alimento} ({self.cantidad})"

    def save(self, *args, **kwargs):
        update_fields = kwargs.get("update_fields")
        with transaction.atomic():
            anterior = None
            if self.pk is not None:
                anterior = (
                    type(self).objects.select_for_update().filter(pk=self.pk).first()
                )

            tipo_anterior_id = anterior.tipo_alimento_id if anterior else None
            cantidad_anterior = anterior.cantidad if anterior else Decimal("0")
            tipo_guardado_id = self.tipo_alimento_id
            cantidad_guardada = self.cantidad

            if anterior is not None and update_fields is not None:
                if "tipo_alimento" not in update_fields:
                    tipo_guardado_id = anterior.tipo_alimento_id
                if "cantidad" not in update_fields:
                    cantidad_guardada = anterior.cantidad

            consumos_por_tipo = {}
            if tipo_anterior_id is not None:
                consumos_por_tipo[tipo_anterior_id] = -cantidad_anterior
            consumos_por_tipo[tipo_guardado_id] = (
                consumos_por_tipo.get(tipo_guardado_id, Decimal("0"))
                + cantidad_guardada
            )

            inventarios = {
                inventario.tipo_alimento_id: inventario
                for inventario in InventarioAlimento.objects.select_for_update()
                .filter(tipo_alimento_id__in=consumos_por_tipo)
                .order_by("tipo_alimento_id")
            }

            for tipo_id, consumo in consumos_por_tipo.items():
                if consumo == 0:
                    continue
                inventario = inventarios.get(tipo_id)
                if inventario is None:
                    raise ValidationError(
                        "Debe existir un inventario para cada tipo de alimento "
                        "entregado."
                    )
                nueva_cantidad = inventario.cantidad_disponible - consumo
                if nueva_cantidad < 0:
                    raise ValidationError(
                        f"Inventario insuficiente de {inventario.tipo_alimento}."
                    )
                inventario.cantidad_disponible = nueva_cantidad
                inventario.save(update_fields=["cantidad_disponible"])

            super().save(*args, **kwargs)


@receiver(pre_delete, sender=EntregaAlimento)
def restablecer_inventario_al_eliminar_entrega(sender, instance, **kwargs):
    with transaction.atomic():
        inventario = (
            InventarioAlimento.objects.select_for_update()
            .filter(tipo_alimento_id=instance.tipo_alimento_id)
            .first()
        )
        if inventario is None:
            raise ValidationError(
                "No se puede eliminar la entrega porque no existe su inventario."
            )
        inventario.cantidad_disponible += instance.cantidad
        inventario.save(update_fields=["cantidad_disponible"])


class Mantenimiento(models.Model):
    zona = models.ForeignKey(
        "fauna.Zona",
        on_delete=models.PROTECT,
        related_name="mantenimientos",
        null=True,
        blank=True,
        verbose_name="zona",
    )
    habitat = models.ForeignKey(
        "fauna.Habitat",
        on_delete=models.PROTECT,
        related_name="mantenimientos",
        null=True,
        blank=True,
        verbose_name="hábitat",
    )
    fecha = models.DateField(verbose_name="fecha")
    descripcion = models.TextField(verbose_name="descripción")
    fecha_proximo_mantenimiento = models.DateField(
        null=True,
        blank=True,
        verbose_name="fecha del próximo mantenimiento",
    )

    class Meta:
        verbose_name = "mantenimiento"
        verbose_name_plural = "mantenimientos"
        ordering = ["-fecha"]
        indexes = [
            models.Index(
                fields=["fecha_proximo_mantenimiento"],
                name="mantenim_proximo_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(zona__isnull=False, habitat__isnull=True)
                    | Q(zona__isnull=True, habitat__isnull=False)
                ),
                name="mantenimiento_una_ubicacion",
            ),
            models.CheckConstraint(
                condition=(
                    Q(fecha_proximo_mantenimiento__isnull=True)
                    | Q(fecha_proximo_mantenimiento__gt=models.F("fecha"))
                ),
                name="mantenimiento_fecha_proxima_valida",
            ),
        ]

    def __str__(self):
        ubicacion = self.zona if self.zona_id else self.habitat
        return f"Mantenimiento de {ubicacion} ({self.fecha})"
