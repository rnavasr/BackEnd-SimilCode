from django.urls import path
from . import views

urlpatterns = [
path('crear_lenguajes/', views.crear_lenguaje, name="crear_lenguaje"),
path('listar_lenguajes/<int:usuario_id>', views.listar_lenguajes_usuario, name='listar_lenguajes_usuario'),
path('editar_lenguajes/<int:lenguaje_id>/', views.editar_lenguaje, name="editar_lenguaje"),
path('cambiar_estado_lenguaje/<int:lenguaje_id>/', views.cambiar_estado_lenguaje, name="cambiar_estado_lenguaje"),
# URLs para Gestión de Modelos IA
path('modelos_ia/crear/', views.crear_modelo_ia, name='crear_modelo_ia'),
path('modelos_ia/listar/<int:usuario_id>/', views.listar_modelos_ia, name='listar_modelos_ia'),
path('modelos_ia/editar/<int:modelo_id>/', views.editar_modelo_ia, name='editar_modelo_ia'),
path('modelos_ia/cambiar_estado/<int:modelo_id>/', views.cambiar_estado_modelo_ia, name='cambiar_estado_modelo_ia'),
path('modelos_ia/marcar_recomendado/<int:modelo_id>/', views.marcar_recomendado_modelo_ia, name='marcar_recomendado_modelo_ia'),

# URLs para Configuración Claude
path('configuracion/claude/crear/', views.crear_configuracion_claude, name='crear_configuracion_claude'),
path('configuracion/claude/editar/<int:config_id>/', views.editar_configuracion_claude, name='editar_configuracion_claude'),

# URLs para Configuración OpenAI
path('configuracion/openai/crear/', views.crear_configuracion_openai, name='crear_configuracion_openai'),
path('configuracion/openai/editar/<int:config_id>/', views.editar_configuracion_openai, name='editar_configuracion_openai'),

# URLs para Configuración Gemini
path('configuracion/gemini/crear/', views.crear_configuracion_gemini, name='crear_configuracion_gemini'),
path('configuracion/gemini/editar/<int:config_id>/', views.editar_configuracion_gemini, name='editar_configuracion_gemini'),

# URLs para Configuración DeepSeek
path('configuracion/deepseek/crear/', views.crear_configuracion_deepseek, name='crear_configuracion_deepseek'),
path('configuracion/deepseek/editar/<int:config_id>/', views.editar_configuracion_deepseek, name='editar_configuracion_deepseek')
]