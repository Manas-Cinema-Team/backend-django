from django.db import models
from django.db.models import Q


class Hall(models.Model):
    name = models.CharField(max_length=100, unique=True)
    rows = models.PositiveSmallIntegerField()
    seats_per_row = models.PositiveSmallIntegerField()
    schema_metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['rows', 'seats_per_row'], name='halls_capacity_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(rows__gt=0),
                name='halls_rows_gt_zero',
            ),
            models.CheckConstraint(
                condition=Q(seats_per_row__gt=0),
                name='halls_seats_per_row_gt_zero',
            ),
        ]

    def __str__(self):
        return self.name
