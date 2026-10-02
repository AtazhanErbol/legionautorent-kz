import secrets
from django.conf import settings
from django.core import signing
from django.core.paginator import Paginator
from django.db import connection
from django.db.models import Q,Min
from django.http import Http404,HttpResponseRedirect,JsonResponse
from django.shortcuts import get_object_or_404,render
from django.utils.translation import gettext as _,get_language
from django.views.decorators.http import require_GET,require_http_methods
from cars.models import Car,CarCategory
from cars.forms import CatalogFilterForm
from locations.models import City
from pages.models import Page,FAQ
from bookings.forms import BookingForm,CallbackForm,CONSENT_TEXT
from bookings.spam import allow_request
from core.models import SiteSettings,ContentBlock
from core.i18n import language_url,localized,get_translation
from core.cache import page_context
from seo.services import page_seo,schemas,catalog_languages

def faq_queryset(**filters):
    qs=FAQ.objects.filter(active=True,**filters).prefetch_related('translations')
    return qs
def blocks(kind):
    qs=ContentBlock.objects.filter(kind=kind,active=True).prefetch_related('translations')
    return list(qs)
def present(request,template,context,status=200,**schema_args):
    site=SiteSettings.get_solo();request.site_settings=site
    context['schemas']=schemas(request,context['seo'],site,breadcrumbs=context.get('breadcrumbs'),faqs=context.get('faqs'),**schema_args)
    return render(request,template,context,status=status)

def city_context(request,path):
    city=get_object_or_404(City.objects.prefetch_related('translations'),legacy_path=path,active=True)
    cars=list(Car.objects.public().with_content().filter(cities=city).order_by('-featured','sort_order','pk'))
    return {
        'seo':page_seo(request,city),'city':city,'cars':cars,'car_count':len(cars),
        'min_price':min([c.base_price for c in cars],default=None),
        'benefits':blocks('benefit'),'steps':blocks('step'),
        'faqs':list(faq_queryset(car__isnull=True,page__isnull=True).filter(Q(city=city)|Q(city__isnull=True))),
        'breadcrumbs':[] if path=='/' else [(_('Главная'),language_url('/')),(localized(city,'name'),language_url(path))]
    }

@require_GET
def home(request):
    context=page_context(request,lambda:city_context(request,'/'));context['search_form']=CatalogFilterForm()
    return present(request,'home.html',context,city=context['city'])
@require_GET
def city_page(request,slug):
    context=page_context(request,lambda:city_context(request,request.base_path));context['search_form']=CatalogFilterForm(initial={'city':context['city'].slug})
    return present(request,'city.html',context,city=context['city'])

@require_GET
def catalog(request,category_slug=None):
    form=CatalogFilterForm(request.GET or None)
    def build():
        category=get_object_or_404(CarCategory.objects.prefetch_related('translations'),slug=category_slug,active=True) if category_slug else None
        qs=Car.objects.public().with_content()
        if category:qs=qs.filter(category=category)
        if form.is_bound:
            if form.is_valid():
                data=form.cleaned_data
                for field,lookup in [('city','cities'),('brand','brand'),('category','category'),('min_price','base_price__gte'),('max_price','base_price__lte'),('transmission','transmission'),('drive','drive'),('seats','seats__gte')]:
                    if data.get(field) is not None and data.get(field)!='':qs=qs.filter(**{lookup:data[field]})
                if data.get('available'):qs=qs.filter(accepts_requests=True)
                if data.get('q'):qs=qs.filter(Q(name__icontains=data['q'])|Q(brand__name__icontains=data['q'])|Q(model_name__icontains=data['q']))
                sort={'price':('base_price','pk'),'-price':('-base_price','pk'),'new':('-created_at','pk')}.get(data.get('sort'),('-featured','sort_order','pk'))
                qs=qs.order_by(*sort)
            else:qs=qs.none()
        else:qs=qs.order_by('-featured','sort_order','pk')
        page=Paginator(qs,12).get_page(request.GET.get('page'));list(page.object_list)
        params=request.GET.copy();params.pop('page',None)
        return {'seo':page_seo(request,category,title=_('Автопарк | Legion Auto Rent'),description=_('Выберите автомобиль для аренды без водителя. Цены, фотографии и классы автомобилей в Legion Auto Rent.'),h1=_('Ваш маршрут. Ваш автомобиль.'),noindex=bool(request.GET),available_languages=catalog_languages() if not category else None),'category':category,'cars':page,'pagination_query':params.urlencode(),'breadcrumbs':[(_('Главная'),language_url('/')),(_('Автопарк'),language_url('/cars/'))]}
    context=page_context(request,build);context['filter_form']=form
    if request.headers.get('X-Legion-Partial')=='catalog':return render(request,'components/catalog_results.html',context)
    return present(request,'catalog.html',context)

