from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from fauna.models import Especie
from operaciones.models import (
    EntregaAlimento,
    InventarioAlimento,
    Mantenimiento,
    RevisionVeterinaria,
    TipoAlimento,
    Vacuna,
)
from personal.models import Cuidador
from reportes.alertas import obtener_alertas
from reportes.consultas import construir_datos_reportes
from visitas.models import Itinerario


class ReportesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_data", verbosity=0)
        cls.administrador = User.objects.create_user(
            username="admin_reportes",
            password="prueba-segura-123",
        )
        grupo = Group.objects.create(name="Administrador")
        cls.administrador.groups.add(grupo)
        cls.usuario_sin_rol = User.objects.create_user(
            username="usuario",
            password="prueba-segura-123",
        )

    def test_solo_administrador_puede_ver_reportes(self):
        self.client.force_login(self.administrador)
        respuesta_admin = self.client.get(reverse("reportes:inicio"))
        self.assertEqual(respuesta_admin.status_code, 200)

        self.client.force_login(self.usuario_sin_rol)
        respuesta_usuario = self.client.get(reverse("reportes:inicio"))
        self.assertEqual(respuesta_usuario.status_code, 403)

    def test_usuario_anonimo_es_enviado_al_login_del_admin(self):
        respuesta = self.client.get(reverse("reportes:inicio"))

        self.assertEqual(respuesta.status_code, 302)
        self.assertTrue(respuesta.url.startswith("/admin/login/"))

    def test_portada_publica_muestra_enlaces_a_las_tres_secciones(self):
        respuesta = self.client.get(reverse("inicio_publico"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, reverse("admin:index"))
        self.assertContains(respuesta, reverse("reportes:inicio"))
        self.assertContains(respuesta, reverse("reportes:alertas"))

    def test_panel_presenta_los_reportes_y_estadisticas(self):
        self.client.force_login(self.administrador)

        respuesta = self.client.get(reverse("reportes:inicio"))

        self.assertContains(respuesta, "Especies por zona y hábitat")
        self.assertContains(respuesta, "Itinerarios más solicitados")
        self.assertContains(respuesta, "Ingresos por día")
        self.assertContains(respuesta, "Ingresos por mes")
        self.assertContains(respuesta, "Ingresos por tipo de boleto")
        self.assertContains(respuesta, "Historial médico")
        self.assertContains(respuesta, "Consumo de alimento por especie y periodo")
        self.assertContains(respuesta, "Ocupación promedio diaria de itinerarios")

    def test_filtros_de_periodo_y_especie_se_aplican(self):
        jaguar = Especie.objects.get(nombre_cientifico="Panthera onca")
        fecha = timezone.localdate()
        self.client.force_login(self.administrador)

        respuesta = self.client.get(
            reverse("reportes:inicio"),
            {
                "fecha_inicio": fecha.isoformat(),
                "fecha_fin": fecha.isoformat(),
                "especie": jaguar.pk,
            },
        )

        self.assertEqual(respuesta.status_code, 200)
        historial = respuesta.context["datos_reportes"]["historial_medico"]
        self.assertTrue(historial)
        self.assertTrue(all(evento["especie"] == "Jaguar" for evento in historial))

    def test_formulario_rechaza_periodo_invertido_y_no_genera_reportes(self):
        fecha = timezone.localdate()
        self.client.force_login(self.administrador)

        respuesta = self.client.get(
            reverse("reportes:inicio"),
            {
                "fecha_inicio": (fecha + timedelta(days=1)).isoformat(),
                "fecha_fin": fecha.isoformat(),
            },
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(
            respuesta,
            "La fecha inicial no puede ser posterior a la fecha final.",
        )
        self.assertNotContains(respuesta, "Itinerarios más solicitados")

    def test_consultas_agrupan_importes_y_uso_de_alimentos_por_unidad(self):
        datos = construir_datos_reportes()

        self.assertTrue(datos["ingresos"]["por_dia"])
        self.assertTrue(datos["ingresos"]["por_mes"])
        self.assertTrue(datos["ingresos"]["por_tipo"])
        self.assertTrue(datos["itinerarios_solicitados"])
        self.assertIsNotNone(datos["ocupacion"]["promedio_general"])
        self.assertTrue(datos["alimento_mas_consumido"])

    def test_historial_medico_puede_filtrarse_por_especie(self):
        jaguar = Especie.objects.get(nombre_cientifico="Panthera onca")

        historial = construir_datos_reportes(especie_id=jaguar.pk)[
            "historial_medico"
        ]

        self.assertTrue(historial)
        self.assertTrue(all(evento["especie"] == "Jaguar" for evento in historial))

    def test_estadistica_de_consumo_no_compara_unidades_incompatibles(self):
        pellets = TipoAlimento.objects.get(nombre="Pellets de tortuga")
        inventario = pellets.inventario
        inventario.cantidad_disponible = Decimal("14500.000")
        inventario.save(update_fields=["cantidad_disponible"])
        cuidador = Cuidador.objects.get(nombre="Camila Torres")
        especie = Especie.objects.get(nombre_cientifico="Chelonia mydas")
        EntregaAlimento.objects.create(
            cuidador=cuidador,
            especie=especie,
            tipo_alimento=pellets,
            cantidad=Decimal("500.000"),
            fecha=timezone.localdate(),
        )

        datos = construir_datos_reportes()
        mayores = {
            fila["dimension"]: fila
            for fila in datos["alimento_mas_consumido"]
        }

        self.assertEqual(
            mayores["masa"]["tipo_alimento__nombre"],
            "Carne preparada",
        )
        self.assertEqual(
            mayores["masa"]["cantidad_normalizada"],
            Decimal("11.000"),
        )


class PanelAlertasTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_data", verbosity=0)
        cls.especie = Especie.objects.get(nombre_cientifico="Panthera leo")
        cls.hoy = timezone.localdate()
        cls.grupo_administrador, _ = Group.objects.get_or_create(
            name="Administrador"
        )

    def setUp(self):
        self.administrador = User.objects.create_user(
            username="admin_alertas",
            password="prueba-segura-123",
        )
        self.administrador.groups.add(self.grupo_administrador)

    def test_incluye_las_cinco_categorias_de_alertas(self):
        heno = TipoAlimento.objects.get(nombre="Heno")
        inventario = InventarioAlimento.objects.get(tipo_alimento=heno)
        inventario.cantidad_disponible = inventario.umbral_minimo - Decimal("1.000")
        inventario.save(update_fields=["cantidad_disponible"])

        itinerario = Itinerario.objects.get(codigo="SAB-01")
        itinerario.cupo_maximo = 9
        itinerario.save(update_fields=["cupo_maximo"])

        alertas = obtener_alertas(self.hoy)

        self.assertTrue(alertas["vacunas"])
        self.assertTrue(alertas["revisiones_pendientes"])
        self.assertIn(inventario, alertas["inventarios_bajos"])
        self.assertTrue(alertas["mantenimientos_vencidos"])
        self.assertTrue(
            any(
                fila["itinerario"].pk == itinerario.pk
                and fila["personas"] == fila["cupo_maximo"]
                for fila in alertas["itinerarios_llenos"]
            )
        )

    def test_vacuna_a_mas_de_quince_dias_no_genera_alerta(self):
        vacuna_lejana = Vacuna.objects.create(
            especie=self.especie,
            nombre="Vacuna futura fuera de ventana",
            fecha_aplicacion=self.hoy,
            fecha_proxima=self.hoy + timedelta(days=16),
        )

        alertas = obtener_alertas(self.hoy)

        self.assertNotIn(vacuna_lejana, alertas["vacunas"])

    def test_revision_con_fecha_futura_no_esta_pendiente(self):
        revision_futura = RevisionVeterinaria.objects.create(
            especie=self.especie,
            fecha=self.hoy - timedelta(days=5),
            diagnostico="Control preventivo.",
            fecha_proxima_revision=self.hoy + timedelta(days=1),
        )

        alertas = obtener_alertas(self.hoy)

        self.assertNotIn(revision_futura, alertas["revisiones_pendientes"])

    def test_acceso_al_panel_restringido_a_administradores(self):
        self.client.force_login(self.administrador)
        respuesta_admin = self.client.get(reverse("reportes:alertas"))
        self.assertEqual(respuesta_admin.status_code, 200)

        usuario = User.objects.create_user(
            username="sin_rol_alertas",
            password="prueba-segura-123",
        )
        self.client.force_login(usuario)
        respuesta_usuario = self.client.get(reverse("reportes:alertas"))
        self.assertEqual(respuesta_usuario.status_code, 403)

    def test_panel_muestra_todas_las_secciones_de_alertas(self):
        self.client.force_login(self.administrador)

        respuesta = self.client.get(reverse("reportes:alertas"))

        self.assertContains(respuesta, "Vacunas vencidas o próximas (15 días)")
        self.assertContains(respuesta, "Revisiones veterinarias pendientes")
        self.assertContains(respuesta, "Inventario por debajo del umbral mínimo")
        self.assertContains(respuesta, "Mantenimientos vencidos")
        self.assertContains(respuesta, "Itinerarios con cupo completo hoy")
