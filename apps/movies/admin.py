from django.contrib import admin

from .models import Movie


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'genre',
        'age_rating',
        'duration',
        'release_date',
        'is_active',
    )
    list_filter = ('is_active', 'genre', 'age_rating', 'release_date')
    search_fields = ('title', 'description')
    list_editable = ('is_active',)
    ordering = ('title',)
    readonly_fields = ()
