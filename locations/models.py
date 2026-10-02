from django.db import models
from seo.models import SEOFields, validate_local_path

class City(SEOFields):
    name = models.CharField('Город', max_length=100)
    name_in = models.CharField('Предложный падеж', max_length=120, blank=True)
    slug = models.SlugField(unique=True)
    legacy_path = models.CharField(max_length=250, unique=True, blank=True, validators=[validate_local_path], help_text='Пустое поле: автоматически /slug/. Существующий путь не меняется.')
    description = models.TextField(blank=True)
    body = models.TextField('SEO-текст (HTML)', blank=True)
    address = models.CharField(max_length=250, blank=True)
    phone = models.CharField(max_length=40, blank=True)
    whatsapp = models.CharField(max_length=20, blank=True)
    map_url = models.URLField(blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name = 'Город'
        verbose_name_plural = 'Города'

    def get_absolute_url(self): return self.legacy_path
    def clean(self):
        if not self.legacy_path: self.legacy_path=f'/{self.slug}/'
        super().clean()
    def save(self,*args,**kwargs):
        if not self.legacy_path: self.legacy_path=f'/{self.slug}/'
        return super().save(*args,**kwargs)
    def __str__(self): return self.name
