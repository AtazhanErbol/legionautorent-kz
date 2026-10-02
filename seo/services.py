from django.conf import settings
from django.utils import translation
from core.i18n import localized,get_translation,language_url

LANGUAGES=('ru','kk','en')
def faq_languages():
    from pages.models import FAQ
    faqs=list(FAQ.objects.filter(active=True,car__isnull=True,page__isnull=True).prefetch_related('translations'))
    return ['ru']+[lang for lang in ('kk','en') if faqs and all(get_translation(f,lang) for f in faqs)]

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
            'og_url':legacy.get('og:url',canonical),'og_type':legacy.get('og:type','website'),'og_site_name':legacy.get('og:site_name','Legion Auto Rent'),'og_video':legacy.get('og:video','')}

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
