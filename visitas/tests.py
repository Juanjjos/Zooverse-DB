from django.test import TestCase

from fauna.models import Especie, Zona
from visitas.models import Itinerario


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
