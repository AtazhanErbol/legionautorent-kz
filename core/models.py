from urllib.parse import quote
from django.db import models
from django.contrib.contenttypes.fields import GenericRelation
from .validators import validate_image, validate_glb

def default_hero_names():
    return {'headlightMaterials':['Headlight_Lens'],'taillightMaterials':['Taillight_Lens'],'headlightNodes':['Headlight_L','Headlight_R'],'wheelNodes':['Wheel_FL','Wheel_FR','Wheel_RL','Wheel_RR']}

class SiteSettings(models.Model):
    name = models.CharField(max_length=100, default='Legion Auto Rent')
    phone = models.CharField(max_length=40, default='+7 (705) 727-77-77')
    whatsapp = models.CharField(max_length=20, default='77057277777')
    email = models.EmailField(blank=True)
    address = models.CharField(max_length=250, blank=True)
    hours = models.CharField(max_length=120, blank=True)
    logo = models.ImageField(upload_to='site/', blank=True, validators=[validate_image])
    favicon = models.ImageField(upload_to='site/', blank=True, validators=[validate_image])
    hero_image = models.ImageField(upload_to='site/', blank=True, validators=[validate_image])
    hero_model = models.FileField(upload_to='models/', blank=True, validators=[validate_glb], help_text='Лицензированный GLB до 3 МБ. Draco и meshopt поддерживаются.')
    hero_model_license = models.CharField(max_length=250, blank=True, help_text='Источник и подтверждение прав на модель')
    hero_model_path = models.CharField(max_length=250,default='/static/models/hero.glb',help_text='Локальный путь GLB; для сохранённого hero.glb браузер использует hero-compressed.glb. Загрузка файла выше имеет приоритет.')
    hero_poster_path = models.CharField(max_length=250,default='/static/img/hero-poster.webp')
    hero_video_path = models.CharField(max_length=250,blank=True,help_text='Необязательный локальный WebM; показывается вместо 3D только по настройке.')
    hero_names = models.JSONField(default=default_hero_names)
    enable_hero_3d = models.BooleanField(default=True)
    enable_hero_video = models.BooleanField(default=False)
    hero_placeholder = models.BooleanField(default=True)
    robots_text = models.TextField(blank=True,help_text='Production robots; {sitemap_url} заменяется автоматически. Staging всегда закрыт.')
    default_seo_title = models.CharField(max_length=250,default='Legion Auto Rent — прокат автомобилей')
    default_seo_description = models.TextField(default='Аренда автомобилей без водителя в Казахстане. Автопарк, цены и контакты Legion Auto Rent.')
    whatsapp_message = models.TextField(default='Здравствуйте! Интересует аренда автомобиля в Legion Auto Rent.')
    notifications_enabled = models.BooleanField(default=False)
    hero_title = models.CharField(max_length=200, default='Прокат авто без водителя в Астане')
    hero_text = models.TextField(default='Для деловых встреч, городских маршрутов и поездок за город. Выберите свой автомобиль — остальное возьмём на себя.')
    hero_car = models.ForeignKey('cars.Car', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    instagram = models.URLField(blank=True)
    map_url = models.URLField(blank=True)
    footer_text = models.CharField(max_length=250, default='Автомобиль под ваши планы.')
    gtm_id = models.CharField(max_length=30, blank=True)
    ga4_id = models.CharField(max_length=30, blank=True)
    metrika_id = models.CharField(max_length=30, blank=True)
    google_verification = models.CharField(max_length=150, blank=True)
    yandex_verification = models.CharField(max_length=150, blank=True)
    show_partner_section = models.BooleanField(default=True)
    partner_title = models.CharField(max_length=200, default='Стать партнером Легионавто')
    partner_description = models.TextField(default='Вы можете стать нашим партнером предоставив нам ваше авто на субаренду.')
    partner_phone = models.CharField(max_length=40, blank=True, help_text='Если пусто, используется основной телефон')
    partner_whatsapp = models.CharField(max_length=20, blank=True, help_text='Если пусто, используется основной WhatsApp')
    partner_whatsapp_message = models.TextField(default='Здравствуйте! Хочу узнать подробнее о партнерстве с Легионавто и передаче автомобиля в субаренду.')
    translations = GenericRelation('seo.Translation')

    class Meta:
        verbose_name = 'Настройки сайта'
        verbose_name_plural = 'Настройки сайта'

    def clean(self):
        super().clean()
        from django.core.exceptions import ValidationError
        import re
        for field, pattern in [('gtm_id', r'GTM-[A-Z0-9]+'), ('ga4_id', r'G-[A-Z0-9]+'), ('metrika_id', r'\d+'), ('whatsapp', r'\d{10,15}'), ('partner_whatsapp', r'\d{10,15}')]:
            value = getattr(self, field)
            if value and not re.fullmatch(pattern, value): raise ValidationError({field: 'Некорректное значение.'})
        if self.hero_model and not self.hero_model_license: raise ValidationError({'hero_model_license': 'Укажите источник лицензии 3D-модели.'})
        for field in ('hero_model_path','hero_poster_path','hero_video_path'):
            value=getattr(self,field)
            if value and (not value.startswith(('/static/','/media/')) or '..' in value or '\\' in value or '?' in value or '#' in value):
                raise ValidationError({field:'Нужен локальный путь /static/ или /media/ без переходов между каталогами.'})
        if not isinstance(self.hero_names,dict) or any(not isinstance(v,list) or any(not isinstance(n,str) for n in v) for v in self.hero_names.values()):
            raise ValidationError({'hero_names':'Конфигурация имён: объект с массивами строк.'})

    def save(self, *args, **kwargs):
        self.pk = 1
        self.full_clean()
        return super().save(*args, **kwargs)

    @classmethod
    def get_solo(cls):
        return cls.objects.select_related('hero_car').prefetch_related('translations').filter(pk=1).first() or cls()

    @property
    def phone_digits(self):
        return '+' + ''.join(c for c in self.phone if c.isdigit())

    def whatsapp_url(self, text=None):
        from core.i18n import localized
        return f'https://wa.me/{self.whatsapp}?text={quote(text or localized(self,"whatsapp_message"))}'

    def __str__(self): return self.name

class ContentBlock(models.Model):
    KIND = [('benefit', 'Преимущество'), ('step', 'Шаг аренды'), ('condition', 'Условие аренды')]
    kind = models.CharField(max_length=20, choices=KIND)
    title = models.CharField(max_length=200)
    text = models.TextField()
    active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    translations = GenericRelation('seo.Translation')

    class Meta:
        ordering = ['sort_order', 'pk']
        verbose_name = 'Блок контента'
        verbose_name_plural = 'Блоки контента'

    def __str__(self): return self.title
