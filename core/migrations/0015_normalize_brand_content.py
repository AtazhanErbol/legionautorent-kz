"""Owner requested one brand spelling on 2026-10-05. Historical leads stay intact."""
import re
from django.db import migrations, models

PATTERN = re.compile(r'(?<![\w/@.\-])(?:legion(?:[ \t]*auto(?:[ \t]*rent)?)?|легион(?:[ \t]*авто(?:[ \t]*рент)?)?|легионе|легионда)(?![\w@\-]|\.[a-z])', re.IGNORECASE)
MODELS = [('core','SiteSettings'), ('core','ContentBlock'), ('core','InterfaceText'), ('core','MenuLink'), ('pages','Page'), ('pages','FAQ'), ('cars','Car'), ('cars','CarCategory'), ('cars','CarImage'), ('locations','City'), ('seo','Translation')]
FIELDS = {'name','title','description','seo_title','seo_description','seo_h1','og_title','og_description','body','intro','text','question','answer','alt','caption','content','h1','hero_title','hero_text','hero_price_caption','hero_steps_caption','partner_title','partner_description','partner_whatsapp_message','whatsapp_message','footer_text','default_seo_title','default_seo_description','source','ru','kk','en','label','label_kk','label_en'}


def forwards(apps, schema_editor):
    alias=schema_editor.connection.alias
    for app, name in MODELS:
        model=apps.get_model(app,name)
        fields=[f.name for f in model._meta.fields if f.name in FIELDS and isinstance(f,(models.CharField,models.TextField)) and not isinstance(f,models.URLField)]
        for obj in model.objects.using(alias).all().iterator():
            changes={}
            for field in fields:
                before=getattr(obj,field)
                if not isinstance(before,str):continue
                after=PATTERN.sub('legionautorent',before)
                if after!=before:changes[field]=after
            if changes:model.objects.using(alias).filter(pk=obj.pk).update(**changes)


class Migration(migrations.Migration):
    dependencies=[('core','0014_unified_brand_defaults'),('cars','0006_alter_carbrand_options_alter_cardiscount_options_and_more'),('locations','0005_alter_city_active_alter_city_address_and_more'),('pages','0003_alter_page_options_alter_faq_active_alter_faq_answer_and_more'),('seo','0005_alter_redirect_options_alter_redirect_active_and_more')]
    operations=[migrations.RunPython(forwards,migrations.RunPython.noop)]
