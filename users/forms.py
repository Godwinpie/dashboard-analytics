from django import forms
from django.contrib.auth.models import User
from .models import UserChartAccess, CHART_CHOICES

class UserChartAccessForm(forms.ModelForm):
    charts = forms.MultipleChoiceField(
        choices=CHART_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Chart Access Permissions"
    )

    class Meta:
        model = UserChartAccess
        fields = ['charts']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.charts:
            self.initial['charts'] = self.instance.charts
