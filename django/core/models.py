from django.db import models


class AuditLog(models.Model):
    action_type = models.CharField(max_length=80)
    user = models.EmailField()
    timestamp = models.DateTimeField(auto_now_add=True)
    record_id = models.IntegerField()
    details = models.TextField()

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.action_type} for request {self.record_id}"
