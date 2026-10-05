from django import forms
from .models import SiteSettings


LABELS = {
    'name': 'Название', 'title': 'Заголовок', 'slug': 'Код в адресе (slug)',
    'legacy_path': 'Адрес страницы', 'legacy_id': 'ID исходного сайта', 'path': 'Адрес страницы',
    'brand': 'Марка', 'model_name': 'Модель', 'category': 'Класс', 'cities': 'Города',
    'active': 'Опубликовано', 'featured': 'Выделить в каталоге', 'sort_order': 'Порядок',
    'year': 'Год выпуска', 'engine': 'Двигатель', 'transmission': 'Коробка передач',
    'drive': 'Привод', 'fuel': 'Топливо', 'seats': 'Места', 'doors': 'Двери', 'color': 'Цвет',
    'features': 'Оснащение', 'description': 'Описание', 'deposit': 'Депозит, ₸',
    'mileage_limit': 'Пробег в сутки, км', 'min_days': 'От дней', 'max_days': 'До дней',
    'daily_price': 'В сутки, ₸', 'percent': 'Скидка, %', 'label': 'Название тарифа',
    'car': 'Автомобиль', 'city': 'Город', 'page': 'Страница', 'value': 'Значение',
    'original': 'Фотография', 'alt': 'Описание фото (alt)', 'caption': 'Подпись',
    'is_main': 'Главное фото', 'legacy_url': 'Исходный адрес изображения',
    'question': 'Вопрос', 'answer': 'Ответ', 'kind': 'Тип', 'text': 'Текст',
    'phone': 'Телефон', 'whatsapp': 'Номер WhatsApp', 'email': 'Электронная почта',
    'address': 'Адрес', 'hours': 'Часы работы', 'logo': 'Логотип', 'favicon': 'Иконка сайта',
    'hero_image': 'Загрузить первый кадр', 'hero_car': 'Автомобиль для резервного режима',
    'hero_text': 'Описание первого экрана', 'map_url': 'Ссылка на встроенную карту Яндекса',
    'footer_text': 'Подпись в подвале', 'whatsapp_message': 'Сообщение в WhatsApp',
    'default_seo_title': 'Запасной Title', 'default_seo_description': 'Запасной Description',
    'robots_text': 'Инструкции robots.txt', 'gtm_id': 'Контейнер Google Tag Manager',
    'ga4_id': 'GA4 — справочный ID', 'metrika_id': 'Метрика — справочный ID',
    'google_verification': 'Подтверждение Google', 'yandex_verification': 'Подтверждение Яндекса',
    'notifications_enabled': 'Уведомления о заявках', 'show_partner_section': 'Показывать блок партнёров',
    'partner_title': 'Заголовок', 'partner_description': 'Описание', 'partner_phone': 'Телефон партнёров',
    'partner_whatsapp': 'WhatsApp партнёров', 'partner_whatsapp_message': 'Сообщение для партнёров',
    'intro': 'Вступление', 'show_in_footer': 'Ссылка в подвале', 'legal_approved': 'Текст утверждён владельцем',
    'canonical_url': 'Канонический адрес', 'robots': 'Индексация', 'og_title': 'Заголовок при отправке ссылки',
    'og_description': 'Описание при отправке ссылки', 'og_image': 'Адрес картинки для соцсетей',
    'legacy_meta': 'Сохранённые метаданные', 'latitude': 'Широта', 'longitude': 'Долгота',
    'status': 'Статус', 'comment': 'Комментарий клиента', 'start_date': 'Начало аренды', 'end_date': 'Конец аренды',
    'created_at': 'Создано', 'updated_at': 'Обновлено', 'consent': 'Согласие клиента', 'consent_text': 'Текст согласия',
    'source_page': 'Страница заявки', 'landing_page': 'Страница входа', 'referrer': 'Источник перехода',
    'old_path': 'Старый адрес', 'new_path': 'Конечный адрес', 'status_code': 'Код ответа',
}


class FriendlyFieldsMixin:
    """Presentation labels only; imports and the schema remain compatible."""
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name in LABELS:
            kwargs.setdefault('label', LABELS[db_field.name])
        field = super().formfield_for_dbfield(db_field, request, **kwargs)
        if field and isinstance(field.widget, forms.Textarea):
            field.widget.attrs.update(rows=4)
            if db_field.name in ('body', 'content', 'description'):
                field.widget.attrs['data-rich-editor'] = 'true'
        return field


class SiteSettingsForm(forms.ModelForm):
    class Meta:
        model = SiteSettings
        fields = '__all__'

    def clean(self):
        data = super().clean()
        if data.get('hero_video_file') and 'hero_video_file' in self.changed_data and not data.get('hero_video_fps'):
            self.add_error('hero_video_fps', 'Укажите частоту кадров загружаемого ролика.')
        return data
