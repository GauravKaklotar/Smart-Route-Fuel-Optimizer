"""
Admin registration for the routing application.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import FuelStation


class HasCoordinatesFilter(admin.SimpleListFilter):
    title = _('geocoded')
    parameter_name = 'has_coordinates'

    def lookups(self, request, model_admin):
        return (
            ('yes', _('Yes')),
            ('no', _('No')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(latitude__isnull=False, longitude__isnull=False)
        if self.value() == 'no':
            return queryset.filter(latitude__isnull=True)
        return queryset


@admin.register(FuelStation)
class FuelStationAdmin(admin.ModelAdmin):
    """Admin interface for FuelStation model."""

    list_display = (
        "opis_id",
        "truckstop_name",
        "city",
        "state",
        "retail_price",
        "has_coordinates",
    )
    list_filter = ("state", HasCoordinatesFilter)
    search_fields = ("opis_id", "truckstop_name", "city")
    readonly_fields = ("opis_id",)
    ordering = ("state", "city")

    @admin.display(description="Geocoded", boolean=True)
    def has_coordinates(self, obj: FuelStation) -> bool:
        """Return True if the station has geocoded coordinates."""
        return obj.latitude is not None and obj.longitude is not None
