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