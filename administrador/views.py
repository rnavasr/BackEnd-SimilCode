from django.conf import settings
from django.shortcuts import render
from django.http import JsonResponse, QueryDict
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import requests
import jwt
from django.db.models import Q
from administrador.models import *
from django.utils import timezone
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
    
@require_http_methods(["GET"])
def listar_proveedores(request):
    """Listar todos los proveedores de IA"""
    payload = validar_token(request)
    
    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    
    if 'error' in payload:
        return JsonResponse(payload, status=401)
    
    try:
        proveedores = ProveedoresIa.objects.all().order_by('nombre')
        
        proveedores_data = [{
            'id': p.id,
            'nombre': p.nombre,
            'descripcion': p.descripcion,
            'logo_url': p.logo_url,
            'sitio_web': p.sitio_web,
            'activo': p.activo
        } for p in proveedores]
        
        return JsonResponse({'proveedores': proveedores_data}, status=200)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
@csrf_exempt
@require_http_methods(["POST"])
def crear_modelo_claude(request):
    """Crear modelo IA + configuración Claude"""
    payload = validar_token(request)

    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    if 'error' in payload:
        return JsonResponse(payload, status=401)

    try:
        # Datos del modelo principal
        nombre = request.POST.get('nombre')
        version = request.POST.get('version')
        descripcion = request.POST.get('descripcion')
        color_ia = request.POST.get('color_ia')
        proveedor_id = 1  # Claude = 1
        usuario_id = request.POST.get('usuario_id')

        # Validaciones básicas
        if not nombre:
            return JsonResponse({'error': 'El campo nombre es requerido'}, status=400)
        if not usuario_id:
            return JsonResponse({'error': 'El campo usuario_id es requerido'}, status=400)

        # Validar que no exista el modelo
        if ModelosIa.objects.filter(nombre=nombre).exists():
            return JsonResponse({'error': f'El modelo "{nombre}" ya existe'}, status=400)

        # Obtener usuario
        try:
            usuario = Usuarios.objects.get(id=usuario_id)
        except Usuarios.DoesNotExist:
            return JsonResponse({'error': 'Usuario no encontrado'}, status=404)

        # Crear modelo IA
        modelo = ModelosIa.objects.create(
            nombre=nombre,
            version=version,
            proveedor_id=proveedor_id,
            descripcion=descripcion,
            activo=True,
            recomendado=False,
            fecha_creacion=timezone.now(),
            color_ia=color_ia,
            id_usuario=usuario
        )

        # Crear configuración Claude
        ConfiguracionClaude.objects.create(
            id_modelo_ia=modelo,
            id_prompt_id=1,
            endpoint_url=request.POST.get("endpoint_url", ""),
            api_key=request.POST.get("api_key", ""),
            model_name=request.POST.get("model_name", ""),
            max_tokens=request.POST.get("max_tokens"),
            anthropic_version=request.POST.get("anthropic_version"),
            activo=True,
            fecha_creacion=timezone.now(),
            fecha_modificacion=timezone.now()
        )

        return JsonResponse({
            "mensaje": "Modelo Claude creado exitosamente",
            "id": modelo.id,
            "nombre": modelo.nombre
        }, status=201)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def crear_modelo_deepseek(request):
    """Crear modelo DeepSeek + configuración"""
    payload = validar_token(request)

    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    if 'error' in payload:
        return JsonResponse(payload, status=401)

    try:
        nombre = request.POST.get('nombre')
        version = request.POST.get('version')
        descripcion = request.POST.get('descripcion')
        color_ia = request.POST.get('color_ia')
        proveedor_id = 2  # DeepSeek = 2
        usuario_id = request.POST.get('usuario_id')

        if not nombre:
            return JsonResponse({'error': 'El campo nombre es requerido'}, status=400)
        if not usuario_id:
            return JsonResponse({'error': 'El campo usuario_id es requerido'}, status=400)

        if ModelosIa.objects.filter(nombre=nombre).exists():
            return JsonResponse({'error': f'El modelo "{nombre}" ya existe'}, status=400)

        try:
            usuario = Usuarios.objects.get(id=usuario_id)
        except Usuarios.DoesNotExist:
            return JsonResponse({'error': 'Usuario no encontrado'}, status=404)

        modelo = ModelosIa.objects.create(
            nombre=nombre,
            version=version,
            proveedor_id=proveedor_id,
            descripcion=descripcion,
            activo=True,
            recomendado=False,
            fecha_creacion=timezone.now(),
            color_ia=color_ia,
            id_usuario=usuario
        )

        ConfiguracionDeepseek.objects.create(
            id_modelo_ia=modelo,
            id_prompt_id=1,
            endpoint_url=request.POST.get("endpoint_url", ""),
            api_key=request.POST.get("api_key", ""),
            model_name=request.POST.get("model_name", ""),
            max_tokens=request.POST.get("max_tokens"),
            temperature=request.POST.get("temperature"),
            activo=True,
            fecha_creacion=timezone.now(),
            fecha_modificacion=timezone.now()
        )

        return JsonResponse({
            "mensaje": "Modelo DeepSeek creado exitosamente",
            "id": modelo.id,
            "nombre": modelo.nombre
        }, status=201)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def crear_modelo_gemini(request):
    """Crear modelo Gemini + configuración"""
    payload = validar_token(request)

    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    if 'error' in payload:
        return JsonResponse(payload, status=401)

    try:
        nombre = request.POST.get('nombre')
        version = request.POST.get('version')
        descripcion = request.POST.get('descripcion')
        color_ia = request.POST.get('color_ia')
        proveedor_id = 3  # Gemini = 3
        usuario_id = request.POST.get('usuario_id')

        if not nombre:
            return JsonResponse({'error': 'El campo nombre es requerido'}, status=400)
        if not usuario_id:
            return JsonResponse({'error': 'El campo usuario_id es requerido'}, status=400)

        if ModelosIa.objects.filter(nombre=nombre).exists():
            return JsonResponse({'error': f'El modelo "{nombre}" ya existe'}, status=400)

        try:
            usuario = Usuarios.objects.get(id=usuario_id)
        except Usuarios.DoesNotExist:
            return JsonResponse({'error': 'Usuario no encontrado'}, status=404)

        modelo = ModelosIa.objects.create(
            nombre=nombre,
            version=version,
            proveedor_id=proveedor_id,
            descripcion=descripcion,
            activo=True,
            recomendado=False,
            fecha_creacion=timezone.now(),
            color_ia=color_ia,
            id_usuario=usuario
        )

        ConfiguracionGemini.objects.create(
            id_modelo_ia=modelo,
            id_prompt_id=1,
            endpoint_url=request.POST.get("endpoint_url", ""),
            api_key=request.POST.get("api_key", ""),
            model_name=request.POST.get("model_name", ""),
            max_tokens=request.POST.get("max_tokens"),
            temperature=request.POST.get("temperature"),
            activo=True,
            fecha_creacion=timezone.now(),
            fecha_modificacion=timezone.now()
        )

        return JsonResponse({
            "mensaje": "Modelo Gemini creado exitosamente",
            "id": modelo.id,
            "nombre": modelo.nombre
        }, status=201)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def crear_modelo_openai(request):
    """Crear modelo OpenAI + configuración"""
    payload = validar_token(request)

    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    if 'error' in payload:
        return JsonResponse(payload, status=401)

    try:
        nombre = request.POST.get('nombre')
        version = request.POST.get('version')
        descripcion = request.POST.get('descripcion')
        color_ia = request.POST.get('color_ia')
        proveedor_id = 4  # OpenAI = 4
        usuario_id = request.POST.get('usuario_id')

        if not nombre:
            return JsonResponse({'error': 'El campo nombre es requerido'}, status=400)
        if not usuario_id:
            return JsonResponse({'error': 'El campo usuario_id es requerido'}, status=400)

        if ModelosIa.objects.filter(nombre=nombre).exists():
            return JsonResponse({'error': f'El modelo "{nombre}" ya existe'}, status=400)

        try:
            usuario = Usuarios.objects.get(id=usuario_id)
        except Usuarios.DoesNotExist:
            return JsonResponse({'error': 'Usuario no encontrado'}, status=404)

        modelo = ModelosIa.objects.create(
            nombre=nombre,
            version=version,
            proveedor_id=proveedor_id,
            descripcion=descripcion,
            activo=True,
            recomendado=False,
            fecha_creacion=timezone.now(),
            color_ia=color_ia,
            id_usuario=usuario
        )

        ConfiguracionOpenai.objects.create(
            id_modelo_ia=modelo,
            id_prompt_id=1,
            endpoint_url=request.POST.get("endpoint_url", ""),
            api_key=request.POST.get("api_key", ""),
            model_name=request.POST.get("model_name", ""),
            max_tokens=request.POST.get("max_tokens"),
            temperature=request.POST.get("temperature"),
            activo=True,
            fecha_creacion=timezone.now(),
            fecha_modificacion=timezone.now()
        )

        return JsonResponse({
            "mensaje": "Modelo OpenAI creado exitosamente",
            "id": modelo.id,
            "nombre": modelo.nombre
        }, status=201)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@require_http_methods(["PUT", "POST"])
