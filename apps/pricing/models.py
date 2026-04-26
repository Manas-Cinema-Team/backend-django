from django.db import models
from django.db.models import Q


class TicketCurrency(models.TextChoices):
    KGS = 'KGS', 'KGS'
    USD = 'USD', 'USD'
    EUR = 'EUR', 'EUR'


class PricingSource(models.TextChoices):
    MANUAL = 'manual', 'Manual'
    PROMOTION = 'promotion', 'Promotion'
    IMPORT = 'import', 'Import'


class TicketPrice(models.Model):
    session = models.ForeignKey(
        'screenings.MovieSession',
        on_delete=models.CASCADE,
        related_name='ticket_prices',
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(
        max_length=3,
        choices=TicketCurrency.choices,
        default=TicketCurrency.KGS,
    )
    pricing_source = models.CharField(
        max_length=16,
        choices=PricingSource.choices,
        default=PricingSource.MANUAL,
        db_index=True,
    )

    class Meta:
        ordering = ['session_id', 'currency']
        indexes = [
            models.Index(fields=['session', 'currency'], name='pricing_session_currency_idx'),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name='pricing_amount_gt_zero',
            ),
            models.UniqueConstraint(
                fields=['session', 'currency'],
                name='pricing_unique_session_currency',
            ),
        ]

    def __str__(self):
        return f'{self.session} - {self.amount} {self.currency}'
