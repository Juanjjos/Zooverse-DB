from django import forms

from fauna.models import Especie


class FiltroReportesForm(forms.Form):
    fecha_inicio = forms.DateField(
        required=False,
        label="Desde",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    fecha_fin = forms.DateField(
        required=False,
        label="Hasta",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    especie = forms.ModelChoiceField(
        queryset=Especie.objects.order_by("nombre_espanol"),
        required=False,
        label="Especie para el historial médico",
        empty_label="Todas las especies",
    )

    def clean(self):
        datos = super().clean()
        inicio = datos.get("fecha_inicio")
        fin = datos.get("fecha_fin")
        if inicio and fin and inicio > fin:
            raise forms.ValidationError(
                "La fecha inicial no puede ser posterior a la fecha final."
            )
        return datos
