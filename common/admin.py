from django.contrib import admin, messages
from django.contrib.admin import SimpleListFilter
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class EstadoRegistroFilter(SimpleListFilter):
    title = _("estado del registro")
    parameter_name = "estado_registro"

    def lookups(self, request, model_admin):
        return (
            ("activos", _("Activos")),
            ("eliminados", _("Eliminados")),
            ("todos", _("Todos")),
        )

    def queryset(self, request, queryset):
        if self.value() == "eliminados":
            return queryset.filter(eliminado=True)
        if self.value() == "todos":
            return queryset
        return queryset.filter(eliminado=False)


class SoftDeleteAdmin(admin.ModelAdmin):
    actions = ["marcar_eliminados", "restaurar_registros"]

    def get_actions(self, request):
        actions = super().get_actions(request)
        estado = request.GET.get("estado_registro")
        if estado != "eliminados":
            actions.pop("restaurar_registros", None)
        if estado == "eliminados":
            actions.pop("marcar_eliminados", None)
        return actions

    def get_queryset(self, request):
        queryset = self.model.all_objects.all()
        estado = request.GET.get("estado_registro")
        if estado == "eliminados":
            return queryset.filter(eliminado=True)
        if estado == "todos":
            return queryset
        return queryset.filter(eliminado=False)

    def get_list_filter(self, request):
        filtros = list(super().get_list_filter(request))
        if EstadoRegistroFilter not in filtros:
            filtros.append(EstadoRegistroFilter)
        return filtros

    def get_list_display(self, request):
        columnas = list(super().get_list_display(request))
        if "estado_registro_display" not in columnas:
            columnas.append("estado_registro_display")
        if "fecha_eliminacion" not in columnas:
            columnas.append("fecha_eliminacion")
        return columnas

    @admin.display(description=_("estado"), boolean=False)
    def estado_registro_display(self, obj):
        return _("Eliminado") if obj.eliminado else _("Activo")

    @admin.action(description=_("Marcar registros seleccionados como eliminados"))
    def marcar_eliminados(self, request, queryset):
        cantidad, _ = queryset.delete()
        self.message_user(
            request,
            _("Se marcaron %(cantidad)s registros como eliminados.")
            % {"cantidad": cantidad},
            messages.SUCCESS,
        )

    @admin.action(description=_("Restaurar registros seleccionados"))
    def restaurar_registros(self, request, queryset):
        try:
            cantidad = queryset.restore()
        except ValidationError as error:
            self.message_user(
                request,
                " ".join(error.messages),
                messages.ERROR,
            )
            return
        self.message_user(
            request,
            _("Se restauraron %(cantidad)s registros.")
            % {"cantidad": cantidad},
            messages.SUCCESS,
        )

    def delete_model(self, request, obj):
        obj.delete()
        self.message_user(
            request,
            _("El registro se marcó como eliminado."),
            messages.SUCCESS,
        )

    def delete_queryset(self, request, queryset):
        queryset.delete()
        self.message_user(
            request,
            _("Los registros seleccionados se marcaron como eliminados."),
            messages.SUCCESS,
        )

    def get_deleted_objects(self, objs, request):
        objetos = list(objs)
        conteo = {str(self.model._meta.verbose_name_plural): len(objetos)}
        return [str(objeto) for objeto in objetos], conteo, set(), []
