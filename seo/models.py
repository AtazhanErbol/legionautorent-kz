from urllib.parse import urlsplit
from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.contenttypes.fields import GenericRelation, GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class SEOFields(models.Model):
    seo_title = models.CharField('SEO Title', max_length=250, blank=True)
    seo_description = models.TextField('Meta Description', blank=True)
    seo_h1 = models.CharField('H1', max_length=250, blank=True)
    canonical_url = models.URLField('Canonical override', blank=True)
    robots = models.CharField(max_length=40, choices=[('index,follow', 'Индексировать'), ('noindex,follow', 'Не индексировать')], default='index,follow')
    og_title = models.CharField(max_length=250, blank=True)
    og_description = models.TextField(blank=True)
    og_image = models.URLField(blank=True)
    legacy_meta = models.JSONField(default=dict,blank=True,help_text='Исходные Open Graph/Twitter поля сохранены для точной миграции.')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    translations = GenericRelation('seo.Translation')

    class Meta:
        abstract = True

    @property
    def indexable(self):
        return self.active and 'noindex' not in self.robots

    def clean(self):
        super().clean()
        from django.conf import settings
        if self.canonical_url and self.canonical_url != settings.SITE_URL + self.get_absolute_url():
            raise ValidationError({'canonical_url': 'Canonical должен совпадать с собственным публичным URL.'})


def validate_local_path(value):
    if not value.startswith('/') or value.startswith('//') or urlsplit(value).netloc or '?' in value or '#' in value or '\\' in value or any(ord(c) < 32 for c in value):
        raise ValidationError('Нужен абсолютный локальный путь без query, fragment и домена.')


class Translation(models.Model):
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField()
    content_object = GenericForeignKey()
    language = models.CharField('Язык', max_length=2, choices=[('kk', 'KZ / Қазақша'), ('en', 'EN / English')])
    published = models.BooleanField('Перевод проверен и опубликован', default=False)
    name = models.CharField('Название', max_length=250, blank=True)
    title = models.CharField('SEO Title / заголовок блока', max_length=250, blank=True)
    description = models.TextField('Meta Description', blank=True)
    h1 = models.CharField('H1', max_length=250, blank=True)
    content = models.TextField('Контент / ответ / HTML', blank=True)
    intro = models.TextField('Вводный текст', blank=True)
    address = models.CharField(max_length=250,blank=True)
    hours = models.CharField(max_length=120,blank=True)
    fuel = models.CharField(max_length=100,blank=True)
    color = models.CharField(max_length=100,blank=True)
    caption = models.CharField(max_length=250,blank=True)
    whatsapp_message = models.TextField(blank=True)
    og_title = models.CharField(max_length=250, blank=True)
    og_description = models.TextField(blank=True)
    hero_title = models.CharField('Финальная подпись Hero (не H1)', max_length=250, blank=True)
    hero_text = models.TextField(blank=True)
    partner_title = models.CharField(max_length=250, blank=True)
    partner_description = models.TextField(blank=True)
    partner_whatsapp_message = models.TextField(blank=True)
    footer_text = models.CharField(max_length=250, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['content_type', 'object_id', 'language'], name='unique_object_translation')]
        verbose_name = 'Перевод'
        verbose_name_plural = 'Переводы KZ / EN'
    def clean(self):
        super().clean()
        if self.published:
            obj = self.content_object
            if isinstance(obj, SEOFields) and not all([self.title, self.description, self.h1, self.content]):
                raise ValidationError('Для публикации SEO-страницы заполните Title, Description, H1 и контент.')
            if obj and obj._meta.model_name in ('city','car','carcategory') and not self.name:
                raise ValidationError('Для публикации заполните название на выбранном языке.')
            if obj and obj._meta.model_name in ('faq', 'contentblock') and not all([self.title, self.content]):
                raise ValidationError('Для публикации заполните заголовок и текст.')
            if obj and obj._meta.model_name == 'carimage' and not self.name:
                raise ValidationError('Для публикации заполните alt изображения в поле «Название».')
            if obj and obj._meta.model_name == 'carspecification' and not all([self.name,self.content]):
                raise ValidationError('Для публикации заполните название характеристики и значение.')
            if obj and obj._meta.model_name == 'sitesettings' and not all([self.hero_title, self.hero_text, self.partner_title, self.partner_description, self.partner_whatsapp_message, self.footer_text]):
                raise ValidationError('Заполните перевод Hero, footer и партнёрского блока.')
    def __str__(self): return f'{self.language}: {self.content_object}'
    def save(self,*args,**kwargs):
        self.full_clean()
        return super().save(*args,**kwargs)


class Redirect(models.Model):
    old_path = models.CharField(max_length=500, unique=True, validators=[validate_local_path])
    new_path = models.CharField(max_length=500, validators=[validate_local_path])
    status_code = models.PositiveSmallIntegerField(default=301, choices=[(301, '301 Permanent'), (302, '302 Temporary')])
    active = models.BooleanField(default=True)

    def clean(self):
        super().clean()
        validate_local_path(self.old_path)
        validate_local_path(self.new_path)
        if self.old_path == self.new_path: raise ValidationError('Redirect на самого себя запрещён.')
        if self.active and Redirect.objects.filter(active=True).exclude(pk=self.pk).filter(models.Q(old_path=self.new_path) | models.Q(new_path=self.old_path)).exists():
            raise ValidationError('Цепочки и циклы redirect запрещены; укажите конечный URL.')

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.old_path} → {self.new_path}'
