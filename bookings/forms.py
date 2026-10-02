import re
from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from cars.models import Car
from locations.models import City
from .models import BookingRequest
from core.forms import LocalizedModelChoiceField

CONSENT_TEXT = 'Я согласен на обработку имени, телефона, дат аренды и комментария компанией Legion Auto Rent для ответа на мою заявку.'

class BookingForm(forms.ModelForm):
    website = forms.CharField(required=False, label='Website', widget=forms.TextInput(attrs={'tabindex': '-1', 'autocomplete': 'off'}))
    source_token = forms.CharField(widget=forms.HiddenInput)
    consent = forms.BooleanField(label=_(CONSENT_TEXT), required=True)
    class Meta:
        model = BookingRequest
        fields = ['car', 'city', 'name', 'phone', 'start_date', 'end_date', 'comment', 'consent']
        field_classes={'car':LocalizedModelChoiceField,'city':LocalizedModelChoiceField}
        labels = {'car': _('Автомобиль'), 'city': _('Город'), 'name': _('Ваше имя'), 'phone': _('Телефон'), 'start_date': _('Дата получения'), 'end_date': _('Дата возврата'), 'comment': _('Комментарий')}
        widgets = {'name': forms.TextInput(attrs={'autocomplete': 'name'}), 'phone': forms.TextInput(attrs={'type': 'tel', 'autocomplete': 'tel', 'placeholder': '+7 700 000 00 00'}), 'start_date': forms.DateInput(attrs={'type': 'date'}), 'end_date': forms.DateInput(attrs={'type': 'date'}), 'comment': forms.Textarea(attrs={'rows': 3, 'maxlength': 2000})}
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['car'].queryset = Car.objects.public().filter(accepts_requests=True).prefetch_related('translations')
        self.fields['car'].empty_label = _('Помогите выбрать автомобиль')
        self.fields['city'].queryset = City.objects.filter(active=True).prefetch_related('translations')
        self.fields['comment'].max_length = 2000
        self.fields['start_date'].widget.attrs['min'] = timezone.localdate().isoformat()
        self.fields['end_date'].widget.attrs['min'] = timezone.localdate().isoformat()
    def clean_phone(self):
        value = self.cleaned_data['phone'].strip()
        if not re.fullmatch(r'[+()\d\s-]+', value): raise forms.ValidationError(_('Укажите корректный номер телефона.'))
        digits = re.sub(r'\D', '', value)
        if not 10 <= len(digits) <= 15: raise forms.ValidationError(_('Укажите номер телефона: от 10 до 15 цифр.'))
        return '+' + digits
    def clean(self):
        data = super().clean()
        if data.get('website'): raise forms.ValidationError(_('Не удалось отправить заявку. Попробуйте ещё раз.'))
        start, end = data.get('start_date'), data.get('end_date')
        if bool(start) != bool(end): raise forms.ValidationError(_('Укажите обе даты или оставьте их пустыми.'))
        if start and start < timezone.localdate(): self.add_error('start_date', _('Дата получения не может быть в прошлом.'))
        if start and end and end <= start: self.add_error('end_date', _('Возврат должен быть позже получения.'))
        car, city = data.get('car'), data.get('city')
        if car and city and not car.cities.filter(pk=city.pk).exists(): self.add_error('car', _('Этот автомобиль не представлен в выбранном городе.'))
        return data
