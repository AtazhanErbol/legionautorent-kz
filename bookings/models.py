from django.db import models

class Lead(models.Model):
    name = models.CharField('Имя', max_length=120)
    phone = models.CharField('Телефон', max_length=30)
    city = models.ForeignKey('locations.City', on_delete=models.PROTECT)
    comment = models.TextField(blank=True)
    consent = models.BooleanField(default=False)
    consent_text = models.TextField(blank=True)
    manager_note = models.TextField('Заметка менеджера', blank=True)
    source_page = models.CharField(max_length=600, blank=True)
    landing_page = models.CharField(max_length=600, blank=True)
    referrer = models.CharField(max_length=600, blank=True)
    utm_source = models.CharField(max_length=200, blank=True)
    utm_medium = models.CharField(max_length=200, blank=True)
    utm_campaign = models.CharField(max_length=200, blank=True)
    utm_content = models.CharField(max_length=200, blank=True)
    utm_term = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta: abstract = True
    def __str__(self): return f'{self.name} — {self.phone}'

class BookingRequest(Lead):
    STATUS = [('NEW', 'Новая'), ('CONTACTED', 'Связались'), ('CONFIRMED', 'Подтверждена'), ('CANCELLED', 'Отменена'), ('COMPLETED', 'Завершена')]
    car = models.ForeignKey('cars.Car', null=True, blank=True, on_delete=models.PROTECT)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default='NEW', db_index=True)
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Заявка на аренду'
        verbose_name_plural = 'Заявки на аренду'
        constraints = [models.CheckConstraint(condition=models.Q(start_date__isnull=True, end_date__isnull=True) | models.Q(start_date__isnull=False, end_date__isnull=False, end_date__gt=models.F('start_date')), name='valid_booking_dates')]

class RateLimitBucket(models.Model):
    key = models.CharField(max_length=100, unique=True)
    hits = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
