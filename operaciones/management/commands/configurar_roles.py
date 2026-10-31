from django.apps import apps
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError


ROLES = {
    "Administrador": {
        app_label: {
            model_name: ("view", "add", "change", "delete")
            for model_name in model_names
        }
        for app_label, model_names in {
            "fauna": ("continente", "habitat", "zona", "especie"),
            "personal": ("guia", "cuidador", "cuidadoespecie"),
            "visitas": ("itinerario", "asignacionguia", "boleto", "reserva"),
            "operaciones": (
                "revisionveterinaria",
                "vacuna",
                "tipoalimento",
                "dieta",
                "inventarioalimento",
                "entregaalimento",
                "mantenimiento",
            ),
        }.items()
    },
    "Cuidador": {
        "fauna": {
            "especie": ("view",),
            "habitat": ("view",),
            "zona": ("view",),
        },
        "personal": {
            "cuidadoespecie": ("view",),
        },
        "operaciones": {
            "revisionveterinaria": ("view", "add", "change"),
            "vacuna": ("view", "add", "change"),
            "tipoalimento": ("view",),
            "dieta": ("view",),
            "inventarioalimento": ("view",),
            "entregaalimento": ("view", "add"),
        },
    },
    "Guía": {
        "fauna": {
            "especie": ("view",),
            "zona": ("view",),
        },
        "visitas": {
            "itinerario": ("view",),
            "asignacionguia": ("view",),
        },
    },
    "Taquillero": {
        "visitas": {
            "itinerario": ("view",),
            "reserva": ("view", "add", "change"),
            "boleto": ("view", "add"),
        },
    },
}


class Command(BaseCommand):
    help = "Crea o actualiza los grupos y permisos de ZooVerse."

    def handle(self, *args, **options):
        for role_name, models_by_app in ROLES.items():
            permissions = []
            for app_label, models_by_name in models_by_app.items():
                for model_name, actions in models_by_name.items():
                    try:
                        model = apps.get_model(app_label, model_name)
                    except LookupError as error:
                        raise CommandError(
                            f"No existe el modelo {app_label}.{model_name}."
                        ) from error

                    for action in actions:
                        codename = f"{action}_{model._meta.model_name}"
                        try:
                            permission = Permission.objects.get(
                                content_type__app_label=app_label,
                                codename=codename,
                            )
                        except Permission.DoesNotExist as error:
                            raise CommandError(
                                "No existe el permiso "
                                f"{app_label}.{codename}; ejecuta migrate primero."
                            ) from error
                        permissions.append(permission)

            group, created = Group.objects.get_or_create(name=role_name)
            group.permissions.set(permissions)
            action = "creado" if created else "actualizado"
            self.stdout.write(f"Grupo {role_name}: {action}.")
