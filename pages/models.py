from django.db import models
from django.contrib.contenttypes.fields import GenericRelation
from seo.models import SEOFields, validate_local_path

class Page(SEOFields):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    path = models.CharField(max_length=250, unique=True, validators=[validate_local_path])
    intro = models.TextField(blank=True)
    body = models.TextField('Содержимое HTML', blank=True)
    active = models.BooleanField(default=True)
    show_in_footer = models.BooleanField(default=False)
    legal_approved = models.BooleanField(default=False, help_text='Юридические страницы требуют утверждения владельцем.')
    def get_absolute_url(self): return self.path
    def __str__(self): return self.title

class FAQ(models.Model):
    question = models.CharField(max_length=250)
    answer = models.TextField()
    city = models.ForeignKey('locations.City', null=True, blank=True, on_delete=models.CASCADE, related_name='faqs')
    page = models.ForeignKey(Page, null=True, blank=True, on_delete=models.CASCADE, related_name='faqs')
    car = models.ForeignKey('cars.Car', null=True, blank=True, on_delete=models.CASCADE, related_name='faqs')
    active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    translations = GenericRelation('seo.Translation')
    class Meta:
        ordering = ['sort_order', 'pk']
        verbose_name = 'Вопрос и ответ'
        verbose_name_plural = 'Вопросы и ответы'
    def __str__(self): return self.question
