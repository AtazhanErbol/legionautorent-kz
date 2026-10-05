from urllib.parse import quote
from django.db import models
from django.contrib.contenttypes.fields import GenericRelation
from .validators import validate_image, validate_glb, validate_hero_video
from django.core.validators import MinValueValidator, MaxValueValidator
from .hero import ASSETS

def default_hero_names():
    return {'headlightMaterials':['Headlight_Lens'],'taillightMaterials':['Taillight_Lens'],'headlightNodes':['Headlight_L','Headlight_R'],'wheelNodes':['Wheel_FL','Wheel_FR','Wheel_RL','Wheel_RR']}

class SiteSettings(models.Model):
    name = models.CharField(max_length=100, default='LEGIONAUTORENT', verbose_name='Название')
    phone = models.CharField(max_length=40, default='+7 (705) 727-77-77', verbose_name='Телефон')
    whatsapp = models.CharField(max_length=20, default='77057277777', verbose_name='Номер WhatsApp')
    email = models.EmailField(blank=True, verbose_name='Электронная почта')
    address = models.CharField(max_length=250, blank=True, verbose_name='Адрес')
    hours = models.CharField(max_length=120, blank=True, verbose_name='Часы работы')
    logo = models.ImageField(upload_to='site/', blank=True, validators=[validate_image], verbose_name='Логотип')
    favicon = models.ImageField(upload_to='site/', blank=True, validators=[validate_image], verbose_name='Иконка сайта')
    hero_image = models.ImageField(upload_to='site/', blank=True, validators=[validate_image], verbose_name='Загрузить первый кадр')
    hero_video_file = models.FileField('Загрузить видео', upload_to='site/hero/', blank=True, validators=[validate_hero_video], help_text='MP4 H.264 без звука, до 20 МБ. Новая загрузка заменяет активный путь ниже; старый файл сохраняется.')
    hero_mobile_video_file = models.FileField('Анимация для телефона', upload_to='site/hero/', blank=True, validators=[validate_hero_video], help_text='Необязательный отдельный MP4 без звука. Пустое поле сохраняет текущую анимацию.')
    hero_mobile_video_path = models.CharField('Путь анимации для телефона', max_length=250, blank=True, help_text='Пусто: готовый цикл для утверждённого видео или основной загруженный ролик.')
    hero_mobile_image = models.ImageField('Загрузить кадр для телефона', upload_to='site/hero/', blank=True, validators=[validate_image])
    hero_ending_image = models.ImageField('Загрузить финальный кадр', upload_to='site/hero/', blank=True, validators=[validate_image])
    hero_video_fps = models.PositiveSmallIntegerField('Частота кадров видео', default=60, validators=[MinValueValidator(1), MaxValueValidator(120)], help_text='Для текущего ролика — 60. При замене укажите фактическую частоту кадров.')
    hero_model = models.FileField(upload_to='models/', blank=True, validators=[validate_glb], help_text='Лицензированный GLB до 3 МБ. Draco и meshopt поддерживаются.')
    hero_model_license = models.CharField(max_length=250, blank=True, help_text='Источник и подтверждение прав на модель')
    hero_model_path = models.CharField(max_length=250,default='/static/models/hero.glb',help_text='Локальный путь GLB; для сохранённого hero.glb браузер использует hero-compressed.glb. Загрузка файла выше имеет приоритет.')
    hero_poster_path = models.CharField('Постер первого экрана', max_length=250, default=ASSETS['poster'])
    hero_mobile_poster_path = models.CharField('Постер для телефона', max_length=250, blank=True, default=ASSETS['mobile'])
    hero_ending_path = models.CharField('Финальный кадр', max_length=250, blank=True, default=ASSETS['ending'])
    hero_video_path = models.CharField('Видео первого экрана', max_length=250, blank=True, default=ASSETS['video'], help_text='Локальный MP4 /static/ или /media/. H.264, без звука, ключевой кадр каждые 8 кадров.')
    hero_names = models.JSONField(default=default_hero_names)
    enable_hero_3d = models.BooleanField(default=True)
    enable_hero_video = models.BooleanField('Анимация при прокрутке', default=True)
    hero_placeholder = models.BooleanField(default=True)
    robots_text = models.TextField(blank=True,help_text='Production robots; {sitemap_url} заменяется автоматически. Staging всегда закрыт.', verbose_name='Инструкции robots.txt')
    default_seo_title = models.CharField(max_length=250,default='LEGIONAUTORENT — прокат автомобилей', verbose_name='Запасной Title')
    default_seo_description = models.TextField(default='Аренда автомобилей без водителя в Казахстане. Автопарк, цены и контакты LEGIONAUTORENT.', verbose_name='Запасной Description')
    whatsapp_message = models.TextField(default='Здравствуйте! Интересует аренда автомобиля в LEGIONAUTORENT.', verbose_name='Сообщение в WhatsApp')
    notifications_enabled = models.BooleanField(default=False, verbose_name='Уведомления о заявках')
    hero_title = models.CharField('Финальная подпись', max_length=200, default='Без водителя. Под ваши планы.', help_text='Текст в конце анимации. H1 берётся только из SEO города и здесь не меняется.')
    hero_price_caption = models.CharField('Подпись о цене', max_length=150, blank=True, help_text='Второй этап видео. Если пусто: от 20 000 ₸ / сутки.')
    hero_steps_caption = models.CharField('Три шага — короткая строка', max_length=250, blank=True, help_text='Третий этап видео. Если пусто: звонок, доставка по городу, договор за 10 минут.')
    hero_text = models.TextField(default='Для деловых встреч, городских маршрутов и поездок за город. Выберите свой автомобиль — остальное возьмём на себя.', verbose_name='Описание первого экрана')
    hero_car = models.ForeignKey('cars.Car', null=True, blank=True, on_delete=models.SET_NULL, related_name='+', verbose_name='Автомобиль для резервного режима')
    instagram = models.URLField(blank=True)
    map_url = models.URLField(blank=True, verbose_name='Ссылка на встроенную карту Яндекса')
    footer_text = models.CharField(max_length=250, default='Автомобиль под ваши планы.', verbose_name='Подпись в подвале')
    gtm_id = models.CharField(max_length=30, blank=True, verbose_name='Контейнер Google Tag Manager')
    ga4_id = models.CharField(max_length=30, blank=True, verbose_name='GA4 — справочный ID')
    metrika_id = models.CharField(max_length=30, blank=True, verbose_name='Метрика — справочный ID')
    google_verification = models.CharField(max_length=150, blank=True, verbose_name='Подтверждение Google')
    yandex_verification = models.CharField(max_length=150, blank=True, verbose_name='Подтверждение Яндекса')
    show_partner_section = models.BooleanField(default=True, verbose_name='Показывать блок партнёров')
    partner_title = models.CharField(max_length=200, default='Стать партнером LEGIONAUTORENT', verbose_name='Заголовок')
    partner_description = models.TextField(default='Вы можете стать нашим партнером предоставив нам ваше авто на субаренду.', verbose_name='Описание')
    partner_phone = models.CharField(max_length=40, blank=True, help_text='Если пусто, используется основной телефон', verbose_name='Телефон партнёров')
    partner_whatsapp = models.CharField(max_length=20, blank=True, help_text='Если пусто, используется основной WhatsApp', verbose_name='WhatsApp партнёров')
    partner_whatsapp_message = models.TextField(default='Здравствуйте! Хочу узнать подробнее о партнерстве с LEGIONAUTORENT и передаче автомобиля в субаренду.', verbose_name='Сообщение для партнёров')
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
        for field in ('hero_model_path','hero_poster_path','hero_video_path','hero_mobile_video_path','hero_mobile_poster_path','hero_ending_path'):
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
    kind = models.CharField(max_length=20, choices=KIND, verbose_name='Тип')
    title = models.CharField(max_length=200, verbose_name='Заголовок')
    text = models.TextField(verbose_name='Текст')
    active = models.BooleanField(default=True, verbose_name='Опубликовано')
    sort_order = models.PositiveIntegerField(default=0, verbose_name='Порядок')
    translations = GenericRelation('seo.Translation')

    class Meta:
        ordering = ['sort_order', 'pk']
        verbose_name = 'Блок контента'
        verbose_name_plural = 'Блоки контента'

    def __str__(self): return self.title


