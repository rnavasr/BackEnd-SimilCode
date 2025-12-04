from django.conf import settings
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import requests
import jwt
from django.db.models import Q
from administrador.models import *

from datetime import datetime
import base64

def validar_token(request):
    """Valida el token JWT del header Authorization"""
    try:
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if not auth_header or not auth_header.startswith('Bearer '):
            return None
        
        token = auth_header.split(' ')[1]
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        return payload
        
    except jwt.ExpiredSignatureError:
        return {'error': 'Token expirado'}
    except jwt.InvalidTokenError:
        return {'error': 'Token inválido'}

@csrf_exempt
@require_http_methods(["POST"])
def crear_lenguaje(request):
    """Crear un nuevo lenguaje"""
    payload = validar_token(request)
    
    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    
    if 'error' in payload:
        return JsonResponse(payload, status=401)
    
    try:
        # Obtener datos del FormData
        nombre = request.POST.get('nombre')
        extension = request.POST.get('extension')
        usuario_id = request.POST.get('usuario_id')  # 👈 OBTENER USUARIO_ID
        
        # Validaciones
        if not nombre:
            return JsonResponse({
                'error': 'El campo nombre es requerido'
            }, status=400)
        
        if not usuario_id:
            return JsonResponse({
                'error': 'El campo usuario_id es requerido'
            }, status=400)
        
        # Verificar si ya existe
        if Lenguajes.objects.filter(nombre=nombre).exists():
            return JsonResponse({
                'error': f'El lenguaje "{nombre}" ya existe'
            }, status=400)
        
        # Obtener el usuario
        try:
            usuario = Usuarios.objects.get(id=usuario_id)
        except Usuarios.DoesNotExist:
            return JsonResponse({
                'error': 'Usuario no encontrado'
            }, status=404)
        
        # Crear el lenguaje con el usuario
        lenguaje = Lenguajes.objects.create(
            nombre=nombre,
            extension=extension,
            usuario=usuario  # 👈 ASIGNAR USUARIO
        )
        
        return JsonResponse({
            'mensaje': 'Lenguaje creado exitosamente',
            'id': lenguaje.id,
            'nombre': lenguaje.nombre,
            'extension': lenguaje.extension
        }, status=201)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def listar_lenguajes_usuario(request, usuario_id):
    """Listar lenguajes creados por admins o por el usuario actual"""
    payload = validar_token(request)
    
    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    
    if 'error' in payload:
        return JsonResponse(payload, status=401)
    
    try:
        # Obtener IDs de todos los usuarios admin
        usuarios_admin_ids = list(Usuarios.objects.filter(
            rol__nombre__iexact='admin'
        ).values_list('id', flat=True))
        
        # Obtener lenguajes creados por admins O por el usuario actual
        lenguajes = Lenguajes.objects.filter(
            Q(usuario_id__in=usuarios_admin_ids) | 
            Q(usuario_id=usuario_id)
        ).values(
            'id', 
            'nombre', 
            'extension',
            'estado'
        ).order_by('nombre')
        
        return JsonResponse({
            'lenguajes': list(lenguajes)
        }, status=200)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
@csrf_exempt
@require_http_methods(["PUT", "POST"])
def editar_lenguaje(request, lenguaje_id):
    """Editar un lenguaje existente"""
    payload = validar_token(request)
    
    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    
    if 'error' in payload:
        return JsonResponse(payload, status=401)
    
    try:
        # Buscar el lenguaje
        try:
            lenguaje = Lenguajes.objects.get(id=lenguaje_id)
        except Lenguajes.DoesNotExist:
            return JsonResponse({'error': 'Lenguaje no encontrado'}, status=404)
        
        # Obtener datos
        nombre = request.POST.get('nombre')
        extension = request.POST.get('extension')
        
        # Validaciones
        if not nombre:
            return JsonResponse({'error': 'El campo nombre es requerido'}, status=400)
        
        # Verificar duplicados (excluyendo el actual)
        if Lenguajes.objects.filter(nombre=nombre).exclude(id=lenguaje_id).exists():
            return JsonResponse({
                'error': f'El lenguaje "{nombre}" ya existe'
            }, status=400)
        
        # Actualizar
        lenguaje.nombre = nombre
        lenguaje.extension = extension
        lenguaje.save()
        
        return JsonResponse({
            'mensaje': 'Lenguaje actualizado exitosamente',
            'id': lenguaje.id,
            'nombre': lenguaje.nombre,
            'extension': lenguaje.extension
        }, status=200)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
