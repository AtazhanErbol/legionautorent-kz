from django.db import models
from seo.models import SEOFields, validate_local_path

class City(SEOFields):
    name = models.CharField('Город', max_length=100)
    name_in = models.CharField('Предложный падеж', max_length=120, blank=True)
    slug = models.SlugField(unique=True, verbose_name='Код в адресе (slug)')
    legacy_path = models.CharField(max_length=250, unique=True, blank=True, validators=[validate_local_path], help_text='Пустое поле: автоматически /slug/. Существующий путь не меняется.', verbose_name='Адрес страницы')
    description = models.TextField(blank=True, verbose_name='Описание')
    hero_text = models.TextField(blank=True, verbose_name='Описание первого экрана')
    hours = models.CharField(max_length=120,blank=True, verbose_name='Часы работы')
    body = models.TextField('SEO-текст (HTML)', blank=True)
    address = models.CharField(max_length=250, blank=True, verbose_name='Адрес')
    phone = models.CharField(max_length=40, blank=True, verbose_name='Телефон')
    whatsapp = models.CharField(max_length=20, blank=True, verbose_name='Номер WhatsApp')
    map_url = models.URLField(blank=True, verbose_name='Ссылка на встроенную карту Яндекса')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name='Широта')
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, verbose_name='Долгота')
    active = models.BooleanField(default=True, verbose_name='Опубликовано')
    sort_order = models.PositiveIntegerField(default=0, verbose_name='Порядок')

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
