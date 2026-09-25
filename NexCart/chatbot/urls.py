from django.urls import path

from . import views

app_name = 'chatbot'

urlpatterns = [
    path('health/', views.health_check, name='health_check'),
    path('chat/', views.chat, name='chat'),
    path('seller-chat/', views.seller_chat, name='seller_chat'),
]
