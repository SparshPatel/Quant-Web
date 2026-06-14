from django.db import models
from django.conf import settings
import json


class SavedAnalysis(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name='saved_analyses')
    tool_name = models.CharField(max_length=50)
    tool_label = models.CharField(max_length=100)
    parameters = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.tool_label} — {self.created_at:%Y-%m-%d %H:%M}"
