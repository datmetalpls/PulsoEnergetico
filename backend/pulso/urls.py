from django.contrib import admin
from django.urls import path, re_path
from energy import views

urlpatterns = [
    path('admin/', admin.site.urls),
    re_path(r'^api/auth/(?P<action>csrf|login|logout|me)$', views.auth),
    path('api/localities', views.localities),
    path('api/sites/<slug:slug>', views.site_endpoint),
    path('api/sites/<slug:slug>/<str:action>', views.site_endpoint),
    path('api/sessions/<uuid:session_id>/zones/<slug:zone_slug>', views.session_endpoint, {'action': 'zones'}),
    path('api/sessions/<uuid:session_id>/alerts/<int:alert_id>/ack', views.session_endpoint, {'action': 'ack'}),
    path('api/sessions/<uuid:session_id>/<str:action>', views.session_endpoint),
    re_path(r'^api/(?P<path>.*)$', views.api_missing),
    re_path(r'^(?P<path>.*)$', views.spa),
]
