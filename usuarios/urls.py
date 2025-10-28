from django.urls import path
from . import views

urlpatterns = [
    path('registrar/', views.registrar_usuario, name='registrar_usuario'),
    path('login/', views.login_usuario, name='login_usuario'),
    path('perfil/', views.perfil_usuario, name='perfil_usuario'),
    path('listar_individual/<int:usuario_id>/', views.listar_comparaciones_individuales, name='listar_comparaciones_individuales'),
    path('listar_grupal/<int:usuario_id>/', views.listar_comparaciones_grupales, name='listar_comparaciones_grupal'),
]