@csrf_exempt
@require_http_methods(["PUT", "POST"])  # Aceptar ambos métodos
def cambiar_estado_lenguaje(request, lenguaje_id):
    """Cambiar el estado de un lenguaje (activar/desactivar)"""
    payload = validar_token(request)
    
    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    
    if 'error' in payload:
        return JsonResponse(payload, status=401)
    
    try:
        # Buscar el lenguaje - CORREGIR EL NOMBRE DEL CAMPO
        try:
            lenguaje = Lenguajes.objects.get(id=lenguaje_id)  # Cambiar id_lenguaje por id
        except Lenguajes.DoesNotExist:
            return JsonResponse({'error': 'Lenguaje no encontrado'}, status=404)
        
        # Cambiar el estado (toggle)
        lenguaje.estado = not lenguaje.estado
        lenguaje.save()
        
        estado_texto = "activado" if lenguaje.estado else "desactivado"
        
        return JsonResponse({
            'mensaje': f'Lenguaje {estado_texto} exitosamente',
            'id': lenguaje.id,  # Cambiar id_lenguaje por id
            'nombre': lenguaje.nombre,
            'estado': lenguaje.estado
        }, status=200)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    

# ============================================================================
# 1. GESTIÓN DE MODELOS IA (CRUD Completo)
# ============================================================================

@csrf_exempt
@require_http_methods(["POST"])
def crear_modelo_ia(request):
    """Crear un nuevo modelo de IA"""
    payload = validar_token(request)
    
    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    
    if 'error' in payload:
        return JsonResponse(payload, status=401)
    
    try:
        # Obtener datos
        nombre = request.POST.get('nombre')
        version = request.POST.get('version', '')
        proveedor_id = request.POST.get('proveedor_id')
        descripcion = request.POST.get('descripcion', '')
        color_ia = request.POST.get('color_ia', '#5ebd8f')
        usuario_id = request.POST.get('usuario_id')
        
        # Manejar imagen (opcional)
        imagen_ia = None
        if 'imagen_ia' in request.FILES:
            imagen_file = request.FILES['imagen_ia']
            imagen_ia = imagen_file.read()
        
        # Validaciones
        if not nombre:
            return JsonResponse({'error': 'El nombre es requerido'}, status=400)
        
        if not proveedor_id:
            return JsonResponse({'error': 'El proveedor es requerido'}, status=400)
        
        if not usuario_id:
            return JsonResponse({'error': 'El usuario_id es requerido'}, status=400)
        
        # Verificar si ya existe
        if ModelosIa.objects.filter(nombre=nombre).exists():
            return JsonResponse({'error': f'El modelo "{nombre}" ya existe'}, status=400)
        
        # Verificar que existe el proveedor
        try:
            proveedor = ProveedoresIa.objects.get(id=proveedor_id)
        except ProveedoresIa.DoesNotExist:
            return JsonResponse({'error': 'Proveedor no encontrado'}, status=404)
        
        # Verificar que existe el usuario
        try:
            usuario = Usuarios.objects.get(id=usuario_id)
        except Usuarios.DoesNotExist:
            return JsonResponse({'error': 'Usuario no encontrado'}, status=404)
        
        # Crear el modelo
        modelo = ModelosIa.objects.create(
            nombre=nombre,
            version=version,
            proveedor=proveedor,
            descripcion=descripcion,
            activo=True,
            fecha_creacion=datetime.now(),
            recomendado=False,
            imagen_ia=imagen_ia,
            color_ia=color_ia,
            id_usuario=usuario
        )
        
        return JsonResponse({
            'mensaje': 'Modelo de IA creado exitosamente',
            'id': modelo.id,
            'nombre': modelo.nombre,
            'version': modelo.version,
            'proveedor': modelo.proveedor.nombre if modelo.proveedor else None
        }, status=201)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def listar_modelos_ia(request, usuario_id):
    """Listar modelos de IA creados por admins o por el usuario actual"""
    payload = validar_token(request)
    
    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    
    if 'error' in payload:
        return JsonResponse(payload, status=401)
    
    try:
        from django.db.models import Q
        
        # Obtener IDs de todos los usuarios admin
        usuarios_admin_ids = list(Usuarios.objects.filter(
            rol__nombre__iexact='admin'
        ).values_list('id', flat=True))
        
        # Obtener modelos creados por admins O por el usuario actual
        modelos = ModelosIa.objects.filter(
            Q(id_usuario_id__in=usuarios_admin_ids) | 
            Q(id_usuario_id=usuario_id)
        ).select_related('proveedor', 'id_usuario').order_by('-fecha_creacion')
        
        modelos_data = []
        for modelo in modelos:
            # Convertir imagen a base64 si existe
            imagen_base64 = None
            if modelo.imagen_ia:
                imagen_base64 = base64.b64encode(modelo.imagen_ia).decode('utf-8')
            
            modelos_data.append({
                'id': modelo.id,
                'nombre': modelo.nombre,
                'version': modelo.version,
                'proveedor': {
                    'id': modelo.proveedor.id if modelo.proveedor else None,
                    'nombre': modelo.proveedor.nombre if modelo.proveedor else None
                },
                'descripcion': modelo.descripcion,
                'activo': modelo.activo,
                'recomendado': modelo.recomendado,
                'color_ia': modelo.color_ia,
                'imagen_ia': imagen_base64,
                'fecha_creacion': modelo.fecha_creacion.isoformat() if modelo.fecha_creacion else None
            })
        
        return JsonResponse({
            'modelos': modelos_data
        }, status=200)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["PUT", "POST"])
