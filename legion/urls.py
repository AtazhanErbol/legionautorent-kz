from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from core import views
from seo.views import robots, sitemap

public = [path('', views.home, name='home'), path('cars/', views.catalog, name='catalog'), path('category/<slug:category_slug>/', views.catalog, name='category'), path('car/<slug:slug>', views.car_detail, name='car'), path('booking/', views.booking, name='booking'), path('request-success/', views.success, name='success'), path('<slug:slug>/', views.content_page, name='page')]
urlpatterns = [path('admin/', admin.site.urls), path('robots.txt', robots), path('sitemap.xml', sitemap), path('kz/', include((public, 'kk'))), path('en/', include((public, 'en'))), *public]
if settings.DEBUG: urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
handler404 = 'core.views.not_found'
