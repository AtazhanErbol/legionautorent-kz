from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Prefetch
from django.core.validators import MinValueValidator, MaxValueValidator
from seo.models import SEOFields, validate_local_path
from core.validators import validate_image
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.fields import GenericRelation

class CarBrand(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    def __str__(self): return self.name

class CarCategory(SEOFields):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    class Meta:
        ordering = ['sort_order', 'pk']
        verbose_name = 'Класс автомобиля'
        verbose_name_plural = 'Классы автомобилей'
    def get_absolute_url(self): return f'/category/{self.slug}/'
    def __str__(self): return self.name

class CarFeature(models.Model):
    name = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.name

class CarQuerySet(models.QuerySet):
    def public(self):
        return self.filter(active=True, category__active=True, cities__active=True).distinct()
    def with_content(self):
        return self.select_related('brand', 'category').prefetch_related('cities__translations', 'translations', 'category__translations', 'features', Prefetch('images', queryset=CarImage.objects.prefetch_related('translations').order_by('-is_main', 'sort_order', 'pk')))

class Car(SEOFields):
    name = models.CharField('Название', max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    legacy_path = models.CharField(max_length=250, unique=True, blank=True, validators=[validate_local_path], help_text='Пустое поле: автоматически /car/slug. Существующий путь не меняется.')
    legacy_id = models.CharField(max_length=250, unique=True, blank=True)
    brand = models.ForeignKey(CarBrand, on_delete=models.PROTECT)
    model_name = models.CharField(max_length=200, blank=True)
    category = models.ForeignKey(CarCategory, on_delete=models.PROTECT)
    cities = models.ManyToManyField('locations.City', related_name='cars')
    features = models.ManyToManyField(CarFeature, blank=True)
    base_price = models.DecimalField('Цена в сутки, ₸', max_digits=12, decimal_places=0, validators=[MinValueValidator(1)])
    year = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(1950), MaxValueValidator(2100)])
    engine = models.CharField(max_length=100, blank=True)
    transmission = models.CharField(max_length=20, blank=True, choices=[('automatic', _('Автомат')), ('manual', _('Механика'))])
    drive = models.CharField(max_length=20, blank=True, choices=[('front', _('Передний')), ('rear', _('Задний')), ('all', _('Полный'))])
    seats = models.PositiveSmallIntegerField(null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(20)])
    color = models.CharField(max_length=100, blank=True)
    fuel = models.CharField(max_length=100,blank=True)
    doors = models.PositiveSmallIntegerField(null=True,blank=True,validators=[MinValueValidator(1),MaxValueValidator(10)])
    deposit = models.DecimalField(max_digits=12,decimal_places=0,null=True,blank=True,validators=[MinValueValidator(0)])
    mileage_limit = models.PositiveIntegerField(null=True,blank=True)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    featured = models.BooleanField(default=False)
    accepts_requests = models.BooleanField('Принимать заявки', default=True, help_text='Это не проверка свободных дат.')
    sort_order = models.PositiveIntegerField(default=0)
    objects = CarQuerySet.as_manager()

    class Meta:
        ordering = ['sort_order', 'pk']
        verbose_name = 'Автомобиль'
        verbose_name_plural = 'Автомобили'
        indexes = [models.Index(fields=['active', 'base_price']), models.Index(fields=['featured', 'sort_order'])]

    def get_absolute_url(self): return self.legacy_path
    def clean(self):
        if not self.legacy_path: self.legacy_path=f'/car/{self.slug}'
        if not self.legacy_id:
            import uuid
            self.legacy_id='cms:'+str(uuid.uuid4())
        super().clean()
    def save(self,*args,**kwargs):
        if not self.legacy_path or not self.legacy_id:self.clean()
        return super().save(*args,**kwargs)
    @property
    def main_image(self): return next(iter(self.images.all()), None)
    def __str__(self): return self.name

