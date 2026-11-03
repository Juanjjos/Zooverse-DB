from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.test import TestCase

from fauna.models import Especie, Zona
from visitas.models import Boleto, Itinerario, Reserva


class ItinerarioNumEspeciesDistintasTests(TestCase):
    def test_calcula_especies_distintas_en_sus_zonas(self):
        zona_norte = Zona.objects.create(
            nombre="Zona norte",
            extension_hectareas="2.50",
        )
        zona_sur = Zona.objects.create(
            nombre="Zona sur",
            extension_hectareas="3.00",
        )
        Itinerario.objects.create(
            codigo="IT-001",
            duracion_minutos=45,
            longitud_km="1.25",
            cupo_maximo=20,
        ).zonas.add(zona_norte, zona_sur)
        Especie.objects.create(
            nombre_espanol="Jaguar",
            nombre_cientifico="Panthera onca",
            descripcion="Felino de prueba.",
            zona=zona_norte,
        )
        Especie.objects.create(
            nombre_espanol="Tapir",
            nombre_cientifico="Tapirus terrestris",
            descripcion="Mamífero de prueba.",
            zona=zona_sur,
        )

        itinerario = Itinerario.objects.get(codigo="IT-001")

        self.assertEqual(itinerario.num_especies_distintas, 2)

    def test_itinerario_sin_zonas_tiene_cero_especies(self):
        itinerario = Itinerario.objects.create(
            codigo="IT-002",
            duracion_minutos=30,
            longitud_km="0.75",
            cupo_maximo=10,
        )

        self.assertEqual(itinerario.num_especies_distintas, 0)


class BoletoTests(TestCase):
    def test_guarda_reserva_y_expone_itinerario_fecha_y_precio(self):
        itinerario = Itinerario.objects.create(
            codigo="IT-BOLETO",
            duracion_minutos=30,
            longitud_km="1.00",
            cupo_maximo=10,
        )
        fecha = date(2026, 11, 1)
        reserva = Reserva.objects.create(
            itinerario=itinerario,
            fecha=fecha,
            cantidad_personas=1,
        )

        boleto = Boleto.objects.create(
            tipo=Boleto.Tipo.ESTUDIANTE,
            reserva=reserva,
            precio_pagado=Decimal("12.50"),
        )

        self.assertEqual(boleto.precio_pagado, Decimal("12.50"))
        self.assertEqual(boleto.itinerario, itinerario)
        self.assertEqual(boleto.fecha, fecha)

    def test_boleto_requiere_reserva(self):
        itinerario = Itinerario.objects.create(
            codigo="IT-VENTA",
            duracion_minutos=30,
            longitud_km="1.00",
            cupo_maximo=10,
        )

        with self.assertRaises(ValidationError):
            Boleto.objects.create(
                tipo=Boleto.Tipo.NINO,
                precio_pagado=Decimal("10.00"),
            )

    def test_reserva_no_puede_tener_mas_boletos_que_personas(self):
        itinerario = Itinerario.objects.create(
            codigo="IT-RES-BOLETO",
            duracion_minutos=30,
            longitud_km="1.00",
            cupo_maximo=1,
        )
        reserva = Reserva.objects.create(
            itinerario=itinerario,
            cantidad_personas=1,
            fecha=date(2026, 11, 1),
        )

        boleto = Boleto.objects.create(
            tipo=Boleto.Tipo.GENERAL,
            reserva=reserva,
            precio_pagado=Decimal("20.00"),
        )

        self.assertEqual(boleto.reserva, reserva)
        with self.assertRaises(ValidationError):
            Boleto.objects.create(
                tipo=Boleto.Tipo.GENERAL,
                reserva=reserva,
                precio_pagado=Decimal("20.00"),
            )


class ReservaCupoTests(TestCase):
    def setUp(self):
        self.itinerario = Itinerario.objects.create(
            codigo="IT-RESERVA",
            duracion_minutos=30,
            longitud_km="1.00",
            cupo_maximo=10,
        )
        self.fecha = date(2026, 11, 1)

    def crear_reserva(self, cantidad, fecha=None):
        return Reserva.objects.create(
            itinerario=self.itinerario,
            cantidad_personas=cantidad,
            fecha=fecha or self.fecha,
        )

    def test_acepta_reservas_hasta_el_cupo_exactamente(self):
        self.crear_reserva(4)
        ultima_reserva = self.crear_reserva(6)

        self.assertEqual(ultima_reserva.cantidad_personas, 6)

    def test_rechaza_reserva_que_excede_cupo_del_mismo_dia(self):
        self.crear_reserva(7)

        with self.assertRaises(ValidationError):
            self.crear_reserva(4)

        self.assertEqual(Reserva.objects.count(), 1)

    def test_cupo_se_calcula_separadamente_por_fecha(self):
        self.crear_reserva(10)

        reserva_dia_siguiente = self.crear_reserva(
            10,
            fecha=date(2026, 11, 2),
        )

        self.assertEqual(reserva_dia_siguiente.cantidad_personas, 10)

    def test_al_actualizar_reserva_no_se_cuenta_dos_veces(self):
        reserva = self.crear_reserva(6)
        reserva.cantidad_personas = 10
        reserva.save()

        self.assertEqual(
            Reserva.objects.filter(fecha=self.fecha).aggregate(
                total=Sum("cantidad_personas")
            )["total"],
            10,
        )

    def test_rechaza_cantidad_no_positiva(self):
        with self.assertRaises(ValidationError):
            self.crear_reserva(0)
