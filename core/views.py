import secrets
from urllib.parse import urlsplit
from django.conf import settings
from django.core import signing
from django.core.paginator import Paginator
from django.db.models import Q, Min
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext as _
from django.utils.translation import get_language
from django.views.decorators.http import require_http_methods, require_GET
from cars.models import Car, CarCategory
from cars.forms import CatalogFilterForm
from locations.models import City
from pages.models import Page, FAQ
from bookings.forms import BookingForm, CONSENT_TEXT
from bookings.spam import allow_request
from core.models import SiteSettings, ContentBlock
from core.i18n import language_url, localized, get_translation
from seo.services import page_seo, schemas, catalog_languages

def present(request, template, context, status=200, **schema_args):
    site = SiteSettings.get_solo()
    request.site_settings = site
    context['schemas'] = schemas(request, context['seo'], site, breadcrumbs=context.get('breadcrumbs'), **schema_args)
    return render(request, template, context, status=status)

def faq_queryset(**kwargs):
    qs=FAQ.objects.filter(active=True, **kwargs).prefetch_related('translations')
    if get_language()!='ru':qs=qs.filter(translations__language=get_language(),translations__published=True)
    return qs

def content_blocks(kind):
    qs=ContentBlock.objects.filter(kind=kind,active=True).prefetch_related('translations')
    if get_language()!='ru':qs=qs.filter(translations__language=get_language(),translations__published=True)
    return qs

@require_GET
def home(request):
    city = get_object_or_404(City.objects.prefetch_related('translations'), legacy_path='/', active=True)
    cars = Car.objects.public().filter(cities=city).with_content()
    context = {'seo': page_seo(request, city), 'city': city, 'featured_cars': cars.filter(featured=True)[:6], 'car_count': cars.count(), 'min_price': cars.aggregate(price=Min('base_price'))['price'], 'benefits': content_blocks('benefit'), 'steps': content_blocks('step'), 'conditions': content_blocks('condition'), 'faqs': faq_queryset(car__isnull=True, page__isnull=True).filter(Q(city=city) | Q(city__isnull=True)), 'search_form': CatalogFilterForm()}
    return present(request, 'home.html', context, city=city)

@require_GET
def catalog(request, category_slug=None):
    category = get_object_or_404(CarCategory.objects.prefetch_related('translations'), slug=category_slug, active=True) if category_slug else None
    qs = Car.objects.public().with_content()
    if category: qs = qs.filter(category=category)
    form = CatalogFilterForm(request.GET or None)
    if form.is_bound:
        if form.is_valid():
            data = form.cleaned_data
            for field, lookup in [('city', 'cities'), ('brand', 'brand'), ('category', 'category'), ('min_price', 'base_price__gte'), ('max_price', 'base_price__lte'), ('transmission', 'transmission'), ('drive', 'drive'), ('seats', 'seats__gte')]:
                if data.get(field) is not None and data.get(field) != '': qs = qs.filter(**{lookup: data[field]})
            if data.get('available'): qs = qs.filter(accepts_requests=True)
            if data.get('q'): qs = qs.filter(Q(name__icontains=data['q']) | Q(brand__name__icontains=data['q']) | Q(model_name__icontains=data['q']))
            sorting = {'price': ('base_price', 'pk'), '-price': ('-base_price', 'pk'), 'new': ('-created_at', 'pk')}.get(data.get('sort'), ('-featured', 'sort_order', 'pk'))
            qs = qs.order_by(*sorting)
        else: qs = qs.none()
    else: qs = qs.order_by('-featured', 'sort_order', 'pk')
    page = Paginator(qs, 12).get_page(request.GET.get('page'))
    params = request.GET.copy(); params.pop('page', None)
    seo = page_seo(request, category, title=_('Автопарк | Legion Auto Rent'), description=_('Выберите автомобиль для аренды без водителя. Цены, фотографии и классы автомобилей в Legion Auto Rent.'), h1=_('Ваш маршрут. Ваш автомобиль.'), noindex=bool(request.GET), available_languages=catalog_languages() if not category else None)
    return present(request, 'catalog.html', {'seo': seo, 'category': category, 'cars': page, 'filter_form': form, 'pagination_query': params.urlencode(), 'breadcrumbs': [(_('Главная'), language_url('/')), (_('Автопарк'), language_url('/cars/'))]})

