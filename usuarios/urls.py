from django.urls import path
from . import views

urlpatterns = [
    path('registrar/', views.registrar_usuario, name='registrar_usuario'),
    path('login/', views.login_usuario, name='login_usuario'),
    path('perfil/', views.perfil_usuario, name='perfil_usuario'),
    path('listar_individual/<int:usuario_id>/', views.listar_comparaciones_individuales, name='listar_comparaciones_individuales'),
    path('listar_grupal/<int:usuario_id>/', views.listar_comparaciones_grupales, name='listar_comparaciones_grupal'),
    path('crear_comparaciones_grupales/', views.crear_comparacion_grupal, name="crear_comparacion_grupal"),
    path('crear_comparaciones_individuales/', views.crear_comparacion_individual, name="crear_comparacion_individual"),
    path('crear_lenguajes/', views.crear_lenguaje, name="crear_lenguaje"),
    path('crear_modelos_ia/', views.crear_modelo_ia, name="crear_modelo_ia"),
    path('crear_proveedor_ia/', views.crear_proveedor_ia, name="crear_proveedor_ia")
]