from django.contrib import admin

from .models import Hall


@admin.register(Hall)
class HallAdmin(admin.ModelAdmin):
    list_display = ('name', 'rows', 'seats_per_row', 'capacity')
    search_fields = ('name',)
    ordering = ('name',)

    @admin.display(description='Capacity')
    def capacity(self, obj):
        return obj.rows * obj.seats_per_row