@require_GET
def car_detail(request,slug):
    def build():
        car=get_object_or_404(Car.objects.public().with_content().prefetch_related('discounts','prices__translations','extra_specs__translations'),legacy_path=request.base_path)
        seo=page_seo(request,car)
        if not seo['og_image'] and car.main_image:seo['og_image']=settings.SITE_URL+car.main_image.display_url
        city=next((c for c in car.cities.all() if c.active),None)
        return {'seo':seo,'car':car,'city':city,'related_cars':list(Car.objects.public().with_content().filter(category=car.category).exclude(pk=car.pk)[:3]),'faqs':list(faq_queryset(car=car)),'conditions':blocks('condition'),'breadcrumbs':[(_('Главная'),language_url('/')),(_('Автопарк'),language_url('/cars/')),(localized(car,'name'),language_url(car.legacy_path))]}
    context=page_context(request,build);car=context['car'];city=context['city']
    context['booking_form']=BookingForm(initial={'car':car.pk,'city':city.pk if city else None,'source_token':signing.dumps(car.legacy_path,salt='booking-source')})
    context['car_whatsapp_message']=_('Здравствуйте! Интересует аренда %(car)s.')%{'car':localized(car,'name')}
    return present(request,'car_detail.html',context,car=car,city=city)

@require_GET
def static_page(request,slug):
    def build():
        page=get_object_or_404(Page.objects.prefetch_related('translations'),path=request.base_path,active=True)
        return {'seo':page_seo(request,page),'page':page,'faqs':list(faq_queryset(page=page)),'conditions':blocks('condition'),'breadcrumbs':[(_('Главная'),language_url('/')),(localized(page,'title'),language_url(page.path))]}
    return present(request,'page.html',page_context(request,build))
@require_GET
def faq_page(request):
    from seo.services import faq_languages
    return present(request,'faq_page.html',{'seo':page_seo(request,title=_('FAQ | Legion Auto Rent'),description=_('Ответы на вопросы об аренде автомобилей.'),h1=_('Вопросы об аренде'),available_languages=faq_languages()),'faqs':list(faq_queryset(car__isnull=True,page__isnull=True))})
@require_GET
def content_page(request,slug):
    if City.objects.filter(legacy_path=request.base_path,active=True).exists():return city_page(request,slug)
    return static_page(request,slug)

@require_http_methods(['GET','POST'])
def booking(request,callback=False):
    kind='callback' if callback else 'booking';initial={}
    raw=request.GET.get('car','');car=Car.objects.public().filter(pk=int(raw)).first() if raw.isdigit() else None
    city=car.cities.filter(active=True).first() if car else City.objects.filter(active=True).first()
    if car:initial['car']=car.pk
    if city:initial['city']=city.pk
    source=car.legacy_path if car else '/cars/'
    initial['source_token']=signing.dumps(source,salt='booking-source')
    form=(CallbackForm if callback else BookingForm)(request.POST or None,initial=initial);status=200
    if request.method=='POST':
        if not allow_request(request):form.is_valid();form.add_error(None,_('Слишком много попыток. Попробуйте через 15 минут.'));status=429
        elif form.is_valid():
            try:source=signing.loads(form.cleaned_data['source_token'],salt='booking-source',max_age=86400)
            except signing.BadSignature:form.add_error(None,_('Срок действия формы истёк. Обновите страницу.'));status=400
            else:
                lead=form.save(commit=False);lead.kind=kind;lead.source_page=language_url(source);lead.consent_text=str(form.fields['consent'].label)
                attribution=request.session.get('attribution',{})
                for key in ['landing_page','referrer','utm_source','utm_medium','utm_campaign','utm_content','utm_term']:setattr(lead,key,attribution.get(key,''))
                lead.save();request.session['booking_success']=secrets.token_urlsafe(20)
                return HttpResponseRedirect(language_url('/request-success/'))
        else:status=400
    return present(request,'booking.html',{'seo':page_seo(request,title=_('Заявка на аренду | Legion Auto Rent'),h1=_('Заказать звонок') if callback else _('Забронировать автомобиль'),noindex=True),'form':form,'selected_car':car,'callback':callback},status=status)
@require_GET
def success(request):
    submitted=bool(request.session.pop('booking_success',None))
    return present(request,'success.html',{'seo':page_seo(request,title=_('Заявка отправлена | Legion Auto Rent'),h1=_('Заявка отправлена'),noindex=True),'submitted':submitted})
def not_found(request,exception=None):
    return present(request,'404.html',{'seo':page_seo(request,title=_('Страница не найдена | Legion Auto Rent'),h1=_('Страница не найдена'),noindex=True)},status=404)
def server_error(request):
    # The error page works even when the DB/cache is unavailable.
    from django.http import HttpResponse
    from django.template.loader import get_template
    return HttpResponse(get_template('500.html').render({'language':getattr(request,'LANGUAGE_CODE','ru')}),status=500)
@require_GET
def health(request):
    try:
        with connection.cursor() as cursor:cursor.execute('SELECT 1')
    except Exception:return JsonResponse({'status':'unavailable'},status=503)
    return JsonResponse({'status':'ok'})
