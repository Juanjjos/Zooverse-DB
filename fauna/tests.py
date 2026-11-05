from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from fauna.models import Especie, Zona


class BorradoLogicoTests(TestCase):
    def setUp(self):
        self.zona = Zona.objects.create(
            nombre="Zona de prueba",
            extension_hectareas="2.00",
        )
        self.especie = Especie.objects.create(
            nombre_espanol="Especie de prueba",
            nombre_cientifico="Species testus",
            descripcion="Registro relacionado para probar el borrado lógico.",
            zona=self.zona,
        )

    def test_borrado_logico_conserva_registros_y_permite_restaurar(self):
        self.zona.delete()

        self.assertFalse(Zona.objects.filter(pk=self.zona.pk).exists())
        self.assertTrue(Zona.all_objects.get(pk=self.zona.pk).eliminado)
        self.assertEqual(self.especie.zona_id, self.zona.pk)
        self.assertTrue(Especie.objects.filter(pk=self.especie.pk).exists())

        self.zona.restore()

        self.assertTrue(Zona.objects.filter(pk=self.zona.pk).exists())
        self.assertIsNone(self.zona.fecha_eliminacion)

    def test_admin_oculta_eliminados_y_permite_restaurarlos(self):
        usuario = get_user_model().objects.create_superuser(
            username="admin_soft_delete",
            email="admin@example.com",
            password="test-password",
        )
        self.client.force_login(usuario)
        self.zona.delete()

        url_lista = reverse("admin:fauna_zona_changelist")
        respuesta_activos = self.client.get(url_lista)
        respuesta_eliminados = self.client.get(
            url_lista,
            {"estado_registro": "eliminados"},
        )

        self.assertNotContains(respuesta_activos, "Zona de prueba")
        self.assertContains(respuesta_eliminados, "Zona de prueba")

        respuesta_restaurar = self.client.post(
            f"{url_lista}?estado_registro=eliminados",
            {
                "action": "restaurar_registros",
                "_selected_action": [self.zona.pk],
            },
        )

        self.assertEqual(respuesta_restaurar.status_code, 302)
        self.assertTrue(Zona.objects.filter(pk=self.zona.pk).exists())

    def test_confirmacion_de_borrado_del_admin_es_logica(self):
        usuario = get_user_model().objects.create_superuser(
            username="admin_delete_confirm",
            email="admin-delete@example.com",
            password="test-password",
        )
        self.client.force_login(usuario)
        url_eliminar = reverse(
            "admin:fauna_zona_delete",
            args=[self.zona.pk],
        )

        respuesta_confirmacion = self.client.get(url_eliminar)
        respuesta_eliminar = self.client.post(url_eliminar, {"post": "yes"})

        self.assertEqual(respuesta_confirmacion.status_code, 200)
        self.assertEqual(respuesta_eliminar.status_code, 302)
        self.assertFalse(Zona.objects.filter(pk=self.zona.pk).exists())
        self.assertTrue(Zona.all_objects.filter(pk=self.zona.pk).exists())
