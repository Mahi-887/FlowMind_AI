from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('login/', views.send_otp, name='send_otp'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('logout/', views.logout_view, name='logout'),

    # Dashboard
    path('', views.index, name='flowmind_index'),

    # AJAX
    path('generate/', views.generate_diagram, name='generate_diagram'),
    path('history/', views.get_history, name='get_history'),
]