class CarImage(models.Model):
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='images')
    original = models.ImageField(upload_to='cars/originals/', validators=[validate_image])
    image = models.ImageField(upload_to='cars/webp/', blank=True, validators=[validate_image])
    small = models.ImageField(upload_to='cars/webp/', blank=True, validators=[validate_image])
    card_image = models.ImageField(upload_to='cars/webp/', blank=True, validators=[validate_image])
    card_small = models.ImageField(upload_to='cars/webp/', blank=True, validators=[validate_image])
    card_width = models.PositiveIntegerField(default=960)
    card_height = models.PositiveIntegerField(default=619)
    legacy_url = models.URLField(max_length=600, blank=True)
    alt = models.CharField(max_length=250, blank=True)
    caption = models.CharField(max_length=250, blank=True)
    is_main = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    width = models.PositiveIntegerField(default=1200)
    height = models.PositiveIntegerField(default=800)
    variants = models.JSONField(default=dict,blank=True)
    translations = GenericRelation('seo.Translation')
    class Meta:
        ordering = ['-is_main', 'sort_order', 'pk']
        constraints = [models.UniqueConstraint(fields=['car', 'legacy_url'], condition=~models.Q(legacy_url=''), name='unique_legacy_car_image'), models.UniqueConstraint(fields=['car'], condition=models.Q(is_main=True), name='one_main_image_per_car')]
    @property
    def display_url(self): return (self.image or self.original).url if (self.image or self.original) else ''
    @property
    def srcset(self): return f'{self.small.url} {min(640, self.width)}w, {self.image.url} {self.width}w' if self.small and self.image and self.width > 640 else ''
    @property
    def card_url(self): return self.card_image.url if self.card_image else self.display_url
    @property
    def card_srcset(self): return f'{self.card_small.url} {min(640,self.card_width)}w, {self.card_image.url} {self.card_width}w' if self.card_small and self.card_image and self.card_width>640 else ''
    @property
    def card_display_width(self):return self.card_width if self.card_image else self.width
    @property
    def card_display_height(self):return self.card_height if self.card_image else self.height
    @property
    def avif_srcset(self):
        return ', '.join(f'/media/{path} {size}w' for size,path in self.variants.get('avif',{}).items())
    @property
    def card_avif_srcset(self):
        return ', '.join(f'/media/{path} {size}w' for size,path in self.variants.get('card_avif',{}).items())
    def __str__(self): return self.alt or self.car.name
    def save(self,*args,**kwargs):
        if self.original and not self.original._committed:
            from io import BytesIO
            import uuid
            from PIL import Image,ImageOps
            from django.core.files.base import ContentFile
            self.original.seek(0);source=Image.open(self.original)
            alpha='A' in source.getbands() or 'transparency' in source.info
            source=ImageOps.exif_transpose(source).convert('RGBA' if alpha else 'RGB')
            token=uuid.uuid4().hex
            for size,field in [(640,'small'),(1200,'image')]:
                image=source.copy();image.thumbnail((size,1000));output=BytesIO();image.save(output,'WEBP',quality=82,method=6)
                getattr(self,field).save(f'{token}-{size}.webp',ContentFile(output.getvalue()),save=False)
                if size==1200:self.width,self.height=image.size
            for size,field in [(640,'card_small'),(960,'card_image')]:
                width=min(size,source.width,int(source.height*1.55));height=round(width/1.55)
                image=ImageOps.fit(source,(width,height));output=BytesIO();image.save(output,'WEBP',quality=76,method=6)
                getattr(self,field).save(f'{token}-card-{size}.webp',ContentFile(output.getvalue()),save=False)
                if size==960:self.card_width,self.card_height=image.size
            self.original.seek(0)
            from cars.images import generate_variants
            self.variants=generate_variants(source,token)
        return super().save(*args,**kwargs)

class CarPrice(models.Model):
    translations=GenericRelation('seo.Translation')
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='prices')
    min_days = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    max_days = models.PositiveIntegerField(null=True, blank=True, validators=[MinValueValidator(1)])
    daily_price = models.DecimalField(max_digits=12, decimal_places=0, validators=[MinValueValidator(1)])
    label = models.CharField(max_length=100, blank=True)
    deposit = models.DecimalField(max_digits=12,decimal_places=0,null=True,blank=True,validators=[MinValueValidator(0)])
    mileage_limit = models.PositiveIntegerField(null=True,blank=True)
    class Meta: ordering = ['min_days']
    def clean(self):
        super().clean()
        if self.max_days and self.max_days < self.min_days: raise ValidationError('Окончание диапазона раньше начала.')
        overlap = CarPrice.objects.filter(car_id=self.car_id).exclude(pk=self.pk).filter(models.Q(max_days__isnull=True) | models.Q(max_days__gte=self.min_days))
        if self.max_days: overlap = overlap.filter(min_days__lte=self.max_days)
        if overlap.exists(): raise ValidationError('Диапазоны тарифов не должны пересекаться.')
    def __str__(self): return self.label or f'{self.min_days}–{self.max_days or "∞"} дней'

class CarDiscount(models.Model):
    translations=GenericRelation('seo.Translation')
    car = models.ForeignKey(Car, on_delete=models.CASCADE, related_name='discounts')
    label = models.CharField(max_length=100)
    min_days = models.PositiveIntegerField()
    max_days = models.PositiveIntegerField(null=True, blank=True)
    percent = models.PositiveSmallIntegerField(validators=[MaxValueValidator(100)])
    class Meta: ordering = ['min_days']
    def __str__(self): return f'{self.label}: {self.percent}%'

class CarSpecification(models.Model):
    car=models.ForeignKey(Car,on_delete=models.CASCADE,related_name='extra_specs')
    name=models.CharField(max_length=100)
    value=models.CharField(max_length=250)
    sort_order=models.PositiveIntegerField(default=0)
    translations=GenericRelation('seo.Translation')
    class Meta:ordering=['sort_order','pk']
    def __str__(self):return f'{self.name}: {self.value}'