def editar_modelo_claude(request, id_modelo):
    """Editar modelo IA + configuración Claude"""
    payload = validar_token(request)

    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    if 'error' in payload:
        return JsonResponse(payload, status=401)

    try:
        # Buscar modelo y configuración
        try:
            modelo = ModelosIa.objects.get(id=id_modelo, proveedor_id=1)
            config = ConfiguracionClaude.objects.get(id_modelo_ia=modelo)
        except ModelosIa.DoesNotExist:
            return JsonResponse({"error": "Modelo Claude no encontrado"}, status=404)
        except ConfiguracionClaude.DoesNotExist:
            return JsonResponse({"error": "Configuración no encontrada"}, status=404)

        # Obtener datos según el método
        if request.method == "PUT":
            data = QueryDict(request.body)
        else:  # POST
            data = request.POST

        # Obtener nombre para validar duplicados
        nombre = data.get("nombre")
        
        if nombre:
            # Verificar duplicados (excluyendo el actual)
            if ModelosIa.objects.filter(nombre=nombre).exclude(id=id_modelo).exists():
                return JsonResponse({'error': f'El modelo "{nombre}" ya existe'}, status=400)
            modelo.nombre = nombre

        # Actualizar modelo
        if data.get("version"):
            modelo.version = data.get("version")
        if data.get("descripcion"):
            modelo.descripcion = data.get("descripcion")
        if data.get("color_ia"):
            modelo.color_ia = data.get("color_ia")
        
        modelo.save()

        # Actualizar configuración
        if data.get("endpoint_url"):
            config.endpoint_url = data.get("endpoint_url")
        if data.get("api_key"):
            config.api_key = data.get("api_key")
        if data.get("model_name"):
            config.model_name = data.get("model_name")
        if data.get("max_tokens"):
            config.max_tokens = data.get("max_tokens")
        if data.get("anthropic_version"):
            config.anthropic_version = data.get("anthropic_version")
        
        config.fecha_modificacion = timezone.now()
        config.save()

        return JsonResponse({
            "mensaje": "Modelo Claude actualizado exitosamente",
            "id": modelo.id,
            "nombre": modelo.nombre
        }, status=200)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["PUT", "POST"])
def editar_modelo_deepseek(request, id_modelo):
    """Editar modelo IA + configuración DeepSeek"""
    payload = validar_token(request)

    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    if 'error' in payload:
        return JsonResponse(payload, status=401)

    try:
        try:
            modelo = ModelosIa.objects.get(id=id_modelo, proveedor_id=2)
            config = ConfiguracionDeepseek.objects.get(id_modelo_ia=modelo)
        except ModelosIa.DoesNotExist:
            return JsonResponse({"error": "Modelo DeepSeek no encontrado"}, status=404)
        except ConfiguracionDeepseek.DoesNotExist:
            return JsonResponse({"error": "Configuración no encontrada"}, status=404)

        if request.method == "PUT":
            data = QueryDict(request.body)
        else:
            data = request.POST

        nombre = data.get("nombre")
        
        if nombre:
            if ModelosIa.objects.filter(nombre=nombre).exclude(id=id_modelo).exists():
                return JsonResponse({'error': f'El modelo "{nombre}" ya existe'}, status=400)
            modelo.nombre = nombre

        if data.get("version"):
            modelo.version = data.get("version")
        if data.get("descripcion"):
            modelo.descripcion = data.get("descripcion")
        if data.get("color_ia"):
            modelo.color_ia = data.get("color_ia")
        
        modelo.save()

        if data.get("endpoint_url"):
            config.endpoint_url = data.get("endpoint_url")
        if data.get("api_key"):
            config.api_key = data.get("api_key")
        if data.get("model_name"):
            config.model_name = data.get("model_name")
        if data.get("max_tokens"):
            config.max_tokens = data.get("max_tokens")
        if data.get("temperature"):
            config.temperature = data.get("temperature")
        
        config.fecha_modificacion = timezone.now()
        config.save()

        return JsonResponse({
            "mensaje": "Modelo DeepSeek actualizado exitosamente",
            "id": modelo.id,
            "nombre": modelo.nombre
        }, status=200)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["PUT", "POST"])