class InterfaceText(models.Model):
    source = models.CharField('Исходная подпись', max_length=500, unique=True)
    section = models.CharField('Раздел сайта', max_length=150)
    ru = models.TextField('Русский', blank=True, help_text='Пусто — используется исходная подпись.')
    kk = models.TextField('Қазақша', blank=True, help_text='Пусто — используется существующий перевод сайта.')
    en = models.TextField('English', blank=True, help_text='Пусто — используется существующий перевод сайта.')

    class Meta:
        ordering = ['section', 'source']
        verbose_name = 'Подпись интерфейса'
        verbose_name_plural = 'Тексты и кнопки'

    def __str__(self): return self.source


class SiteSection(models.Model):
    KEYS = [('fleet', 'Автопарк'), ('categories', 'Строка классов'), ('steps', 'Шаги аренды'), ('benefits', 'Преимущества'), ('seo', 'Описание города'), ('faq', 'Вопросы и ответы'), ('partner', 'Партнёрам'), ('contacts', 'Контакты')]
    key = models.CharField('Блок', max_length=30, choices=KEYS, unique=True)
    active = models.BooleanField('Показывать', default=True)
    sort_order = models.PositiveIntegerField('Порядок', default=0)

    class Meta:
        ordering = ['sort_order', 'pk']
        verbose_name = 'Раздел главной и городов'
        verbose_name_plural = 'Порядок разделов'

    @property
    def template_name(self): return f'components/sections/{self.key}.html'

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.key in ('fleet', 'seo') and not self.active:
            raise ValidationError({'active': 'Автопарк и описание города сохраняются для ссылок и SEO. Их содержимое можно изменить в соответствующих разделах.'})

    def __str__(self): return self.get_key_display()


class MenuLink(models.Model):
    from seo.models import validate_local_path
    area = models.CharField('Меню', max_length=20, choices=[('main', 'Шапка'), ('mobile', 'Мобильное меню')])
    label = models.CharField('Подпись RU', max_length=80)
    label_kk = models.CharField('Подпись KZ', max_length=100, blank=True)
    label_en = models.CharField('Подпись EN', max_length=100, blank=True)
    path = models.CharField('Страница сайта', max_length=250, validators=[validate_local_path], help_text='Существующий адрес, например /cars/. Языковой префикс добавляется автоматически.')
    active = models.BooleanField('Показывать', default=True)
    sort_order = models.PositiveIntegerField('Порядок', default=0)

    class Meta:
        ordering = ['sort_order', 'pk']
        verbose_name = 'Ссылка меню'
        verbose_name_plural = 'Навигация'

    @property
    def display_label(self):
        from django.utils.translation import get_language, gettext
        language = get_language()
        return (getattr(self, 'label_' + language, '') if language in ('kk', 'en') else '') or gettext(self.label)

    def __str__(self): return self.label
