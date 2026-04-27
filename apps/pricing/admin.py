from django.contrib import admin

from .models import TicketPrice


@admin.register(TicketPrice)
class TicketPriceAdmin(admin.ModelAdmin):
    list_display = ('session', 'amount', 'currency', 'pricing_source')
    list_filter = ('currency', 'pricing_source')
    search_fields = ('session__movie__title', 'session__hall__name')
    autocomplete_fields = ('session',)
    list_select_related = ('session', 'session__movie', 'session__hall')
    ordering = ('session__start_datetime', 'currency')
