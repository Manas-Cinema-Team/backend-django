from django.db import models
from django.db.models import F, Q


class MovieSession(models.Model):
    movie = models.ForeignKey(
        'movies.Movie',
        on_delete=models.PROTECT,
        related_name='sessions',
    )
    hall = models.ForeignKey(
        'halls.Hall',
        on_delete=models.PROTECT,
        related_name='sessions',
    )
    start_datetime = models.DateTimeField(db_index=True)
    end_datetime = models.DateTimeField()
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['start_datetime']
        indexes = [
            models.Index(fields=['movie', 'start_datetime'], name='screenings_movie_start_idx'),
            models.Index(fields=['hall', 'start_datetime'], name='screenings_hall_start_idx'),
            models.Index(fields=['is_active', 'start_datetime'], name='screenings_active_start_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_datetime__gt=F('start_datetime')),
                name='screenings_end_after_start',
            ),
            models.UniqueConstraint(
                fields=['hall', 'start_datetime'],
                name='screenings_unique_hall_start',
            ),
        ]

    def __str__(self):
        return f'{self.movie} @ {self.hall} ({self.start_datetime:%Y-%m-%d %H:%M})'
