from django.conf import settings
from django.utils import translation
from core.i18n import localized, get_translation, language_url

def languages_for(obj):
    if not obj or not obj.pk: return ['ru', 'kk', 'en']
    langs = ['ru']
    for lang in ['kk', 'en']:
        t = get_translation(obj, lang)
        if t and all([t.title, t.description, t.h1, t.content]): langs.append(lang)
    return langs

def catalog_languages():
    from cars.models import Car, CarCategory
    from locations.models import City
    from django.core.cache import cache
    cached=cache.get('catalog_languages')
    if cached is not None:return cached
    objects = [*Car.objects.public().prefetch_related('translations'), *CarCategory.objects.filter(active=True).prefetch_related('translations'), *City.objects.filter(active=True).prefetch_related('translations')]
    result=['ru'] + [language for language in ['kk', 'en'] if objects and all(language in languages_for(obj) for obj in objects)]
    cache.set('catalog_languages',result,60)
    return result

def page_seo(request, obj=None, title='', description='', h1='', noindex=False, path=None, available_languages=None):
    language = request.LANGUAGE_CODE
    base_path = path or request.base_path
    available = available_languages if available_languages is not None else languages_for(obj)
    fallback = language not in available
    canonical = settings.SITE_URL + language_url(base_path, 'ru' if fallback else language)
    robots = 'noindex,follow' if noindex or fallback or (obj and 'noindex' in obj.robots) else 'index,follow'
    if settings.IS_STAGING: robots = 'noindex,nofollow'
    title = localized(obj, 'seo_title') if obj else title
    description = localized(obj, 'seo_description') if obj else description
    h1 = localized(obj, 'seo_h1') if obj else h1
    return {'title': title, 'description': description, 'h1': h1, 'canonical': canonical, 'robots': robots, 'fallback': fallback, 'alternates': [{'language': l, 'url': settings.SITE_URL + language_url(base_path, l)} for l in available] if not noindex else [], 'default_url': settings.SITE_URL + base_path, 'og_title': (localized(obj, 'og_title') if obj else '') or title, 'og_description': (localized(obj, 'og_description') if obj else '') or description, 'og_image': getattr(obj, 'og_image', '')}

def schemas(request, seo, site, breadcrumbs=None, car=None, city=None):
    root = settings.SITE_URL
    result = [{'@context': 'https://schema.org', '@type': 'WebSite', '@id': root + '/#website', 'name': site.name, 'url': root + '/', 'inLanguage': request.LANGUAGE_CODE}, {'@context': 'https://schema.org', '@type': 'WebPage', 'name': seo['title'], 'url': seo['canonical'], 'inLanguage': 'ru' if seo['fallback'] else request.LANGUAGE_CODE, 'isPartOf': {'@id': root + '/#website'}}]
    business = {'@context': 'https://schema.org', '@type': 'AutoRental', 'name': site.name, 'url': root + '/', 'telephone': city.phone if city and city.phone else site.phone}
    address = city.address if city else site.address
    if address: business['address'] = {'@type': 'PostalAddress', 'streetAddress': address, 'addressCountry': 'KZ', **({'addressLocality': city.name} if city else {})}
    result.append(business)
    if breadcrumbs:
        result.append({'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [{'@type': 'ListItem', 'position': i + 1, 'name': name, 'item': root + link} for i, (name, link) in enumerate(breadcrumbs)]})
    if car:
        vehicle = {'@context': 'https://schema.org', '@type': 'Vehicle', 'name': localized(car, 'name'), 'brand': {'@type': 'Brand', 'name': car.brand.name}, 'url': seo['canonical']}
        if car.main_image: vehicle['image'] = root + car.main_image.display_url
        if car.year: vehicle['vehicleModelDate'] = str(car.year)
        if car.seats: vehicle['vehicleSeatingCapacity'] = car.seats
        result.append(vehicle)
    return result