def editar_modelo_ia(request, modelo_id):
    """Editar un modelo de IA existente"""
    payload = validar_token(request)
    
    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    
    if 'error' in payload:
        return JsonResponse(payload, status=401)
    
    try:
        # Buscar el modelo
        try:
            modelo = ModelosIa.objects.get(id=modelo_id)
        except ModelosIa.DoesNotExist:
            return JsonResponse({'error': 'Modelo no encontrado'}, status=404)
        
        # Obtener datos
        nombre = request.POST.get('nombre')
        version = request.POST.get('version')
        proveedor_id = request.POST.get('proveedor_id')
        descripcion = request.POST.get('descripcion')
        color_ia = request.POST.get('color_ia')
        
        # Validaciones
        if nombre:
            # Verificar duplicados (excluyendo el actual)
            if ModelosIa.objects.filter(nombre=nombre).exclude(id=modelo_id).exists():
                return JsonResponse({'error': f'El modelo "{nombre}" ya existe'}, status=400)
            modelo.nombre = nombre
        
        if version is not None:
            modelo.version = version
        
        if proveedor_id:
            try:
                proveedor = ProveedoresIa.objects.get(id=proveedor_id)
                modelo.proveedor = proveedor
            except ProveedoresIa.DoesNotExist:
                return JsonResponse({'error': 'Proveedor no encontrado'}, status=404)
        
        if descripcion is not None:
            modelo.descripcion = descripcion
        
        if color_ia:
            modelo.color_ia = color_ia
        
        # Manejar imagen si se envió
        if 'imagen_ia' in request.FILES:
            imagen_file = request.FILES['imagen_ia']
            modelo.imagen_ia = imagen_file.read()
        
        modelo.save()
        
        return JsonResponse({
            'mensaje': 'Modelo actualizado exitosamente',
            'id': modelo.id,
            'nombre': modelo.nombre
        }, status=200)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["PUT", "POST"])
