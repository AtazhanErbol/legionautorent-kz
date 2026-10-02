"""Apply the new service/view layer after the preserved-data Git/backup checkpoint."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FILES={
'seo/services.py':r'''from django.conf import settings
from django.utils import translation
from core.i18n import localized,get_translation,language_url

LANGUAGES=('ru','kk','en')
def languages_for(obj):
    if not obj or not obj.pk:return list(LANGUAGES)
    return ['ru']+[lang for lang in ('kk','en') if (t:=get_translation(obj,lang)) and all([t.title,t.description,t.h1,t.content])]

def catalog_languages():
    from django.core.cache import cache
    from cars.models import Car,CarCategory
    from locations.models import City
    result=cache.get('catalog_languages')
    if result is None:
        objects=[*Car.objects.public().prefetch_related('translations'),*CarCategory.objects.filter(active=True).prefetch_related('translations'),*City.objects.filter(active=True).prefetch_related('translations')]
        result=['ru']+[lang for lang in ('kk','en') if objects and all(lang in languages_for(obj) for obj in objects)]
        cache.set('catalog_languages',result,60)
    return result

def page_seo(request,obj=None,title='',description='',h1='',noindex=False,path=None,available_languages=None):
    lang=request.LANGUAGE_CODE;path=path or request.base_path
    available=available_languages if available_languages is not None else languages_for(obj)
    fallback=lang not in available
    title=localized(obj,'seo_title') if obj else title
    description=localized(obj,'seo_description') if obj else description
    h1=localized(obj,'seo_h1') if obj else h1
    canonical=settings.SITE_URL+language_url(path,lang)
    if lang=='ru' and obj and obj.canonical_url:canonical=obj.canonical_url
    robots='noindex,follow' if noindex or fallback or (obj and 'noindex' in obj.robots) else 'index,follow'
    if settings.IS_STAGING:robots='noindex,nofollow'
    legacy=getattr(obj,'legacy_meta',{}).get('open_graph',{}) if obj and lang=='ru' else {}
    return {'title':title,'description':description,'h1':h1,'canonical':canonical,'robots':robots,'fallback':fallback,
            'alternates':[{'language':l,'url':settings.SITE_URL+language_url(path,l)} for l in LANGUAGES],
            'default_url':settings.SITE_URL+path,'og_title':(localized(obj,'og_title') if obj else '') or title,
            'og_description':(localized(obj,'og_description') if obj else '') or description,'og_image':getattr(obj,'og_image',''),
            'og_type':legacy.get('og:type','website'),'og_site_name':legacy.get('og:site_name','Legion Auto Rent'),'og_video':legacy.get('og:video','')}

def schemas(request,seo,site,breadcrumbs=None,car=None,city=None,faqs=None):
    root=settings.SITE_URL;lang=request.LANGUAGE_CODE
    result=[{'@context':'https://schema.org','@type':'WebSite','@id':root+'/#website','name':site.name,'url':root+'/', 'inLanguage':lang},
            {'@context':'https://schema.org','@type':'WebPage','name':seo['title'],'url':seo['canonical'],'inLanguage':lang,'isPartOf':{'@id':root+'/#website'}}]
    business={'@context':'https://schema.org','@type':['AutoRental','LocalBusiness'],'@id':root+(city.legacy_path if city else '/')+'#business','name':site.name,'url':root+(city.legacy_path if city else '/'),'telephone':city.phone if city and city.phone else site.phone}
    address=city.address if city else site.address
    if address:business['address']={'@type':'PostalAddress','streetAddress':address,'addressCountry':'KZ',**({'addressLocality':localized(city,'name')} if city else {})}
    hours=city.hours if city and city.hours else site.hours
    if hours:business['openingHours']=hours
    if city and city.latitude is not None and city.longitude is not None:business['geo']={'@type':'GeoCoordinates','latitude':str(city.latitude),'longitude':str(city.longitude)}
    if site.instagram:business['sameAs']=[site.instagram]
    result.append(business)
    if breadcrumbs:result.append({'@context':'https://schema.org','@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':i+1,'name':name,'item':root+link} for i,(name,link) in enumerate(breadcrumbs)]})
    if car:
        offer={'@type':'Offer','url':seo['canonical'],'price':str(car.base_price),'priceCurrency':'KZT','priceSpecification':{'@type':'UnitPriceSpecification','price':str(car.base_price),'priceCurrency':'KZT','referenceQuantity':{'@type':'QuantitativeValue','value':1,'unitCode':'DAY'}}}
        vehicle={'@context':'https://schema.org','@type':['Vehicle','Product'],'name':localized(car,'name'),'brand':{'@type':'Brand','name':car.brand.name},'url':seo['canonical'],'offers':offer}
        if car.main_image:vehicle['image']=root+car.main_image.display_url
        if car.year:vehicle['vehicleModelDate']=str(car.year)
        if car.seats:vehicle['vehicleSeatingCapacity']=car.seats
        result.append(vehicle)
    if faqs:
        from nh3 import clean
        result.append({'@context':'https://schema.org','@type':'FAQPage','mainEntity':[{'@type':'Question','name':localized(f,'question'),'acceptedAnswer':{'@type':'Answer','text':clean(localized(f,'answer'),tags=set())}} for f in faqs]})
    return result
''',
'seo/views.py':r'''from xml.etree.ElementTree import Element,SubElement,tostring,register_namespace
from django.conf import settings
from django.http import HttpResponse,Http404
from django.views.decorators.http import require_GET
from locations.models import City
from cars.models import Car,CarCategory
from pages.models import Page
from core.models import SiteSettings
from core.i18n import language_url
from .services import languages_for,catalog_languages

NS='http://www.sitemaps.org/schemas/sitemap/0.9';XHTML='http://www.w3.org/1999/xhtml'
register_namespace('',NS);register_namespace('xhtml',XHTML)
SECTIONS=('cities','cars','categories','pages')

@require_GET
def robots(request):
    if settings.IS_STAGING:text='User-agent: *\nDisallow: /\n'
    else:
        site=SiteSettings.get_solo();url=settings.SITE_URL+'/sitemap.xml'
        text=site.robots_text.replace('{sitemap_url}',url) if site.robots_text else f'User-agent: *\nDisallow: /{settings.ADMIN_PATH}\nDisallow: /booking/\nDisallow: /callback/\nDisallow: /request-success/\nDisallow: /kk/booking/\nDisallow: /en/booking/\n'
        if 'Sitemap:' not in text:text+='\nSitemap: '+url+'\n'
    return HttpResponse(text,content_type='text/plain; charset=utf-8')

@require_GET
def sitemap(request,section=None):
    if section is None:
        root=Element(f'{{{NS}}}sitemapindex')
        latest=max([d for d in [Car.objects.order_by('-updated_at').values_list('updated_at',flat=True).first(),City.objects.order_by('-updated_at').values_list('updated_at',flat=True).first()] if d],default=None)
        for name in SECTIONS:
            item=SubElement(root,f'{{{NS}}}sitemap');SubElement(item,f'{{{NS}}}loc').text=f'{settings.SITE_URL}/sitemap-{name}.xml'
            if latest:SubElement(item,f'{{{NS}}}lastmod').text=latest.isoformat()
    else:
        if section not in SECTIONS:raise Http404()
        groups={'cities':City.objects.filter(active=True,robots='index,follow'), 'cars':Car.objects.public().filter(robots='index,follow'), 'categories':CarCategory.objects.filter(active=True,robots='index,follow'), 'pages':Page.objects.filter(active=True,robots='index,follow')}
        entries=[(obj.get_absolute_url(),languages_for(obj),obj.updated_at) for obj in groups[section].prefetch_related('translations')]
        if section=='pages':entries.append(('/cars/',catalog_languages(),None))
        root=Element(f'{{{NS}}}urlset')
        for path,languages,modified in entries:
            for lang in languages:
                item=SubElement(root,f'{{{NS}}}url');SubElement(item,f'{{{NS}}}loc').text=settings.SITE_URL+language_url(path,lang)
                if modified:SubElement(item,f'{{{NS}}}lastmod').text=modified.isoformat()
                for alternate in languages:SubElement(item,f'{{{XHTML}}}link',{'rel':'alternate','hreflang':alternate,'href':settings.SITE_URL+language_url(path,alternate)})
                SubElement(item,f'{{{XHTML}}}link',{'rel':'alternate','hreflang':'x-default','href':settings.SITE_URL+path})
    return HttpResponse(tostring(root,encoding='utf8',xml_declaration=True),content_type='application/xml')
''',
'core/views.py':r'''import secrets
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
    if get_language()!='ru':qs=qs.filter(translations__language=get_language(),translations__published=True)
    return qs
def blocks(kind):
    qs=ContentBlock.objects.filter(kind=kind,active=True).prefetch_related('translations')
    if get_language()!='ru':qs=qs.filter(translations__language=get_language(),translations__published=True)
    return list(qs)
def present(request,template,context,status=200,**schema_args):
    site=SiteSettings.get_solo();request.site_settings=site
    context['schemas']=schemas(request,context['seo'],site,breadcrumbs=context.get('breadcrumbs'),faqs=context.get('faqs'),**schema_args)
    return render(request,template,context,status=status)

def city_context(request,path):
    city=get_object_or_404(City.objects.prefetch_related('translations'),legacy_path=path,active=True)
    cars=list(Car.objects.public().with_content().filter(cities=city).order_by('-featured','sort_order','pk'))
    return {'seo':page_seo(request,city),'city':city,'cars':cars,'car_count':len(cars),'min_price':min([c.base_price for c in cars],default=None),'benefits':blocks('benefit'),'steps':blocks('step'),'faqs':list(faq_queryset(car__isnull=True,page__isnull=True).filter(Q(city=city)|Q(city__isnull=True))),'breadcrumbs':[] if path=='/' else [(_('Главная'),language_url('/')),(localized(city,'name'),language_url(path))]}

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
        car=get_object_or_404(Car.objects.public().with_content().prefetch_related('discounts','prices','extra_specs__translations'),legacy_path=request.base_path)
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
    return present(request,'faq_page.html',{'seo':page_seo(request,title=_('FAQ | Legion Auto Rent'),description=_('Ответы на вопросы об аренде автомобилей.'),h1=_('Вопросы об аренде')),'faqs':list(faq_queryset(car__isnull=True,page__isnull=True))})
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
    return render(request,'500.html',{'language':getattr(request,'LANGUAGE_CODE','ru')},status=500)
@require_GET
def health(request):
    try:
        with connection.cursor() as cursor:cursor.execute('SELECT 1')
    except Exception:return JsonResponse({'status':'unavailable'},status=503)
    return JsonResponse({'status':'ok'})
''',
'legion/urls.py':r'''from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path,include
from django.http import HttpResponsePermanentRedirect,Http404
from core import views
from seo.views import robots,sitemap

public=[path('',views.home,name='home'),path('cars/',views.catalog,name='catalog'),path('category/<slug:category_slug>/',views.catalog,name='category'),path('car/<slug:slug>',views.car_detail,name='car'),path('booking/',views.booking,name='booking'),path('callback/',views.booking,{'callback':True},name='callback'),path('request-success/',views.success,name='success'),path('faq/',views.faq_page,name='faq'),path('<slug:slug>/',views.content_page,name='page')]
def old_kazakh(request,path=''):
    # Live audit proved these were 404, not Kazakh SEO pages. Previous local links get one hop.
    from django.urls import resolve,Resolver404
    target='/kk/'+path
    try:resolve(target)
    except Resolver404:raise Http404()
    query=request.META.get('QUERY_STRING','')
    return HttpResponsePermanentRedirect(target+('?' + query if query else ''))
urlpatterns=[path(settings.ADMIN_PATH,admin.site.urls),path('healthz/',views.health),path('robots.txt',robots),path('sitemap.xml',sitemap),path('sitemap-<str:section>.xml',sitemap),path('kk/',include((public,'kk'))),path('en/',include((public,'en'))),path('kz/',old_kazakh),path('kz/<path:path>',old_kazakh),*public]
if settings.DEBUG:urlpatterns+=static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)
handler404='core.views.not_found'
handler500='core.views.server_error'
''',
}
for name,text in FILES.items():(ROOT/name).write_text(text,encoding='utf8')
print('Rebuilt views, SEO services and URL routing; raw sources/media untouched.')
