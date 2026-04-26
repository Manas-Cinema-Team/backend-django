from django.db import models
from django.db.models import Q


class MovieGenre(models.TextChoices):
    ACTION = 'action', 'Action'
    COMEDY = 'comedy', 'Comedy'
    DRAMA = 'drama', 'Drama'
    FANTASY = 'fantasy', 'Fantasy'
    HORROR = 'horror', 'Horror'
    SCI_FI = 'sci_fi', 'Sci-Fi'
    THRILLER = 'thriller', 'Thriller'
    ANIMATION = 'animation', 'Animation'


class AgeRating(models.TextChoices):
    AGE_0 = '0+', '0+'
    AGE_6 = '6+', '6+'
    AGE_12 = '12+', '12+'
    AGE_16 = '16+', '16+'
    AGE_18 = '18+', '18+'


class Movie(models.Model):
    title = models.CharField(max_length=255, db_index=True)
    description = models.TextField()
    genre = models.CharField(max_length=32, choices=MovieGenre.choices, db_index=True)
    duration = models.PositiveSmallIntegerField(help_text='Duration in minutes.')
    age_rating = models.CharField(max_length=3, choices=AgeRating.choices, db_index=True)
    poster_url = models.URLField(max_length=500, blank=True)
    release_date = models.DateField()
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['title']
        indexes = [
            models.Index(fields=['is_active', 'release_date'], name='movies_active_release_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(duration__gt=0),
                name='movies_movie_duration_gt_zero',
            ),
        ]

    def __str__(self):
        return self.title