def cambiar_estado_modelo_ia(request, modelo_id):
    """Cambiar el estado activo de un modelo de IA"""
    payload = validar_token(request)
    
    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    
    if 'error' in payload:
        return JsonResponse(payload, status=401)
    
    try:
        try:
            modelo = ModelosIa.objects.get(id=modelo_id)
        except ModelosIa.DoesNotExist:
            return JsonResponse({'error': 'Modelo no encontrado'}, status=404)
        
        # Cambiar el estado
        modelo.activo = not modelo.activo
        modelo.save()
        
        estado_texto = "activado" if modelo.activo else "desactivado"
        
        return JsonResponse({
            'mensaje': f'Modelo {estado_texto} exitosamente',
            'id': modelo.id,
            'nombre': modelo.nombre,
            'activo': modelo.activo
        }, status=200)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["PUT", "POST"])
def marcar_recomendado_modelo_ia(request, modelo_id):
    """Marcar/desmarcar un modelo como recomendado"""
    payload = validar_token(request)
    
    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    
    if 'error' in payload:
        return JsonResponse(payload, status=401)
    
    try:
        try:
            modelo = ModelosIa.objects.get(id=modelo_id)
        except ModelosIa.DoesNotExist:
            return JsonResponse({'error': 'Modelo no encontrado'}, status=404)
        
        # Cambiar estado de recomendado
        modelo.recomendado = not modelo.recomendado
        modelo.save()
        
        estado_texto = "marcado como recomendado" if modelo.recomendado else "desmarcado como recomendado"
        
        return JsonResponse({
            'mensaje': f'Modelo {estado_texto} exitosamente',
            'id': modelo.id,
            'nombre': modelo.nombre,
            'recomendado': modelo.recomendado
        }, status=200)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================================
# 2. CONFIGURACIÓN CLAUDE
# ============================================================================

@csrf_exempt
@require_http_methods(["POST"])
def crear_configuracion_claude(request):
    """Crear configuración para Claude"""
    payload = validar_token(request)
    
    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    
    if 'error' in payload:
        return JsonResponse(payload, status=401)
    
    try:
        # Obtener datos
        modelo_ia_id = request.POST.get('modelo_ia_id')
        prompt_id = request.POST.get('prompt_id')
        endpoint_url = request.POST.get('endpoint_url')
        api_key = request.POST.get('api_key')
        model_name = request.POST.get('model_name')
        max_tokens = request.POST.get('max_tokens', 4000)
        anthropic_version = request.POST.get('anthropic_version', '2023-06-01')
        
        # Validaciones
        if not all([modelo_ia_id, prompt_id, endpoint_url, api_key, model_name]):
            return JsonResponse({'error': 'Todos los campos son requeridos'}, status=400)
        
        # Verificar que no exista ya una configuración para este modelo
        if ConfiguracionClaude.objects.filter(id_modelo_ia_id=modelo_ia_id).exists():
            return JsonResponse({'error': 'Ya existe una configuración para este modelo'}, status=400)
        
        # Verificar que existen el modelo y el prompt
        try:
            modelo = ModelosIa.objects.get(id=modelo_ia_id)
        except ModelosIa.DoesNotExist:
            return JsonResponse({'error': 'Modelo de IA no encontrado'}, status=404)
        
        try:
            prompt = PromptComparacion.objects.get(id=prompt_id)
        except PromptComparacion.DoesNotExist:
            return JsonResponse({'error': 'Prompt no encontrado'}, status=404)
        
        # Crear configuración
        config = ConfiguracionClaude.objects.create(
            id_modelo_ia=modelo,
            id_prompt=prompt,
            endpoint_url=endpoint_url,
            api_key=api_key,
            model_name=model_name,
            max_tokens=int(max_tokens),
            anthropic_version=anthropic_version,
            activo=True,
            fecha_creacion=datetime.now(),
            fecha_modificacion=datetime.now()
        )
        
        return JsonResponse({
            'mensaje': 'Configuración de Claude creada exitosamente',
            'id': config.id_config_claude,
            'modelo': modelo.nombre
        }, status=201)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["PUT", "POST"])
