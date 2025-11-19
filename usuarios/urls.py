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
    path('crear_proveedor_ia/', views.crear_proveedor_ia, name="crear_proveedor_ia"),
    path('comparacion_individual_reciente/<int:comparacion_id>/', views.marcar_individual_reciente, name="marcar_individual_reciente"),
    path('comparacion_individual_destacado/<int:comparacion_id>/', views.marcar_individual_destacado, name="marcar_individual_destacado"),
    path('comparacion_individual_oculto/<int:comparacion_id>/', views.marcar_individual_oculto, name="marcar_individual_oculto"),
    path('comparacion_grupal_reciente/<int:comparacion_id>/', views.marcar_grupal_reciente, name="marcar_grupal_reciente"),
    path('comparacion_grupal_destacado/<int:comparacion_id>/', views.marcar_grupal_destacado, name="marcar_grupal_destacado"),
    path('comparacion_grupal_oculto/<int:comparacion_id>/', views.marcar_grupal_oculto, name="marcar_grupal_oculto"),
    path('listar_modelos_admin/', views.listar_modelos_admin, name='listar_modelos_admin'),
    path('listar_modelos_usuario/<int:usuario_id>/', views.listar_modelos_usuario, name='listar_modelos_usuario'),
    path('comparacion_individual/<int:comparacion_id>/', views.obtener_comparacion_individual, name="obtener_comparacion_individual"),
    path('listar_lenguajes/<int:usuario_id>', views.listar_lenguajes_usuario, name='listar_lenguajes_usuario')
]