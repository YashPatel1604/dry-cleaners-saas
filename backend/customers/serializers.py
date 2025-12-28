from rest_framework import serializers
from .models import Customer


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ["id", "name", "phone", "phone_e164",
                  "email", "notes", "created_at"]
        read_only_fields = ["id", "phone_e164", "created_at"]