def editar_configuracion_claude(request, config_id):
    """Editar configuración de Claude"""
    payload = validar_token(request)
    
    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    
    if 'error' in payload:
        return JsonResponse(payload, status=401)
    
    try:
        try:
            config = ConfiguracionClaude.objects.get(id_config_claude=config_id)
        except ConfiguracionClaude.DoesNotExist:
            return JsonResponse({'error': 'Configuración no encontrada'}, status=404)
        
        # Actualizar campos
        if 'endpoint_url' in request.POST:
            config.endpoint_url = request.POST.get('endpoint_url')
        if 'api_key' in request.POST:
            config.api_key = request.POST.get('api_key')
        if 'model_name' in request.POST:
            config.model_name = request.POST.get('model_name')
        if 'max_tokens' in request.POST:
            config.max_tokens = int(request.POST.get('max_tokens'))
        if 'anthropic_version' in request.POST:
            config.anthropic_version = request.POST.get('anthropic_version')
        if 'prompt_id' in request.POST:
            try:
                prompt = PromptComparacion.objects.get(id=request.POST.get('prompt_id'))
                config.id_prompt = prompt
            except PromptComparacion.DoesNotExist:
                return JsonResponse({'error': 'Prompt no encontrado'}, status=404)
        
        config.fecha_modificacion = datetime.now()
        config.save()
        
        return JsonResponse({
            'mensaje': 'Configuración de Claude actualizada exitosamente',
            'id': config.id_config_claude
        }, status=200)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================================
# 3. CONFIGURACIÓN OPENAI
# ============================================================================

@csrf_exempt
@require_http_methods(["POST"])
def crear_configuracion_openai(request):
    """Crear configuración para OpenAI"""
    payload = validar_token(request)
    
    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    
    if 'error' in payload:
        return JsonResponse(payload, status=401)
    
    try:
        modelo_ia_id = request.POST.get('modelo_ia_id')
        prompt_id = request.POST.get('prompt_id')
        endpoint_url = request.POST.get('endpoint_url')
        api_key = request.POST.get('api_key')
        model_name = request.POST.get('model_name')
        max_tokens = request.POST.get('max_tokens', 4000)
        temperature = request.POST.get('temperature', '0.7')
        
        if not all([modelo_ia_id, prompt_id, endpoint_url, api_key, model_name]):
            return JsonResponse({'error': 'Todos los campos son requeridos'}, status=400)
        
        if ConfiguracionOpenai.objects.filter(id_modelo_ia_id=modelo_ia_id).exists():
            return JsonResponse({'error': 'Ya existe una configuración para este modelo'}, status=400)
        
        try:
            modelo = ModelosIa.objects.get(id=modelo_ia_id)
            prompt = PromptComparacion.objects.get(id=prompt_id)
        except (ModelosIa.DoesNotExist, PromptComparacion.DoesNotExist) as e:
            return JsonResponse({'error': str(e)}, status=404)
        
        config = ConfiguracionOpenai.objects.create(
            id_modelo_ia=modelo,
            id_prompt=prompt,
            endpoint_url=endpoint_url,
            api_key=api_key,
            model_name=model_name,
            max_tokens=int(max_tokens),
            temperature=float(temperature),
            activo=True,
            fecha_creacion=datetime.now(),
            fecha_modificacion=datetime.now()
        )
        
        return JsonResponse({
            'mensaje': 'Configuración de OpenAI creada exitosamente',
            'id': config.id_config_openai,
            'modelo': modelo.nombre
        }, status=201)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["PUT", "POST"])
