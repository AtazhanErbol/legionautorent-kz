"""Editable UI copy, with the existing gettext catalogue as a fallback."""
from django.utils.translation import get_language, gettext
from .models import InterfaceText


def interface_copy(request):
    if not hasattr(request, '_interface_copy'):
        request._interface_copy = {row.source: row for row in InterfaceText.objects.all()}
    return request._interface_copy


def text_for(request, source):
    row = interface_copy(request).get(source)
    value = getattr(row, get_language() or 'ru', '') if row else ''
    return value or gettext(source)


def edit_form_copy(request, form):
    from django.utils.translation import override
    from django.forms import ChoiceField, ModelChoiceField
    if getattr(form, '_cms_labels_applied', False):
        return
    for name, field in form.fields.items():
        if name in ('website', 'source_token'):
            continue
        with override('ru'):
            source = str(field.label or '')
        field.label = text_for(request, source)
        if isinstance(field, ModelChoiceField) and field.empty_label:
            with override('ru'): source = str(field.empty_label)
            field.empty_label = text_for(request, source)
        elif isinstance(field, ChoiceField):
            choices = []
            for key, label in field.choices:
                with override('ru'): source = str(label)
                choices.append((key, text_for(request, source)))
            field.choices = choices
    form._cms_labels_applied = True
