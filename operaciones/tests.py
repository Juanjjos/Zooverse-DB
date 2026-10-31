from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
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
