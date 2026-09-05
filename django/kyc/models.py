from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class KycRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "Pending", "Pending"
        APPROVED = "Approved", "Approved"
        REJECTED = "Rejected", "Rejected"

    kyc_request_id = models.IntegerField(unique=True)
    customer_name = models.CharField(max_length=160)
    customer_email = models.EmailField()
    risk_score = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    submission_date = models.DateField()
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    reviewer_notes = models.TextField(blank=True)
    reviewed_by = models.EmailField(blank=True)
    reviewed_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["submission_date", "kyc_request_id"]

    def __str__(self):
        return f"{self.kyc_request_id}: {self.customer_name}"