@require_GET
def car_detail(request, slug):
    car = get_object_or_404(Car.objects.public().with_content().prefetch_related('translations', 'discounts', 'prices'), legacy_path=request.base_path)
    seo = page_seo(request, car)
    if car.main_image: seo['og_image'] = settings.SITE_URL + car.main_image.display_url
    related = Car.objects.public().with_content().filter(category=car.category).exclude(pk=car.pk)[:3]
    breadcrumbs = [(_('Главная'), language_url('/')), (_('Автопарк'), language_url('/cars/')), (localized(car, 'name'), language_url(car.legacy_path))]
    return present(request, 'car_detail.html', {'seo': seo, 'car': car, 'related_cars': related, 'faqs': faq_queryset(car=car), 'conditions': content_blocks('condition'), 'breadcrumbs': breadcrumbs, 'car_whatsapp_message': _('Здравствуйте! Интересует аренда %(car)s.') % {'car': car.name}}, car=car)

@require_GET
def city_page(request, slug):
    city = get_object_or_404(City.objects.prefetch_related('translations'), legacy_path=request.base_path, active=True)
    cars = Car.objects.public().with_content().filter(cities=city)
    return present(request, 'city.html', {'seo': page_seo(request, city), 'city': city, 'cars': cars, 'faqs': faq_queryset(city=city), 'breadcrumbs': [(_('Главная'), language_url('/')), (localized(city, 'name'), language_url(city.legacy_path))]}, city=city)

@require_GET
def static_page(request, slug):
    page = get_object_or_404(Page.objects.prefetch_related('translations'), path=request.base_path, active=True)
    return present(request, 'page.html', {'seo': page_seo(request, page), 'page': page, 'faqs': faq_queryset(page=page), 'breadcrumbs': [(_('Главная'), language_url('/')), (localized(page, 'title'), language_url(page.path))]})

@require_GET
def content_page(request, slug):
    if City.objects.filter(legacy_path=request.base_path, active=True).exists():
        return city_page(request, slug)
    return static_page(request, slug)

@require_http_methods(['GET', 'POST'])
def booking(request):
    initial = {}
    car_id = request.GET.get('car', '')
    car = Car.objects.public().filter(pk=int(car_id)).first() if car_id.isdigit() else None
    if car:
        initial['car'] = car.pk
        initial['city'] = car.cities.filter(active=True).first().pk
    source = car.legacy_path if car else '/cars/'
    initial['source_token'] = signing.dumps(source, salt='booking-source')
    form = BookingForm(request.POST or None, initial=initial)
    status = 200
    if request.method == 'POST':
        if not allow_request(request):
            form.is_valid(); form.add_error(None, _('Слишком много попыток. Попробуйте через 15 минут.')); status = 429
        elif form.is_valid():
            try: source = signing.loads(form.cleaned_data['source_token'], salt='booking-source', max_age=86400)
            except signing.BadSignature:
                form.add_error(None, _('Срок действия формы истёк. Обновите страницу.')); status = 400
            else:
                lead = form.save(commit=False)
                lead.source_page = language_url(source)
                lead.consent_text = CONSENT_TEXT
                attribution = request.session.get('attribution', {})
                for key in ['landing_page', 'referrer', 'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term']: setattr(lead, key, attribution.get(key, ''))
                lead.save()
                request.session['booking_success'] = secrets.token_urlsafe(20)
                return HttpResponseRedirect(language_url('/request-success/'))
        else: status = 400
    seo = page_seo(request, title=_('Заявка на аренду | Legion Auto Rent'), h1=_('Забронировать автомобиль'), noindex=True)
    return present(request, 'booking.html', {'seo': seo, 'form': form, 'selected_car': car, 'breadcrumbs': [(_('Главная'), language_url('/')), (_('Заявка на аренду'), language_url('/booking/'))]}, status=status)

@require_GET
def success(request):
    valid = bool(request.session.pop('booking_success', None))
    seo = page_seo(request, title=_('Заявка отправлена | Legion Auto Rent'), h1=_('Заявка отправлена'), noindex=True)
    return present(request, 'success.html', {'seo': seo, 'submitted': valid})

def not_found(request, exception=None):
    seo = page_seo(request, title=_('Страница не найдена | Legion Auto Rent'), h1=_('Здесь начинается другой маршрут'), noindex=True)
    return present(request, '404.html', {'seo': seo}, status=404)
