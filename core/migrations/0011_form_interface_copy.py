from django.db import migrations

SOURCES = ['Автомат', 'Автомобиль', 'Ваше имя', 'Все города', 'Все классы', 'Все марки', 'Город', 'Дата возврата', 'Дата получения', 'Задний', 'Класс', 'Комментарий', 'Коробка', 'Любая коробка', 'Любой привод', 'Марка', 'Марка или модель', 'Мест от', 'Механика', 'Новые в каталоге', 'Передний', 'Поиск', 'Полный', 'Помогите выбрать автомобиль', 'Популярные', 'Привод', 'Принимают заявки', 'Сначала дешевле', 'Сначала дороже', 'Сортировка', 'Телефон', 'Цена до', 'Цена от', 'Я согласен на обработку имени, телефона, дат аренды и комментария компанией Legion Auto Rent для ответа на мою заявку.']

def seed(apps, schema_editor):
    Text=apps.get_model('core','InterfaceText')
    for source in SOURCES:
        Text.objects.get_or_create(source=source,defaults={'section':'Формы и фильтры'})

class Migration(migrations.Migration):
    dependencies=[('core','0010_alter_contentblock_active_alter_contentblock_kind_and_more')]
    operations=[migrations.RunPython(seed,migrations.RunPython.noop)]
