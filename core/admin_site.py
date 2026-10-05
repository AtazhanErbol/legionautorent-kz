"""LEGIONAUTORENT's staff workspace. Django permissions remain the source of access."""
from django.contrib.admin import AdminSite
from django.contrib.admin.apps import AdminConfig
from django.urls import reverse


class LegionAdminConfig(AdminConfig):
    default_site = 'core.admin_site.LegionAdminSite'


class LegionAdminSite(AdminSite):
    def each_context(self, request):
        from core.models import SiteSettings
        from django.templatetags.static import static
        site=SiteSettings.get_solo()
        return {**super().each_context(request), 'brand_favicon': site.favicon.url if site.favicon else static('img/favicon-original.jpg')}

    site_header = 'LEGIONAUTORENT'
    site_title = 'LEGIONAUTORENT — управление'
    index_title = 'Обзор'

    def get_app_list(self, request, app_label=None):
        apps = super().get_app_list(request, app_label)
        if app_label:
            return apps
        models = {(app['app_label'], model['object_name'].lower()): model for app in apps for model in app['models']}
        groups = [
            ('Заявки', [('bookings', 'bookingrequest', 'Заявки и звонки')]),
            ('Автопарк', [('cars', 'car', 'Автомобили'), ('cars', 'carcategory', 'Классы'), ('cars', 'carbrand', 'Марки'), ('cars', 'carfeature', 'Оснащение'), ('cars', 'carspecification', 'Характеристики'), ('cars', 'carimage', 'Фотографии'), ('cars', 'carprice', 'Тарифы')]),
            ('Сайт и контент', [('core', 'sitesettings', 'Бренд, контакты и видео'), ('core', 'interfacetext', 'Тексты и кнопки'), ('core', 'sitesection', 'Порядок разделов'), ('core', 'menulink', 'Навигация'), ('core', 'contentblock', 'Преимущества, шаги, условия'), ('locations', 'city', 'Города'), ('pages', 'page', 'Страницы'), ('pages', 'faq', 'Вопросы и ответы')]),
            ('Служебное', [('seo', 'redirect', 'Перенаправления'), ('auth', 'user', 'Пользователи'), ('auth', 'group', 'Роли и права'), ('axes', 'accessattempt', 'Попытки входа'), ('axes', 'accesslog', 'Журнал входов'), ('axes', 'accessfailurelog', 'Ошибки входа')]),
        ]
        result = []
        for title, entries in groups:
            items = []
            for app, model, label in entries:
                item = models.pop((app, model), None)
                if item:
                    item['name'] = label
                    items.append(item)
            if items:
                result.append({'name': title, 'app_label': title, 'app_url': items[0].get('admin_url', ''), 'has_module_perms': True, 'models': items})
        for app in apps:
            remainder = [m for m in app['models'] if (app['app_label'], m['object_name'].lower()) in models]
            if remainder:
                result.append({**app, 'models': remainder})
        return result

    def index(self, request, extra_context=None):
        from cars.models import Car
        from bookings.models import BookingRequest
        from locations.models import City
        from pages.models import Page
        stats = []
        for model, title, filter_values in [(BookingRequest, 'Новые заявки', {'status': 'NEW'}), (Car, 'Автомобили', {}), (City, 'Города', {'active': True}), (Page, 'Страницы', {'active': True})]:
            opts = model._meta
            if request.user.has_perm(f'{opts.app_label}.view_{opts.model_name}') or request.user.has_perm(f'{opts.app_label}.change_{opts.model_name}'):
                url = reverse(f'admin:{opts.app_label}_{opts.model_name}_changelist')
                if model == BookingRequest: url += '?status__exact=NEW'
                stats.append({'title': title, 'value': model.objects.filter(**filter_values).count(), 'url': url})
        context = {'workspace_stats': stats}
        if request.user.has_perm('pages.view_page') or request.user.has_perm('pages.change_page'):
            privacy = Page.objects.filter(path='/privacy/').first()
            if privacy:
                context['privacy_admin_url'] = reverse('admin:pages_page_change', args=[privacy.pk])
        if request.user.has_perm('bookings.view_bookingrequest') or request.user.has_perm('bookings.change_bookingrequest'):
            context['workspace_leads'] = BookingRequest.objects.select_related('car', 'city').order_by('-created_at')[:5]
        return super().index(request, {**context, **(extra_context or {})})
