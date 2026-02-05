# from django.conf import settings
from django.db import models
from django.contrib.auth.models import User

CHART_CHOICES = [
	("win_rate", "Win Rate Over Time"),
	("win_rate_strategist", "Win Rate by Strategist"),
	("win_rate_product", "Win Rate by Product"),
	("win_rate_adtype", "Win Rate by Ad Type"),
	("adtype_ratio", "Ad Type Ratio"),
	("product_ratio", "Product Ratio"),
	("format_ratio", "Format Ratio"),
	("production_time", "Avg Production Time"),
	("editing_time", "Avg Editing Time"),
	("creatives_volume", "Creatives Volume"),
]

class UserChartAccess(models.Model):
	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="chart_access")
	charts = models.JSONField(default=list)  # List of chart keys

	def __str__(self):
		return f"Chart access for {self.user.email or self.user.username}"
