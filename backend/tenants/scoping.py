from django.db import models


class TenantQuerySet(models.QuerySet):
    def for_tenant(self, tenant):
        return self.filter(tenant=tenant)


class TenantManager(models.Manager):
    def get_queryset(self):
        return TenantQuerySet(self.model, using=self._db)


class TenantScopedModel(models.Model):
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.PROTECT, related_name="%(class)ss")

    objects = TenantManager()

    class Meta:
        abstract = True
