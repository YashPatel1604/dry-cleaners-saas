from django.db import models
from tenants.models import Tenant
import re


def normalize_phone_us(phone: str) -> str:
    """
    Lightweight normalizer (US default):
    - strips non-digits
    - 10 digits -> +1XXXXXXXXXX
    - 11 digits starting with 1 -> +1XXXXXXXXXX
    - otherwise -> "" (unknown)
    """
    if not phone:
        return ""
    digits = re.sub(r"\D+", "", phone)
    if len(digits) == 10:
        return "+1" + digits
    if len(digits) == 11 and digits.startswith("1"):
        return "+" + digits
    return ""


class Customer(models.Model):
    tenant = models.ForeignKey(
        Tenant, on_delete=models.CASCADE, related_name="customers"
    )

    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=30, blank=True)

    # ✅ canonical phone for fast lookup/dedupe
    phone_e164 = models.CharField(max_length=20, blank=True, default="")

    email = models.EmailField(blank=True)
    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "created_at"]),
            models.Index(fields=["tenant", "name"]),
            models.Index(fields=["tenant", "phone_e164"]),  # ✅ fast lookup
        ]
        constraints = [
            # ✅ prevent duplicates by phone within a tenant (only when phone_e164 is non-empty)
            models.UniqueConstraint(
                fields=["tenant", "phone_e164"],
                name="uniq_customer_phone_per_tenant",
                condition=~models.Q(phone_e164=""),
            )
        ]

    def save(self, *args, **kwargs):
        self.phone_e164 = normalize_phone_us(self.phone)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} ({self.tenant.slug})"
