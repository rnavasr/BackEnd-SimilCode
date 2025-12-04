from django.urls import path
from . import views

urlpatterns = [
path('crear_lenguajes/', views.crear_lenguaje, name="crear_lenguaje"),
path('listar_lenguajes/<int:usuario_id>', views.listar_lenguajes_usuario, name='listar_lenguajes_usuario'),
path('editar_lenguajes/<int:lenguaje_id>/', views.editar_lenguaje, name="editar_lenguaje"),
path('cambiar_estado_lenguaje/<int:lenguaje_id>/', views.cambiar_estado_lenguaje, name="cambiar_estado_lenguaje"),
]