def editar_configuracion_openai(request, config_id):
    """Editar configuración de OpenAI"""
    payload = validar_token(request)
    
    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    
    if 'error' in payload:
        return JsonResponse(payload, status=401)
    
    try:
        try:
            config = ConfiguracionOpenai.objects.get(id_config_openai=config_id)
        except ConfiguracionOpenai.DoesNotExist:
            return JsonResponse({'error': 'Configuración no encontrada'}, status=404)
        
        if 'endpoint_url' in request.POST:
            config.endpoint_url = request.POST.get('endpoint_url')
        if 'api_key' in request.POST:
            config.api_key = request.POST.get('api_key')
        if 'model_name' in request.POST:
            config.model_name = request.POST.get('model_name')
        if 'max_tokens' in request.POST:
            config.max_tokens = int(request.POST.get('max_tokens'))
        if 'temperature' in request.POST:
            config.temperature = float(request.POST.get('temperature'))
        if 'prompt_id' in request.POST:
            try:
                prompt = PromptComparacion.objects.get(id=request.POST.get('prompt_id'))
                config.id_prompt = prompt
            except PromptComparacion.DoesNotExist:
                return JsonResponse({'error': 'Prompt no encontrado'}, status=404)
        
        config.fecha_modificacion = datetime.now()
        config.save()
        
        return JsonResponse({
            'mensaje': 'Configuración de OpenAI actualizada exitosamente',
            'id': config.id_config_openai
        }, status=200)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================================
# 4. CONFIGURACIÓN GEMINI
# ============================================================================

@csrf_exempt
@require_http_methods(["POST"])
def crear_configuracion_gemini(request):
    """Crear configuración para Gemini"""
    payload = validar_token(request)
    
    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    
    if 'error' in payload:
        return JsonResponse(payload, status=401)
    
    try:
        modelo_ia_id = request.POST.get('modelo_ia_id')
        prompt_id = request.POST.get('prompt_id')
        endpoint_url = request.POST.get('endpoint_url')
        api_key = request.POST.get('api_key')
        model_name = request.POST.get('model_name')
        max_tokens = request.POST.get('max_tokens', 4000)
        temperature = request.POST.get('temperature', '0.7')
        
        if not all([modelo_ia_id, prompt_id, endpoint_url, api_key, model_name]):
            return JsonResponse({'error': 'Todos los campos son requeridos'}, status=400)
        
        if ConfiguracionGemini.objects.filter(id_modelo_ia_id=modelo_ia_id).exists():
            return JsonResponse({'error': 'Ya existe una configuración para este modelo'}, status=400)
        
        try:
            modelo = ModelosIa.objects.get(id=modelo_ia_id)
            prompt = PromptComparacion.objects.get(id=prompt_id)
        except (ModelosIa.DoesNotExist, PromptComparacion.DoesNotExist) as e:
            return JsonResponse({'error': str(e)}, status=404)
        
        config = ConfiguracionGemini.objects.create(
            id_modelo_ia=modelo,
            id_prompt=prompt,
            endpoint_url=endpoint_url,
            api_key=api_key,
            model_name=model_name,
            max_tokens=int(max_tokens),
            temperature=float(temperature),
            activo=True,
            fecha_creacion=datetime.now(),
            fecha_modificacion=datetime.now()
        )
        
        return JsonResponse({
            'mensaje': 'Configuración de Gemini creada exitosamente',
            'id': config.id_config_gemini,
            'modelo': modelo.nombre
        }, status=201)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["PUT", "POST"])
def editar_configuracion_gemini(request, config_id):
    """Editar configuración de Gemini"""
    payload = validar_token(request)
    
    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    
    if 'error' in payload:
        return JsonResponse(payload, status=401)
    
    try:
        try:
            config = ConfiguracionGemini.objects.get(id_config_gemini=config_id)
        except ConfiguracionGemini.DoesNotExist:
            return JsonResponse({'error': 'Configuración no encontrada'}, status=404)
        
        if 'endpoint_url' in request.POST:
            config.endpoint_url = request.POST.get('endpoint_url')
        if 'api_key' in request.POST:
            config.api_key = request.POST.get('api_key')
        if 'model_name' in request.POST:
            config.model_name = request.POST.get('model_name')
        if 'max_tokens' in request.POST:
            config.max_tokens = int(request.POST.get('max_tokens'))
        if 'temperature' in request.POST:
            config.temperature = float(request.POST.get('temperature'))
        if 'prompt_id' in request.POST:
            try:
                prompt = PromptComparacion.objects.get(id=request.POST.get('prompt_id'))
                config.id_prompt = prompt
            except PromptComparacion.DoesNotExist:
                return JsonResponse({'error': 'Prompt no encontrado'}, status=404)
        
        config.fecha_modificacion = datetime.now()
        config.save()
        
        return JsonResponse({
            'mensaje': 'Configuración de Gemini actualizada exitosamente',
            'id': config.id_config_gemini
        }, status=200)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============================================================================
