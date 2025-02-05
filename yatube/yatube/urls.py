from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', include('posts.urls', namespace='posts')),
    path('group/<slug:slug>/', include('posts.urls', namespace='posts')),
    path('create/', include('posts.urls', namespace='posts')),

    path('about/', include('about.urls', namespace='about')),


    path('auth/', include('users.urls')),
    path('auth/', include('django.contrib.auth.urls')),

    path('admin/', admin.site.urls),
]
handler403 = 'core.views.csrf_failure'
handler404 = 'core.views.page_not_found'
handler500 = 'core.views.error_500'

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )
