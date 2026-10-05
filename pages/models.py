from django.db import models
from django.contrib.contenttypes.fields import GenericRelation
from seo.models import SEOFields, validate_local_path

class Page(SEOFields):
    class Meta:
        verbose_name = 'Страница'
        verbose_name_plural = 'Страницы'
    title = models.CharField(max_length=200, verbose_name='Заголовок')
    slug = models.SlugField(max_length=200, unique=True, verbose_name='Код в адресе (slug)')
    path = models.CharField(max_length=250, unique=True, validators=[validate_local_path], verbose_name='Адрес страницы')
    intro = models.TextField(blank=True, verbose_name='Вступление')
    body = models.TextField('Содержимое HTML', blank=True)
    active = models.BooleanField(default=True, verbose_name='Опубликовано')
    show_in_footer = models.BooleanField(default=False, verbose_name='Ссылка в подвале')
    legal_approved = models.BooleanField(default=False, help_text='Юридические страницы требуют утверждения владельцем.', verbose_name='Текст утверждён владельцем')
    def get_absolute_url(self): return self.path
    def __str__(self): return self.title

class FAQ(models.Model):
    question = models.CharField(max_length=250, verbose_name='Вопрос')
    answer = models.TextField(verbose_name='Ответ')
    city = models.ForeignKey('locations.City', null=True, blank=True, on_delete=models.CASCADE, related_name='faqs', verbose_name='Город')
    page = models.ForeignKey(Page, null=True, blank=True, on_delete=models.CASCADE, related_name='faqs', verbose_name='Страница')
    car = models.ForeignKey('cars.Car', null=True, blank=True, on_delete=models.CASCADE, related_name='faqs', verbose_name='Автомобиль')
    active = models.BooleanField(default=True, verbose_name='Опубликовано')
    sort_order = models.PositiveIntegerField(default=0, verbose_name='Порядок')
    translations = GenericRelation('seo.Translation')
    class Meta:
        ordering = ['sort_order', 'pk']
        verbose_name = 'Вопрос и ответ'
        verbose_name_plural = 'Вопросы и ответы'
    def __str__(self): return self.question