# 5. CONFIGURACIÓN DEEPSEEK
# ============================================================================

@csrf_exempt
@require_http_methods(["POST"])
def crear_configuracion_deepseek(request):
    """Crear configuración para DeepSeek"""
    payload = validar_token(request)
    
    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    
    if 'error' in payload:
        return JsonResponse(payload, status=401)
    
    try:
        modelo_ia_id = request.POST.get('modelo_ia_id')
        prompt_id = request.POST.get('prompt_id')
        endpoint_url = request.POST.get('endpoint_url')
        api_key = request.POST.get('api_key')
        model_name = request.POST.get('model_name')
        max_tokens = request.POST.get('max_tokens', 4000)
        temperature = request.POST.get('temperature', '0.7')
        
        if not all([modelo_ia_id, prompt_id, endpoint_url, api_key, model_name]):
            return JsonResponse({'error': 'Todos los campos son requeridos'}, status=400)
        
        if ConfiguracionDeepseek.objects.filter(id_modelo_ia_id=modelo_ia_id).exists():
            return JsonResponse({'error': 'Ya existe una configuración para este modelo'}, status=400)
        
        try:
            modelo = ModelosIa.objects.get(id=modelo_ia_id)
            prompt = PromptComparacion.objects.get(id=prompt_id)
        except (ModelosIa.DoesNotExist, PromptComparacion.DoesNotExist) as e:
            return JsonResponse({'error': str(e)}, status=404)
        
        config = ConfiguracionDeepseek.objects.create(
            id_modelo_ia=modelo,
            id_prompt=prompt,
            endpoint_url=endpoint_url,
            api_key=api_key,
            model_name=model_name,
            max_tokens=int(max_tokens),
            temperature=float(temperature),
            activo=True,
            fecha_creacion=datetime.now(),
            fecha_modificacion=datetime.now()
        )
        
        return JsonResponse({
            'mensaje': 'Configuración de DeepSeek creada exitosamente',
            'id': config.id_config_deepseek,
            'modelo': modelo.nombre
        }, status=201)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["PUT", "POST"])
def editar_configuracion_deepseek(request, config_id):
    """Editar configuración de DeepSeek"""
    payload = validar_token(request)
    
    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    
    if 'error' in payload:
        return JsonResponse(payload, status=401)
    
    try:
        try:
            config = ConfiguracionDeepseek.objects.get(id_config_deepseek=config_id)
        except ConfiguracionDeepseek.DoesNotExist:
            return JsonResponse({'error': 'Configuración no encontrada'}, status=404)
        
        if 'endpoint_url' in request.POST:
            config.endpoint_url = request.POST.get('endpoint_url')
        if 'api_key' in request.POST:
            config.api_key = request.POST.get('api_key')
        if 'model_name' in request.POST:
            config.model_name = request.POST.get('model_name')
        if 'max_tokens' in request.POST:
            config.max_tokens = int(request.POST.get('max_tokens'))
        if 'temperature' in request.POST:
            config.temperature = float(request.POST.get('temperature'))
        if 'prompt_id' in request.POST:
            try:
                prompt = PromptComparacion.objects.get(id=request.POST.get('prompt_id'))
                config.id_prompt = prompt
            except PromptComparacion.DoesNotExist:
                return JsonResponse({'error': 'Prompt no encontrado'}, status=404)
        
        config.fecha_modificacion = datetime.now()
        config.save()
        
        return JsonResponse({
            'mensaje': 'Configuración de DeepSeek actualizada exitosamente',
            'id': config.id_config_deepseek
        }, status=200)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)