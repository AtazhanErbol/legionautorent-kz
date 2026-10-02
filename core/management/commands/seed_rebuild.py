from django.core.management.base import BaseCommand
from core.models import SiteSettings,ContentBlock
from seo.models import Translation

class Command(BaseCommand):
    help='Add editable KK/EN partner drafts and the three source-backed rental steps.'
    def handle(self,*args,**options):
        site=SiteSettings.objects.get(pk=1)
        drafts={
            'kk':{'hero_title':'Астанада жүргізушісіз автокөлік жалдау','hero_text':'Қаладағы сапарлар мен іскерлік кездесулерге арналған автокөлікті таңдаңыз. Жалға алу шарттарын менеджермен келісіңіз.',
                  'partner_title':'Легионавто серіктесі болыңыз','partner_description':'Автокөлігіңізді бізге қосалқы жалға беру арқылы серіктесіміз бола аласыз.',
                  'partner_whatsapp_message':'Сәлеметсіз бе! Легионавто серіктесі болып, автокөлігімді қосалқы жалға бергім келеді.','footer_text':'Сіздің сапарыңызға арналған автокөлік.'},
            'en':{'hero_title':'Self-drive car rental in Astana','hero_text':'Choose a car for city journeys and business meetings. Arrange the rental details with our team.',
                  'partner_title':'Become a Legion Auto partner','partner_description':'Become our partner by providing your car to us for sublease.',
                  'partner_whatsapp_message':'Hello! I would like to become a Legion Auto partner and provide my car for sublease.','footer_text':'A car for your journey.'}
        }
        for lang,fields in drafts.items():site.translations.get_or_create(language=lang,defaults={**fields,'published':False})
        old=ContentBlock.objects.filter(kind='step',active=True)
        titles=['Позвоните нам','Получите автомобиль','Подпишите договор']
        old.exclude(title__in=titles).update(active=False)
        for order,(title,text) in enumerate(zip(titles,['Звонок на бронирование выбранного автомобиля на сайте.','Доставка автомобиля в любую точку вашего города.','Подписание договора об аренде за 10 минут.'])):
            ContentBlock.objects.get_or_create(kind='step',title=title,defaults={'text':text,'sort_order':order,'active':True})
        self.stdout.write('Partner KK/EN drafts created without overwriting edits. Original blocks retained; source-backed steps enabled.')