def editar_modelo_gemini(request, id_modelo):
    """Editar modelo IA + configuración Gemini"""
    payload = validar_token(request)

    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    if 'error' in payload:
        return JsonResponse(payload, status=401)

    try:
        try:
            modelo = ModelosIa.objects.get(id=id_modelo, proveedor_id=3)
            config = ConfiguracionGemini.objects.get(id_modelo_ia=modelo)
        except ModelosIa.DoesNotExist:
            return JsonResponse({"error": "Modelo Gemini no encontrado"}, status=404)
        except ConfiguracionGemini.DoesNotExist:
            return JsonResponse({"error": "Configuración no encontrada"}, status=404)

        if request.method == "PUT":
            data = QueryDict(request.body)
        else:
            data = request.POST

        nombre = data.get("nombre")
        
        if nombre:
            if ModelosIa.objects.filter(nombre=nombre).exclude(id=id_modelo).exists():
                return JsonResponse({'error': f'El modelo "{nombre}" ya existe'}, status=400)
            modelo.nombre = nombre

        if data.get("version"):
            modelo.version = data.get("version")
        if data.get("descripcion"):
            modelo.descripcion = data.get("descripcion")
        if data.get("color_ia"):
            modelo.color_ia = data.get("color_ia")
        
        modelo.save()

        if data.get("endpoint_url"):
            config.endpoint_url = data.get("endpoint_url")
        if data.get("api_key"):
            config.api_key = data.get("api_key")
        if data.get("model_name"):
            config.model_name = data.get("model_name")
        if data.get("max_tokens"):
            config.max_tokens = data.get("max_tokens")
        if data.get("temperature"):
            config.temperature = data.get("temperature")
        
        config.fecha_modificacion = timezone.now()
        config.save()

        return JsonResponse({
            "mensaje": "Modelo Gemini actualizado exitosamente",
            "id": modelo.id,
            "nombre": modelo.nombre
        }, status=200)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["PUT", "POST"])
