
from rest_framework import serializers

from .models import PantryItem


class PantryItemSerializer(serializers.ModelSerializer):

    class Meta:
        model = PantryItem

        fields = [
            "id",
            "name",
            "category",
            "quantity",
            "unit",
            "storage",
            "expiry_date",
            "recipe_name",
            "quantity_display",
            "unit_display",
            "days_left",
            "status",
            "status_tone",
            "is_expired",
            "status_label",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "quantity_display",
            "unit_display",
            "days_left",
            "status",
            "status_tone",
            "is_expired",
            "status_label",
            "created_at",
            "updated_at",
        ]
