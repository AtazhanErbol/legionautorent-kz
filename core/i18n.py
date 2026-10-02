from django.middleware.locale import LocaleMiddleware
from django.utils import translation

PREFIXES = {'ru': '', 'kk': '/kk', 'en': '/en'}

class LegionLocaleMiddleware(LocaleMiddleware):
    def process_request(self, request):
        language = 'kk' if request.path == '/kk' or request.path.startswith('/kk/') else 'en' if request.path == '/en' or request.path.startswith('/en/') else 'ru'
        translation.activate(language)
        request.LANGUAGE_CODE = language
        request.base_path = request.path[len(PREFIXES[language]):] or '/'
    def process_response(self, request, response):
        response.setdefault('Content-Language', request.LANGUAGE_CODE)
        return response

def language_url(path, language=None):
    return PREFIXES[language or translation.get_language() or 'ru'] + path

def get_translation(obj, language=None):
    language = language or translation.get_language() or 'ru'
    if language == 'ru' or not obj or not obj.pk: return None
    return next((t for t in obj.translations.all() if t.language == language and t.published), None)

FIELD_MAP = {'seo_title': 'title', 'seo_description': 'description', 'seo_h1': 'h1', 'body': 'content', 'text': 'content', 'answer': 'content', 'question': 'title','alt':'name','value':'content','label':'title'}
def localized(obj, field, language=None):
    t = get_translation(obj, language)
    if t:
        key = 'content' if field == 'description' and obj._meta.model_name in ('car', 'carcategory') else FIELD_MAP.get(field, field)
        if field == 'title' and obj._meta.model_name == 'page': return t.name or t.h1
        if field == 'og_title': return t.og_title or t.title
        if field == 'og_description': return t.og_description or t.description
        value = getattr(t, key, '')
        if value: return value
    return getattr(obj, field, '')
