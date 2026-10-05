from django.db import migrations


def seed(apps, schema_editor):
    model = apps.get_model('core', 'InterfaceText')
    for source, kk, en in [
        ('Разработано в', 'Әзірлеген', 'Developed by'),
        ('Открыть фото', 'Фотосуретті ашу', 'Open photo'),
        ('Закрыть фото', 'Фотосуретті жабу', 'Close photo'),
    ]:
        model.objects.get_or_create(source=source, defaults={'section': 'Интерфейс', 'kk': kk, 'en': en})


class Migration(migrations.Migration):
    dependencies = [('core', '0011_form_interface_copy')]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
