from django import forms
from django.utils.translation import gettext_lazy as _
from .models import CarBrand, CarCategory
from locations.models import City
from core.forms import LocalizedModelChoiceField

class CatalogFilterForm(forms.Form):
    city = LocalizedModelChoiceField(City.objects.filter(active=True).prefetch_related('translations'), required=False, label=_('Город'), to_field_name='slug', empty_label=_('Все города'))
    brand = forms.ModelChoiceField(CarBrand.objects.all(), required=False, label=_('Марка'), to_field_name='slug', empty_label=_('Все марки'))
    category = LocalizedModelChoiceField(CarCategory.objects.filter(active=True).prefetch_related('translations'), required=False, label=_('Класс'), to_field_name='slug', empty_label=_('Все классы'))
    min_price = forms.IntegerField(min_value=0, required=False, label=_('Цена от'))
    max_price = forms.IntegerField(min_value=0, required=False, label=_('Цена до'))
    transmission = forms.ChoiceField(choices=[('', _('Любая коробка')), ('automatic', _('Автомат')), ('manual', _('Механика'))], required=False, label=_('Коробка'))
    drive = forms.ChoiceField(choices=[('', _('Любой привод')), ('front', _('Передний')), ('rear', _('Задний')), ('all', _('Полный'))], required=False, label=_('Привод'))
    seats = forms.IntegerField(min_value=1, max_value=20, required=False, label=_('Мест от'))
    available = forms.BooleanField(required=False, label=_('Принимают заявки'))
    q = forms.CharField(max_length=100, required=False, label=_('Поиск'), widget=forms.TextInput(attrs={'placeholder': _('Марка или модель')}))
    sort = forms.ChoiceField(required=False, label=_('Сортировка'), choices=[('', _('Популярные')), ('price', _('Сначала дешевле')), ('-price', _('Сначала дороже')), ('new', _('Новые в каталоге'))])
    start_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}), label=_('Дата получения'))
    end_date = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}), label=_('Дата возврата'))
    def clean(self):
        data = super().clean()
        if data.get('min_price') and data.get('max_price') and data['min_price'] > data['max_price']:
            raise forms.ValidationError(_('Минимальная цена не может быть выше максимальной.'))
        if data.get('start_date') and data.get('end_date') and data['end_date'] <= data['start_date']:
            raise forms.ValidationError(_('Возврат должен быть позже получения.'))
        return data
