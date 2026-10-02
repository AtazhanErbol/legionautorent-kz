from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path,include
from django.http import Http404
from core import views
from core.legacy_assets import legacy_image,legacy_video
from seo.views import robots,sitemap

public=[path('',views.home,name='home'),path('cars/',views.catalog,name='catalog'),path('category/<slug:category_slug>/',views.catalog,name='category'),path('car/<slug:slug>',views.car_detail,name='car'),path('booking/',views.booking,name='booking'),path('callback/',views.booking,{'callback':True},name='callback'),path('request-success/',views.success,name='success'),path('faq/',views.faq_page,name='faq'),path('<slug:slug>/',views.content_page,name='page')]
def old_kazakh(request,path=''):
    # Every audited live /kz/ URL was 404. Do not redirect /kz/ to /kk/.
    raise Http404()
urlpatterns=[path(settings.ADMIN_PATH,admin.site.urls),path('healthz/',views.health),path('img/<path:path>',legacy_image),path('video/video-2.mp4',legacy_video),path('robots.txt',robots),path('sitemap.xml',sitemap),path('sitemap-<str:section>.xml',sitemap),path('kk/',include((public,'kk'))),path('en/',include((public,'en'))),path('kz/',old_kazakh),path('kz/<path:path>',old_kazakh),*public]
if settings.DEBUG:urlpatterns+=static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)
handler404='core.views.not_found'
handler500='core.views.server_error'
