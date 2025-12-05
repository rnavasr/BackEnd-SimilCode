from django.urls import path
from . import views

urlpatterns = [
path('crear_lenguajes/', views.crear_lenguaje, name="crear_lenguaje"),
path('listar_lenguajes/<int:usuario_id>/', views.listar_lenguajes_usuario, name='listar_lenguajes_usuario'),
path('editar_lenguajes/<int:lenguaje_id>/', views.editar_lenguaje, name="editar_lenguaje"),
path('cambiar_estado_lenguaje/<int:lenguaje_id>/', views.cambiar_estado_lenguaje, name="cambiar_estado_lenguaje"),
path('listar_proveedores/',views.listar_proveedores, name='listar_proveedores'),
path('crear_modelo_claude/', views.crear_modelo_claude, name='crear_modelo_claude'),
path('crear_modelo_deepseek/', views.crear_modelo_deepseek, name='crear_modelo_deepseek'),
path('crear_modelo_gemini/', views.crear_modelo_gemini, name='crear_modelo_gemini'),
path('crear_modelo_openai/', views.crear_modelo_openai, name='crear_modelo_openai'),
path('editar_modelo_claude/<int:id_modelo>/', views.editar_modelo_claude, name='editar_modelo_claude'),
path('editar_modelo_deepseek/<int:id_modelo>/', views.editar_modelo_deepseek, name='editar_modelo_deepseek'),
path('editar_modelo_gemini/<int:id_modelo>/', views.editar_modelo_gemini, name='editar_modelo_gemini'),
path('editar_modelo_openai/<int:id_modelo>/', views.editar_modelo_openai, name='editar_modelo_openai'),
path('listar_modelos_usuario/', views.listar_modelos_usuario, name='listar_modelos_usuario'),
path('cambiar_estado_modelo/<int:id_modelo>/', views.cambiar_estado_modelo, name='cambiar_estado_modelo'),
path('marcar_modelo_recomendado/<int:id_modelo>/', views.marcar_recomendado, name='marcar_modelo_recomendado'),
path('listar_comparaciones/', views.listar_comparaciones, name='listar_comparaciones'),
path('cambiar_estado_comparacion/<int:id_comparacion>/', views.cambiar_estado_comparacion, name='cambiar_estado_comparacion')
]