def editar_modelo_openai(request, id_modelo):
    """Editar modelo IA + configuración OpenAI"""
    payload = validar_token(request)

    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    if 'error' in payload:
        return JsonResponse(payload, status=401)

    try:
        try:
            modelo = ModelosIa.objects.get(id=id_modelo, proveedor_id=4)
            config = ConfiguracionOpenai.objects.get(id_modelo_ia=modelo)
        except ModelosIa.DoesNotExist:
            return JsonResponse({"error": "Modelo OpenAI no encontrado"}, status=404)
        except ConfiguracionOpenai.DoesNotExist:
            return JsonResponse({"error": "Configuración no encontrada"}, status=404)

        if request.method == "PUT":
            data = QueryDict(request.body)
        else:
            data = request.POST

        nombre = data.get("nombre")
        
        if nombre:
            if ModelosIa.objects.filter(nombre=nombre).exclude(id=id_modelo).exists():
                return JsonResponse({'error': f'El modelo "{nombre}" ya existe'}, status=400)
            modelo.nombre = nombre

        if data.get("version"):
            modelo.version = data.get("version")
        if data.get("descripcion"):
            modelo.descripcion = data.get("descripcion")
        if data.get("color_ia"):
            modelo.color_ia = data.get("color_ia")
        
        modelo.save()

        if data.get("endpoint_url"):
            config.endpoint_url = data.get("endpoint_url")
        if data.get("api_key"):
            config.api_key = data.get("api_key")
        if data.get("model_name"):
            config.model_name = data.get("model_name")
        if data.get("max_tokens"):
            config.max_tokens = data.get("max_tokens")
        if data.get("temperature"):
            config.temperature = data.get("temperature")
        
        config.fecha_modificacion = timezone.now()
        config.save()

        return JsonResponse({
            "mensaje": "Modelo OpenAI actualizado exitosamente",
            "id": modelo.id,
            "nombre": modelo.nombre
        }, status=200)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@require_http_methods(["GET"])
def listar_modelos_usuario(request):
    """Listar modelos IA creados solo por admins"""
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

        # Obtener solo modelos creados por admins
        modelos = ModelosIa.objects.filter(
            id_usuario_id__in=usuarios_admin_ids
        ).order_by('proveedor_id', '-fecha_creacion')

        data = []
        for m in modelos:
            data.append({
                "id": m.id,
                "nombre": m.nombre,
                "version": m.version,
                "descripcion": m.descripcion,
                "proveedor_id": m.proveedor_id,
                "color_ia": m.color_ia,
                "recomendado": m.recomendado,
                "activo": m.activo,
                "fecha_creacion": m.fecha_creacion,
            })

        return JsonResponse({"modelos": data}, status=200)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@require_http_methods(["PUT", "POST"])
def cambiar_estado_modelo(request, id_modelo):
    """Activar o desactivar un modelo IA"""
    payload = validar_token(request)

    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    if 'error' in payload:
        return JsonResponse(payload, status=401)

    try:
        try:
            modelo = ModelosIa.objects.get(id=id_modelo)
        except ModelosIa.DoesNotExist:
            return JsonResponse({"error": "Modelo no encontrado"}, status=404)

        # Cambiar estado (toggle)
        modelo.activo = not modelo.activo
        modelo.save()

        estado_texto = "activado" if modelo.activo else "desactivado"

        return JsonResponse({
            "mensaje": f"Modelo {estado_texto} exitosamente",
            "id": modelo.id,
            "nombre": modelo.nombre,
            "activo": modelo.activo
        }, status=200)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@require_http_methods(["PUT", "POST"])
