from django.contrib.auth.models import Group,Permission
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help='Create least-privilege CMS groups without replacing existing users or permissions.'
    def handle(self,*args,**kwargs):
        editor,_=Group.objects.get_or_create(name='Редактор контента')
        editor.permissions.add(*Permission.objects.filter(content_type__app_label__in=['cars','locations','pages','core','seo']).exclude(content_type__model='redirect'))
        manager,_=Group.objects.get_or_create(name='Менеджер заявок')
        manager.permissions.add(*Permission.objects.filter(content_type__app_label='bookings',content_type__model='bookingrequest',codename__in=['view_bookingrequest','change_bookingrequest']))
        manager.permissions.add(*Permission.objects.filter(content_type__app_label='cars',codename='view_car'))
        manager.permissions.add(*Permission.objects.filter(content_type__app_label='locations',codename='view_city'))
        seo,_=Group.objects.get_or_create(name='SEO редактор')
        seo.permissions.add(*Permission.objects.filter(content_type__app_label='seo'))
        self.stdout.write('CMS groups ready. Set is_staff and assign groups to named users in Admin.')
