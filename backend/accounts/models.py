from django.db import models


class PasswordResetEvent(models.Model):
    class EventType(models.TextChoices):
        REQUESTED = "REQUESTED", "Requested"
        CONFIRMED = "CONFIRMED", "Confirmed"

    email = models.EmailField()
    event_type = models.CharField(max_length=20, choices=EventType.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.event_type} {self.email}"
