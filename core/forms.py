from django.forms import ModelChoiceField
from .i18n import localized
class LocalizedModelChoiceField(ModelChoiceField):
    def label_from_instance(self,obj):
        return localized(obj,'name') if hasattr(obj,'translations') else str(obj)
