from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.index, name='flowmind_index'),

    # AJAX
    path('generate/', views.generate_diagram, name='generate_diagram'),
    path('history/', views.get_history, name='get_history'),
]


