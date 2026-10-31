from datetime import date
from decimal import Decimal

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.core.management import call_command
from django.test import TestCase

from fauna.models import Especie, Habitat, Zona
from operaciones.models import (
    EntregaAlimento,
    InventarioAlimento,
    Mantenimiento,
    TipoAlimento,
)
from personal.models import Cuidador


class EntregaAlimentoTests(TestCase):
    def setUp(self):
        self.zona = Zona.objects.create(
            nombre="Sabana",
            extension_hectareas=Decimal("3.00"),
        )
        self.especie = Especie.objects.create(
            nombre_espanol="Cebra",
            nombre_cientifico="Equus quagga",
            descripcion="Mamífero herbívoro.",
            zona=self.zona,
        )
        self.cuidador = Cuidador.objects.create(
            nombre="Ana",
            direccion="Dirección de prueba",
            telefono="555-0100",
            fecha_ingreso=date(2025, 1, 1),
        )
        self.alimento = TipoAlimento.objects.create(
            nombre="Heno",
            unidad=TipoAlimento.Unidad.KILOGRAMO,
        )
        self.inventario = InventarioAlimento.objects.create(
            tipo_alimento=self.alimento,
            cantidad_disponible=Decimal("20.000"),
            umbral_minimo=Decimal("2.000"),
        )

    def crear_entrega(self, cantidad):
        return EntregaAlimento.objects.create(
            cuidador=self.cuidador,
            especie=self.especie,
            tipo_alimento=self.alimento,
            cantidad=Decimal(cantidad),
            fecha=date(2026, 10, 31),
        )

    def test_crear_entrega_descuenta_inventario(self):
        self.crear_entrega("3.500")

        self.inventario.refresh_from_db()
        self.assertEqual(self.inventario.cantidad_disponible, Decimal("16.500"))

    def test_no_permite_entrega_mayor_al_inventario(self):
        with self.assertRaises(ValidationError):
            self.crear_entrega("21.000")

        self.inventario.refresh_from_db()
        self.assertEqual(self.inventario.cantidad_disponible, Decimal("20.000"))
        self.assertEqual(EntregaAlimento.objects.count(), 0)

    def test_actualizar_entrega_aplica_solo_la_diferencia(self):
        entrega = self.crear_entrega("3.000")
        entrega.cantidad = Decimal("5.000")
        entrega.save()

        self.inventario.refresh_from_db()
        self.assertEqual(self.inventario.cantidad_disponible, Decimal("15.000"))

    def test_eliminar_entrega_reintegra_inventario_incluso_en_borrado_masivo(self):
        self.crear_entrega("3.000")

        EntregaAlimento.objects.all().delete()

        self.inventario.refresh_from_db()
        self.assertEqual(self.inventario.cantidad_disponible, Decimal("20.000"))


class MantenimientoTests(TestCase):
    def test_registra_ubicacion_zona_o_habitat(self):
        zona = Zona.objects.create(
            nombre="Acuática",
            extension_hectareas=Decimal("2.00"),
        )
        habitat = Habitat.objects.create(
            nombre="Humedal",
            clima="Tropical",
            vegetacion="Juncos",
        )
        hoy = date(2026, 10, 31)

        mantenimiento_zona = Mantenimiento.objects.create(
            zona=zona,
            fecha=hoy,
            descripcion="Revisión de sendero.",
        )
        mantenimiento_habitat = Mantenimiento.objects.create(
            habitat=habitat,
            fecha=hoy,
            descripcion="Limpieza de estanque.",
        )

        self.assertEqual(mantenimiento_zona.zona, zona)
        self.assertEqual(mantenimiento_habitat.habitat, habitat)

    def test_rechaza_mantenimiento_sin_ubicacion_o_con_dos(self):
        zona = Zona.objects.create(
            nombre="Bosque",
            extension_hectareas=Decimal("4.00"),
        )
        habitat = Habitat.objects.create(
            nombre="Bosque templado",
            clima="Templado",
            vegetacion="Árboles",
        )
        datos = {
            "fecha": date(2026, 10, 31),
            "descripcion": "Mantenimiento de prueba.",
        }

        with self.assertRaises(IntegrityError), transaction.atomic():
            Mantenimiento.objects.create(**datos)

        with self.assertRaises(IntegrityError), transaction.atomic():
            Mantenimiento.objects.create(zona=zona, habitat=habitat, **datos)


class ConfigurarRolesTests(TestCase):
    def setUp(self):
        call_command("configurar_roles", verbosity=0)

    def permisos_de(self, nombre_grupo):
        return set(
            Group.objects.get(name=nombre_grupo)
            .permissions.values_list(
                "content_type__app_label",
                "codename",
            )
        )

    def test_crea_los_cuatro_grupos(self):
        self.assertSetEqual(
            set(Group.objects.values_list("name", flat=True)),
            {"Administrador", "Cuidador", "Guía", "Taquillero"},
        )

    def test_cuidador_puede_registrar_entregas_y_no_borrar(self):
        permisos = self.permisos_de("Cuidador")

        self.assertIn(("operaciones", "add_entregaalimento"), permisos)
        self.assertIn(("operaciones", "view_entregaalimento"), permisos)
        self.assertNotIn(("operaciones", "delete_entregaalimento"), permisos)
        self.assertNotIn(("visitas", "add_boleto"), permisos)

    def test_guia_tiene_acceso_de_solo_lectura_a_itinerarios(self):
        permisos = self.permisos_de("Guía")

        self.assertIn(("visitas", "view_itinerario"), permisos)
        self.assertIn(("visitas", "view_asignacionguia"), permisos)
        self.assertNotIn(("visitas", "change_itinerario"), permisos)
        self.assertNotIn(("visitas", "add_reserva"), permisos)

    def test_taquillero_puede_vender_boletos_sin_modificar_boleto_existente(self):
        permisos = self.permisos_de("Taquillero")

        self.assertIn(("visitas", "add_boleto"), permisos)
        self.assertIn(("visitas", "add_reserva"), permisos)
        self.assertNotIn(("visitas", "change_boleto"), permisos)
        self.assertNotIn(("visitas", "delete_boleto"), permisos)

    def test_administrador_tiene_permisos_completos_de_modelos_del_dominio(self):
        permisos = self.permisos_de("Administrador")

        self.assertIn(("fauna", "delete_especie"), permisos)
        self.assertIn(("visitas", "change_boleto"), permisos)
        self.assertIn(("operaciones", "delete_mantenimiento"), permisos)

    def test_ejecucion_repetida_no_duplica_grupos_ni_permisos(self):
        permisos_antes = self.permisos_de("Cuidador")
        call_command("configurar_roles", verbosity=0)

        self.assertEqual(Group.objects.filter(name="Cuidador").count(), 1)
        self.assertSetEqual(self.permisos_de("Cuidador"), permisos_antes)
