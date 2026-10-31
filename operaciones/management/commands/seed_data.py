from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from fauna.models import Continente, Especie, Habitat, Zona
from operaciones.models import (
    Dieta,
    EntregaAlimento,
    InventarioAlimento,
    Mantenimiento,
    RevisionVeterinaria,
    TipoAlimento,
    Vacuna,
)
from personal.models import Cuidador, CuidadoEspecie, Guia
from visitas.models import AsignacionGuia, Boleto, Itinerario, Reserva


class Command(BaseCommand):
    help = "Carga datos de prueba realistas para ZooVerse sin duplicarlos."

    @transaction.atomic
    def handle(self, *args, **options):
        hoy = timezone.localdate()
        continentes = self._crear_catalogo(Continente, "nombre", [
            {"nombre": "África"},
            {"nombre": "América del Sur"},
            {"nombre": "Asia"},
            {"nombre": "Oceanía"},
        ])

        habitats = {}
        for datos in [
            {
                "nombre": "Sabana africana",
                "clima": "Tropical estacional",
                "vegetacion": "Pastizales y acacias",
                "continentes": ["África"],
            },
            {
                "nombre": "Selva amazónica",
                "clima": "Tropical húmedo",
                "vegetacion": "Bosque denso y lianas",
                "continentes": ["América del Sur"],
            },
            {
                "nombre": "Bosque asiático",
                "clima": "Templado húmedo",
                "vegetacion": "Bosque mixto",
                "continentes": ["Asia"],
            },
            {
                "nombre": "Arrecife oceánico",
                "clima": "Tropical marino",
                "vegetacion": "Corales y algas",
                "continentes": ["Oceanía", "Asia"],
            },
        ]:
            continente_names = datos.pop("continentes")
            habitat, _ = Habitat.objects.get_or_create(
                nombre=datos["nombre"],
                defaults=datos,
            )
            for nombre in continente_names:
                habitat.continentes.add(continentes[nombre])
            habitats[habitat.nombre] = habitat

        zonas = self._crear_catalogo(Zona, "nombre", [
            {"nombre": "Llanuras", "extension_hectareas": Decimal("12.50")},
            {"nombre": "Bosque tropical", "extension_hectareas": Decimal("8.75")},
            {"nombre": "Montaña asiática", "extension_hectareas": Decimal("6.25")},
            {"nombre": "Mundo marino", "extension_hectareas": Decimal("5.00")},
        ])

        especies_datos = [
            (
                "León africano", "Panthera leo",
                "Felino social nativo de las sabanas africanas.",
                "Llanuras", ["Sabana africana"],
            ),
            (
                "Jirafa", "Giraffa camelopardalis",
                "Mamífero herbívoro de cuello largo.",
                "Llanuras", ["Sabana africana"],
            ),
            (
                "Jaguar", "Panthera onca",
                "Felino de gran tamaño propio de América.",
                "Bosque tropical", ["Selva amazónica"],
            ),
            (
                "Tapir amazónico", "Tapirus terrestris",
                "Mamífero herbívoro de ambientes selváticos.",
                "Bosque tropical", ["Selva amazónica"],
            ),
            (
                "Panda rojo", "Ailurus fulgens",
                "Mamífero arborícola de bosques montañosos.",
                "Montaña asiática", ["Bosque asiático"],
            ),
            (
                "Tortuga verde", "Chelonia mydas",
                "Tortuga marina que habita aguas tropicales.",
                "Mundo marino", ["Arrecife oceánico"],
            ),
        ]
        especies = {}
        for nombre, cientifico, descripcion, zona_nombre, habitat_names in especies_datos:
            especie, _ = Especie.objects.get_or_create(
                nombre_cientifico=cientifico,
                defaults={
                    "nombre_espanol": nombre,
                    "descripcion": descripcion,
                    "zona": zonas[zona_nombre],
                },
            )
            especie.habitats.add(*(habitats[n] for n in habitat_names))
            especies[cientifico] = especie

        guias = self._crear_catalogo(Guia, "nombre", [
            {
                "nombre": "Lucía Herrera",
                "direccion": "Calle 10 # 12-30",
                "telefono": "3005550101",
                "fecha_inicio": hoy - timedelta(days=900),
            },
            {
                "nombre": "Mateo Ríos",
                "direccion": "Carrera 8 # 20-15",
                "telefono": "3005550102",
                "fecha_inicio": hoy - timedelta(days=600),
            },
            {
                "nombre": "Valentina Cruz",
                "direccion": "Avenida 5 # 18-40",
                "telefono": "3005550103",
                "fecha_inicio": hoy - timedelta(days=300),
            },
        ])
        cuidadores = self._crear_catalogo(Cuidador, "nombre", [
            {
                "nombre": "Sofía Méndez",
                "direccion": "Calle 14 # 7-22",
                "telefono": "3105550201",
                "fecha_ingreso": hoy - timedelta(days=800),
            },
            {
                "nombre": "Andrés Pardo",
                "direccion": "Carrera 16 # 9-11",
                "telefono": "3105550202",
                "fecha_ingreso": hoy - timedelta(days=500),
            },
            {
                "nombre": "Camila Torres",
                "direccion": "Calle 22 # 4-19",
                "telefono": "3105550203",
                "fecha_ingreso": hoy - timedelta(days=250),
            },
        ])

        cuidador_por_especie = [
            ("Sofía Méndez", "Panthera leo"),
            ("Sofía Méndez", "Giraffa camelopardalis"),
            ("Andrés Pardo", "Panthera onca"),
            ("Andrés Pardo", "Tapirus terrestris"),
            ("Camila Torres", "Ailurus fulgens"),
            ("Camila Torres", "Chelonia mydas"),
        ]
        for indice, (cuidador_nombre, especie_codigo) in enumerate(
            cuidador_por_especie
        ):
            CuidadoEspecie.objects.get_or_create(
                cuidador=cuidadores[cuidador_nombre],
                especie=especies[especie_codigo],
                defaults={"fecha_inicio": hoy - timedelta(days=180 - indice * 10)},
            )

        itinerarios = self._crear_catalogo(Itinerario, "codigo", [
            {
                "codigo": "SAB-01",
                "duracion_minutos": 50,
                "longitud_km": Decimal("2.40"),
                "cupo_maximo": 20,
            },
            {
                "codigo": "SEL-01",
                "duracion_minutos": 40,
                "longitud_km": Decimal("1.80"),
                "cupo_maximo": 16,
            },
            {
                "codigo": "BIO-01",
                "duracion_minutos": 65,
                "longitud_km": Decimal("3.10"),
                "cupo_maximo": 24,
            },
        ])
        zonas_por_itinerario = {
            "SAB-01": ["Llanuras"],
            "SEL-01": ["Bosque tropical"],
            "BIO-01": ["Llanuras", "Bosque tropical", "Montaña asiática"],
        }
        guias_por_itinerario = {
            "SAB-01": [("Lucía Herrera", "09:00"), ("Mateo Ríos", "14:00")],
            "SEL-01": [("Mateo Ríos", "10:00")],
            "BIO-01": [("Valentina Cruz", "11:00")],
        }
        for codigo, nombres_zona in zonas_por_itinerario.items():
            itinerarios[codigo].zonas.add(*(zonas[n] for n in nombres_zona))
            for guia_nombre, hora in guias_por_itinerario[codigo]:
                AsignacionGuia.objects.get_or_create(
                    itinerario=itinerarios[codigo],
                    hora=hora,
                    defaults={"guia": guias[guia_nombre]},
                )

        tipos_alimento = self._crear_catalogo(TipoAlimento, "nombre", [
            {"nombre": "Carne preparada", "unidad": TipoAlimento.Unidad.KILOGRAMO},
            {"nombre": "Heno", "unidad": TipoAlimento.Unidad.KILOGRAMO},
            {"nombre": "Fruta variada", "unidad": TipoAlimento.Unidad.KILOGRAMO},
            {"nombre": "Pescado", "unidad": TipoAlimento.Unidad.KILOGRAMO},
            {"nombre": "Pellets de tortuga", "unidad": TipoAlimento.Unidad.GRAMO},
        ])
        for nombre, cantidad, umbral in [
            ("Carne preparada", "120.000", "25.000"),
            ("Heno", "300.000", "50.000"),
            ("Fruta variada", "180.000", "30.000"),
            ("Pescado", "90.000", "20.000"),
            ("Pellets de tortuga", "15000.000", "2500.000"),
        ]:
            InventarioAlimento.objects.get_or_create(
                tipo_alimento=tipos_alimento[nombre],
                defaults={
                    "cantidad_disponible": Decimal(cantidad),
                    "umbral_minimo": Decimal(umbral),
                },
            )

        dietas = [
            ("Panthera leo", "Carne preparada", "7.500"),
            ("Giraffa camelopardalis", "Heno", "12.000"),
            ("Giraffa camelopardalis", "Fruta variada", "2.000"),
            ("Panthera onca", "Carne preparada", "5.000"),
            ("Tapirus terrestris", "Fruta variada", "4.000"),
            ("Ailurus fulgens", "Fruta variada", "1.500"),
            ("Chelonia mydas", "Pescado", "1.200"),
            ("Chelonia mydas", "Pellets de tortuga", "250.000"),
        ]
        for especie_codigo, tipo_nombre, cantidad in dietas:
            Dieta.objects.get_or_create(
                especie=especies[especie_codigo],
                tipo_alimento=tipos_alimento[tipo_nombre],
                defaults={"cantidad_diaria": Decimal(cantidad)},
            )

        for codigo, fecha_dias, diagnostico, proxima_dias in [
            ("Panthera leo", -45, "Control general sin novedades.", 45),
            ("Panthera leo", -180, "Seguimiento dental; requiere control.", -2),
            ("Giraffa camelopardalis", -30, "Evaluación nutricional estable.", 60),
            ("Panthera onca", -12, "Control preventivo rutinario.", 30),
            ("Tapirus terrestris", -90, "Revisión general satisfactoria.", 90),
            ("Ailurus fulgens", -20, "Seguimiento de peso y condición corporal.", 40),
            ("Chelonia mydas", -60, "Evaluación de caparazón satisfactoria.", 120),
        ]:
            fecha = hoy + timedelta(days=fecha_dias)
            RevisionVeterinaria.objects.get_or_create(
                especie=especies[codigo],
                fecha=fecha,
                defaults={
                    "diagnostico": diagnostico,
                    "fecha_proxima_revision": hoy + timedelta(days=proxima_dias),
                },
            )

        vacunas = [
            ("Panthera leo", "Vacuna felina", -365, 10),
            ("Giraffa camelopardalis", "Vacuna clostridial", -365, 90),
            ("Panthera onca", "Vacuna felina", -390, -25),
            ("Tapirus terrestris", "Vacuna polivalente", -300, 65),
            ("Ailurus fulgens", "Vacuna polivalente", -360, 5),
            ("Chelonia mydas", "Vacuna preventiva", -330, 35),
        ]
        for codigo, nombre, aplicacion_dias, proxima_dias in vacunas:
            Vacuna.objects.get_or_create(
                especie=especies[codigo],
                nombre=nombre,
                fecha_aplicacion=hoy + timedelta(days=aplicacion_dias),
                defaults={"fecha_proxima": hoy + timedelta(days=proxima_dias)},
            )

        for indice, (cuidador_nombre, especie_codigo, alimento_nombre, cantidad) in enumerate([
            ("Sofía Méndez", "Panthera leo", "Carne preparada", "6.500"),
            ("Sofía Méndez", "Giraffa camelopardalis", "Heno", "10.000"),
            ("Andrés Pardo", "Panthera onca", "Carne preparada", "4.500"),
            ("Andrés Pardo", "Tapirus terrestris", "Fruta variada", "3.000"),
            ("Camila Torres", "Ailurus fulgens", "Fruta variada", "1.000"),
            ("Camila Torres", "Chelonia mydas", "Pescado", "1.000"),
        ]):
            EntregaAlimento.objects.get_or_create(
                cuidador=cuidadores[cuidador_nombre],
                especie=especies[especie_codigo],
                tipo_alimento=tipos_alimento[alimento_nombre],
                fecha=hoy - timedelta(days=indice),
                defaults={"cantidad": Decimal(cantidad)},
            )

        mantenimientos = [
            ("zona", "Llanuras", -90, 90, "Inspección de cercas y senderos."),
            ("zona", "Bosque tropical", -30, -1, "Mantenimiento de pasarelas."),
            ("habitat", "Sabana africana", -60, 120, "Revisión de puntos de agua."),
            ("habitat", "Arrecife oceánico", -15, 75, "Limpieza y revisión de filtros."),
        ]
        for tipo_ubicacion, nombre_ubicacion, fecha_dias, proxima_dias, descripcion in mantenimientos:
            ubicacion = {
                "zona": zonas,
                "habitat": habitats,
            }[tipo_ubicacion][nombre_ubicacion]
            campos_ubicacion = {tipo_ubicacion: ubicacion}
            Mantenimiento.objects.get_or_create(
                **campos_ubicacion,
                fecha=hoy + timedelta(days=fecha_dias),
                descripcion=descripcion,
                defaults={
                    "fecha_proximo_mantenimiento": hoy + timedelta(days=proxima_dias),
                },
            )

        reservas = {}
        for codigo, cantidad, fecha_dias in [
            ("SAB-01", 8, 0),
            ("SAB-01", 5, 1),
            ("SEL-01", 6, 0),
            ("BIO-01", 10, 2),
        ]:
            fecha = hoy + timedelta(days=fecha_dias)
            reserva, _ = Reserva.objects.get_or_create(
                itinerario=itinerarios[codigo],
                fecha=fecha,
                cantidad_personas=cantidad,
            )
            reservas[(codigo, fecha)] = reserva

        for codigo, tipo, fecha_dias, precio, reserva_key in [
            ("SAB-01", Boleto.Tipo.GENERAL, 0, "35.00", ("SAB-01", hoy)),
            ("SAB-01", Boleto.Tipo.ESTUDIANTE, 0, "25.00", ("SAB-01", hoy)),
            ("SEL-01", Boleto.Tipo.NINO, 0, "18.00", ("SEL-01", hoy)),
            ("BIO-01", Boleto.Tipo.GENERAL, 2, "40.00", ("BIO-01", hoy + timedelta(days=2))),
            ("SAB-01", Boleto.Tipo.GENERAL, 0, "35.00", None),
        ]:
            fecha = hoy + timedelta(days=fecha_dias)
            reserva = reservas.get(reserva_key) if reserva_key else None
            Boleto.objects.get_or_create(
                tipo=tipo,
                itinerario=itinerarios[codigo],
                reserva=reserva,
                fecha=fecha,
                precio_pagado=Decimal(precio),
            )

        self.stdout.write(self.style.SUCCESS(
            "Datos de prueba cargados o ya existentes; la ejecución es repetible."
        ))

    @staticmethod
    def _crear_catalogo(modelo, campo_unico, registros):
        objetos = {}
        for datos in registros:
            clave = datos[campo_unico]
            objeto, _ = modelo.objects.get_or_create(
                **{campo_unico: clave},
                defaults=datos,
            )
            objetos[clave] = objeto
        return objetos