def marcar_recomendado(request, id_modelo):
    """Marcar un modelo como recomendado (solo uno por usuario)"""
    payload = validar_token(request)

    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    if 'error' in payload:
        return JsonResponse(payload, status=401)

    try:
        try:
            modelo = ModelosIa.objects.get(id=id_modelo)
        except ModelosIa.DoesNotExist:
            return JsonResponse({"error": "Modelo no encontrado"}, status=404)

        # Quitar recomendado a todos los modelos del usuario
        ModelosIa.objects.filter(id_usuario=modelo.id_usuario).update(recomendado=False)

        # Activar recomendado en este
        modelo.recomendado = True
        modelo.save()

        return JsonResponse({
            "mensaje": "Modelo marcado como recomendado exitosamente",
            "id": modelo.id,
            "nombre": modelo.nombre,
            "recomendado": modelo.recomendado
        }, status=200)

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    
@require_http_methods(["GET"])
def listar_comparaciones(request):
    """Listar TODAS las comparaciones individuales de todos los usuarios"""
    payload = validar_token(request)

    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    if 'error' in payload:
        return JsonResponse(payload, status=401)

    try:
        # Verificar que el usuario es admin (opcional pero recomendado)
        try:
            usuario = Usuarios.objects.select_related('rol').get(id=payload['usuario_id'])
            if usuario.rol.nombre.lower() != 'admin':
                return JsonResponse({
                    'error': 'No tienes permisos para ver todas las comparaciones'
                }, status=403)
        except Usuarios.DoesNotExist:
            return JsonResponse({'error': 'Usuario no encontrado'}, status=404)
        
        # Obtener TODAS las comparaciones de TODOS los usuarios
        comparaciones = ComparacionesIndividuales.objects.select_related(
            'usuario__datos_personales',
            'lenguaje',
            'id_modelo_ia'
        ).order_by('-fecha_creacion')

        print(f"🔍 DEBUG: Total de comparaciones en el sistema: {comparaciones.count()}")

        data = []
        for comp in comparaciones:
            # Concatenar nombres y apellidos
            nombre_completo = f"{comp.usuario.datos_personales.nombres} {comp.usuario.datos_personales.apellidos}"
            
            data.append({
                "id": comp.id,
                "nombre_comparacion": comp.nombre_comparacion,
                "nombre_usuario": nombre_completo,
                "usuario_id": comp.usuario.id,  # Agregar el ID del usuario
                "estado": comp.estado,
                "lenguaje": comp.lenguaje.nombre if comp.lenguaje else None,
                "modelo_ia": comp.id_modelo_ia.nombre if comp.id_modelo_ia else None,
                "fecha_creacion": comp.fecha_creacion,
            })

        print(f"🔍 DEBUG: Datos a enviar: {len(data)} comparaciones")

        return JsonResponse({"comparaciones": data}, status=200)

    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@require_http_methods(["PUT", "POST"])
def cambiar_estado_comparacion(request, id_comparacion):
    """Cambiar estado de comparación entre 'Reciente' y 'Oculto' (ADMIN puede cambiar cualquier comparación)"""
    payload = validar_token(request)

    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    if 'error' in payload:
        return JsonResponse(payload, status=401)

    try:
        # Verificar que el usuario es admin
        try:
            usuario = Usuarios.objects.select_related('rol').get(id=payload['usuario_id'])
            if usuario.rol.nombre.lower() != 'admin':
                return JsonResponse({
                    'error': 'No tienes permisos para modificar comparaciones'
                }, status=403)
        except Usuarios.DoesNotExist:
            return JsonResponse({'error': 'Usuario no encontrado'}, status=404)
        
        # Admin puede cambiar el estado de cualquier comparación
        try:
            comparacion = ComparacionesIndividuales.objects.get(id=id_comparacion)
        except ComparacionesIndividuales.DoesNotExist:
            return JsonResponse({
                "error": "Comparación no encontrada"
            }, status=404)

        print(f"🔍 DEBUG: Comparación {comparacion.id} - Estado actual: {comparacion.estado}")

        # Cambiar estado entre 'Reciente' y 'Oculto'
        if comparacion.estado == 'Reciente':
            comparacion.estado = 'Oculto'
        else:
            comparacion.estado = 'Reciente'
        
        comparacion.save()

        print(f"✅ DEBUG: Nuevo estado: {comparacion.estado}")

        return JsonResponse({
            "mensaje": f"Estado cambiado a '{comparacion.estado}' exitosamente",
            "id": comparacion.id,
            "nombre_comparacion": comparacion.nombre_comparacion,
            "estado": comparacion.estado
        }, status=200)

    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return JsonResponse({"error": str(e)}, status=500)