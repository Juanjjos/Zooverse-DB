from django.db import models, transaction
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        eliminados = 0
        conteo_por_modelo = {}
        with transaction.atomic(using=self.db):
            for objeto in self.iterator():
                cantidad, _ = objeto.delete()
                eliminados += cantidad
                if not cantidad:
                    continue
                etiqueta = (
                    objeto._meta.label,
                    objeto._meta.verbose_name_plural,
                )
                conteo_por_modelo[etiqueta] = (
                    conteo_por_modelo.get(etiqueta, 0) + 1
                )

        return eliminados, {
            f"{etiqueta[0]}": cantidad
            for etiqueta, cantidad in conteo_por_modelo.items()
        }

    def restore(self):
        restaurados = 0
        with transaction.atomic(using=self.db):
            for objeto in self.filter(eliminado=True).iterator():
                restaurados += objeto.restore()
        return restaurados


class AllObjectsManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    use_in_migrations = True


class ActiveObjectsManager(AllObjectsManager):
    use_in_migrations = True

    def get_queryset(self):
        return super().get_queryset().filter(eliminado=False)


class SoftDeleteModel(models.Model):
    eliminado = models.BooleanField(
        default=False,
        editable=False,
        verbose_name="eliminado",
    )
    fecha_eliminacion = models.DateTimeField(
        null=True,
        blank=True,
        editable=False,
        verbose_name="fecha de eliminación",
    )

    objects = ActiveObjectsManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True
        default_manager_name = "objects"
        base_manager_name = "all_objects"

    def before_soft_delete(self):
        pass

    def before_restore(self):
        pass

    def delete(self, using=None, keep_parents=False):
        if self.pk is None:
            return 0, {}

        db = using or self._state.db
        with transaction.atomic(using=db):
            objeto_actual = (
                type(self).all_objects.using(db)
                .select_for_update()
                .filter(pk=self.pk)
                .first()
            )
            if objeto_actual is None or objeto_actual.eliminado:
                return 0, {}

            objeto_actual.before_soft_delete()
            fecha_eliminacion = timezone.now()
            updated = type(self).all_objects.using(db).filter(pk=self.pk).update(
                eliminado=True,
                fecha_eliminacion=fecha_eliminacion,
            )
            if updated:
                self.eliminado = True
                self.fecha_eliminacion = fecha_eliminacion

        return updated, {self._meta.label: updated} if updated else {}

    def restore(self, using=None):
        if self.pk is None or not self.eliminado:
            return 0

        db = using or self._state.db
        with transaction.atomic(using=db):
            objeto_actual = (
                type(self).all_objects.using(db)
                .select_for_update()
                .filter(pk=self.pk)
                .first()
            )
            if objeto_actual is None or not objeto_actual.eliminado:
                return 0

            objeto_actual.before_restore()
            updated = type(self).all_objects.using(db).filter(pk=self.pk).update(
                eliminado=False,
                fecha_eliminacion=None,
            )
        if updated:
            self.eliminado = False
            self.fecha_eliminacion = None
        return updated
