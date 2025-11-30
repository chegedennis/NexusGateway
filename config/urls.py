from django.contrib import admin
from django.urls import path, re_path
from portal import views as portal_views
from billing import views as billing_views # You need to create this view logic for callbacks

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # User Interface
    path('', portal_views.captive_portal, name='home'),
    path('pay', portal_views.initiate_payment, name='pay'),
    
    # API Callbacks (Create this in billing/views.py!)
    path('billing/callback/', billing_views.mpesa_callback, name='mpesa_callback'),
    
    # Polling & Success
    path('check_status/<str:phone>/', portal_views.check_status, name='check_status'),
    path('success/', portal_views.success_page, name='success'),

    # Captive Portal Traps
    path('generate_204', portal_views.captive_portal),
    path('ncsi.txt', portal_views.captive_portal),
    re_path(r'^.*$', portal_views.captive_portal),
]
