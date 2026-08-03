from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.hashers import make_password, check_password
from django.db import transaction
from datetime import datetime, timedelta
import jwt,json,base64,os
from django.conf import settings
from usuarios.models import ComentariosCodigoGrupal, ComentariosIaGrupal,ComparacionesPareadas
from usuarios.models import *
from usuarios.models import ComparacionesGrupales, ComparacionesIndividuales, Lenguajes, ModelosIa, ProveedoresIa
from usuarios.credenciales import clave_api, CredencialAusente
from django.utils import timezone
from django.db.models import Q
import requests
import json
import time
import re
import json
from django.core.files.uploadhandler import MemoryFileUploadHandler
from typing import Dict, List

@csrf_exempt
@require_http_methods(["POST"])
def registrar_usuario(request):
    try:
        # Obtener datos del FormData
        usuario = request.POST.get('usuario')
        contraseña = request.POST.get('contraseña')
        nombre = request.POST.get('nombre')
        apellido = request.POST.get('apellido')
        
        # Validar datos requeridos (sin rol_id)
        required_fields = {
            'usuario': usuario,
            'contraseña': contraseña,
            'nombre': nombre,
            'apellido': apellido
        }
        
        for field_name, field_value in required_fields.items():
            if not field_value:
                return JsonResponse({'error': f'Campo requerido: {field_name}'}, status=400)
        
        # Verificar si el usuario ya existe
        if Usuarios.objects.filter(usuario=usuario).exists():
            return JsonResponse({'error': 'El usuario ya existe'}, status=400)
        
        # Asignar rol de usuario por defecto (ID = 2)
        try:
            rol = Roles.objects.get(id=2)  # Rol de "usuario"
        except Roles.DoesNotExist:
            return JsonResponse({'error': 'Error del sistema: rol de usuario no encontrado'}, status=500)
        
        # TRANSACCIÓN: Todo o nada
        with transaction.atomic():
            # Crear datos personales
            datos_personales = DatosPersonales.objects.create(
                nombre=nombre,
                apellido=apellido
            )
            
            # Encriptar contraseña y crear usuario
            contraseña_encriptada = make_password(contraseña)
            usuario_obj = Usuarios.objects.create(
                usuario=usuario,
                contrasenia=contraseña_encriptada,
                datos_personales=datos_personales,
                rol=rol,
                activo=True
            )
        
        return JsonResponse({
            'mensaje': 'Usuario registrado exitosamente',
            'usuario_id': usuario_obj.id,
            'usuario': usuario_obj.usuario
        }, status=201)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
@csrf_exempt
@require_http_methods(["POST"])
def login_usuario(request):
    try:
        # Obtener datos del FormData
        usuario = request.POST.get('usuario')
        contraseña = request.POST.get('contraseña')
        
        # Validar datos requeridos
        if not usuario or not contraseña:
            return JsonResponse({'error': 'Usuario y contraseña requeridos'}, status=400)
        
        # Buscar usuario
        try:
            usuario_obj = Usuarios.objects.select_related('datos_personales', 'rol').get(
                usuario=usuario, 
                activo=True
            )
        except Usuarios.DoesNotExist:
            return JsonResponse({'error': 'Credenciales inválidas'}, status=401)
        
        # Verificar contraseña
        if check_password(contraseña, usuario_obj.contrasenia):
            # Generar JWT token
            payload = {
                'usuario_id': usuario_obj.id,
                'usuario': usuario_obj.usuario,
                'rol': usuario_obj.rol.nombre,
                'exp': datetime.utcnow() + timedelta(hours=24),  # Expira en 24 horas
                'iat': datetime.utcnow()  # Fecha de emisión
            }
            
            # Crear token (usa SECRET_KEY de Django por seguridad)
            token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
            
            return JsonResponse({
                'mensaje': 'Login exitoso',
                'token': token,
            }, status=200)
        else:
            return JsonResponse({'error': 'Credenciales inválidas'}, status=401)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    

# Función auxiliar para validar JWT, es decir ya no es necesario validar el token en cada llamado a la API
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
    


@require_http_methods(["GET"])
def perfil_usuario(request):
    """Endpoint protegido que requiere JWT"""
    payload = validar_token(request)
    
    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    
    if 'error' in payload:
        return JsonResponse(payload, status=401)
    
    try:
        usuario = Usuarios.objects.select_related('datos_personales', 'rol').get(
            id=payload['usuario_id'],
            activo=True
        )
        
        return JsonResponse({
            'usuario_id': usuario.id,
            'usuario': usuario.usuario,
            'nombres': usuario.datos_personales.nombres,  # Cambiado de .nombre a .nombres
            'apellidos': usuario.datos_personales.apellidos,  # Cambiado de .apellido a .apellidos
            'email': usuario.datos_personales.email,
            'telefono': usuario.datos_personales.telefono,
            'institucion': usuario.datos_personales.institucion,
            'facultad_area': usuario.datos_personales.facultad_area,
            'rol': usuario.rol.nombre
        }, status=200)
        
    except Usuarios.DoesNotExist:
        return JsonResponse({'error': 'Usuario no encontrado'}, status=404)

@require_http_methods(["GET"])
def listar_comparaciones_individuales(request, usuario_id):
    """Listar comparaciones individuales de un usuario específico"""
    payload = validar_token(request)
    
    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    
    if 'error' in payload:
        return JsonResponse(payload, status=401)
    
    try:
        # Obtener todas las comparaciones individuales del usuario
        comparaciones = ComparacionesIndividuales.objects.filter(
            usuario_id=usuario_id  # Ahora usa el parámetro de la URL
        ).values('id', 'nombre_comparacion', 'fecha_creacion', 'estado').order_by('-fecha_creacion')
        
        return JsonResponse({
            'comparaciones': list(comparaciones)
        }, status=200)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def listar_comparaciones_grupales(request, usuario_id):
    """Listar comparaciones grupales de un usuario específico"""
    payload = validar_token(request)
    
    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    
    if 'error' in payload:
        return JsonResponse(payload, status=401)
    
    try:
        # Obtener todas las comparaciones grupales del usuario
        comparaciones = ComparacionesGrupales.objects.filter(
            usuario_id=usuario_id  # Ahora usa el parámetro de la URL
        ).values('id', 'nombre_comparacion', 'fecha_creacion','estado').order_by('-fecha_creacion')
        
        return JsonResponse({
            'comparaciones': list(comparaciones)
        }, status=200)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def crear_comparacion_grupal(request):
    """Crear una nueva comparación grupal con múltiples códigos"""
    payload = validar_token(request)
    
    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    
    if 'error' in payload:
        return JsonResponse(payload, status=401)
    
    try:
        from django.db import transaction
        
        # Obtener datos básicos con los nombres correctos
        id_usuario = request.POST.get('id_usuario')
        id_modelo_ia = request.POST.get('id_modelo_ia')
        id_lenguaje = request.POST.get('id_lenguaje')
        nombre_comparacion = request.POST.get('nombre_comparacion')
        estado = request.POST.get('estado', 'Reciente')
        
        # Validaciones básicas
        if not all([id_usuario, id_modelo_ia, id_lenguaje]):
            return JsonResponse({
                'error': 'Faltan campos requeridos: id_usuario, id_modelo_ia, id_lenguaje'
            }, status=400)
        
        # Validar registros relacionados
        if not Usuarios.objects.filter(pk=id_usuario).exists():
            return JsonResponse({'error': f'Usuario con id {id_usuario} no existe'}, status=400)
        
        if not ModelosIa.objects.filter(pk=id_modelo_ia).exists():
            return JsonResponse({'error': f'Modelo IA con id {id_modelo_ia} no existe'}, status=400)
        
        try:
            lenguaje = Lenguajes.objects.get(pk=id_lenguaje)
            extension_esperada = lenguaje.extension
        except Lenguajes.DoesNotExist:
            return JsonResponse({'error': f'Lenguaje con id {id_lenguaje} no existe'}, status=400)
        
        # Función para validar y extraer código
        def obtener_codigo(nombre_campo, campo_texto, campo_archivo, extension_esperada):
            codigo = request.POST.get(campo_texto)
            archivo = request.FILES.get(campo_archivo)
            
            if archivo:
                _, extension_archivo = os.path.splitext(archivo.name)
                extension_archivo = extension_archivo.lower()
                
                if extension_esperada:
                    extension_esperada_con_punto = extension_esperada if extension_esperada.startswith('.') else f'.{extension_esperada}'
                    
                    if extension_archivo != extension_esperada_con_punto.lower():
                        raise ValueError(
                            f'El archivo {nombre_campo} debe tener extensión '
                            f'{extension_esperada_con_punto}, pero tiene {extension_archivo}'
                        )
                
                try:
                    contenido = archivo.read().decode('utf-8')
                    return contenido, archivo.name
                except UnicodeDecodeError:
                    raise ValueError(f'El archivo {nombre_campo} no está en formato UTF-8 válido')
            
            elif codigo:
                return codigo, None
            
            return None, None
        
        # Recolectar códigos dinámicamente (codigo_1, codigo_2, codigo_3, ...)
        codigos_data = []
        orden = 1
        
        while True:
            codigo, nombre_archivo = obtener_codigo(
                f'codigo_{orden}',
                f'codigo_{orden}',
                f'archivo_{orden}',
                extension_esperada
            )
            
            if not codigo:
                break
            
            # Permitir nombre de archivo personalizado
            nombre_archivo_custom = request.POST.get(f'nombre_archivo_{orden}')
            
            codigos_data.append({
                'codigo': codigo,
                'nombre_archivo': nombre_archivo_custom or nombre_archivo or f'codigo_{orden}',
                'orden': orden
            })
            
            orden += 1
        
        # Validar mínimo 3 códigos
        if len(codigos_data) < 3:
            return JsonResponse({
                'error': 'Debes proporcionar al menos 3 códigos para comparar'
            }, status=400)
        
        # Crear comparación y códigos en una transacción
        with transaction.atomic():
            # Crear comparación grupal
            comparacion = ComparacionesGrupales.objects.create(
                usuario_id=id_usuario,
                lenguaje_id=id_lenguaje,
                id_modelo_ia_id=id_modelo_ia,
                nombre_comparacion=nombre_comparacion,
                estado=estado,
                fecha_creacion=timezone.now()
            )
            
            # Crear códigos fuente asociados
            codigos_creados = []
            for codigo_data in codigos_data:
                codigo_fuente = CodigosFuente.objects.create(
                    comparacion_grupal_id=comparacion.pk,
                    codigo=codigo_data['codigo'],
                    nombre_archivo=codigo_data['nombre_archivo'],
                    orden=codigo_data['orden']
                )
                codigos_creados.append({
                    'id': codigo_fuente.pk,
                    'nombre_archivo': codigo_fuente.nombre_archivo,
                    'orden': codigo_fuente.orden
                })
        
        return JsonResponse({
            'mensaje': 'Comparación grupal creada exitosamente',
            'id': comparacion.pk,
            'nombre_comparacion': comparacion.nombre_comparacion,
            'fecha_creacion': comparacion.fecha_creacion.isoformat(),
            'lenguaje': lenguaje.nombre,
            'total_codigos': len(codigos_creados),
            'codigos': codigos_creados
        }, status=201)
        
    except ValueError as ve:
        return JsonResponse({'error': str(ve)}, status=400)
    except Exception as e:
        import traceback
        return JsonResponse({
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def crear_comparacion_individual(request):
    """Crear una nueva comparación individual"""
    payload = validar_token(request)
    
    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    
    if 'error' in payload:
        return JsonResponse(payload, status=401)
    
    try:
        # Obtener datos del FormData
        usuario_id = request.POST.get('usuario_id')
        modelo_ia_id = request.POST.get('modelo_ia_id')
        lenguaje_id = request.POST.get('lenguaje_id')
        nombre_comparacion = request.POST.get('nombre_comparacion')
        estado = request.POST.get('estado', 'Reciente')
        
        # Validaciones básicas
        if not all([usuario_id, modelo_ia_id, lenguaje_id]):
            return JsonResponse({
                'error': 'Faltan campos requeridos: usuario_id, modelo_ia_id, lenguaje_id'
            }, status=400)
        
        # Validar que existan los registros relacionados
        if not Usuarios.objects.filter(pk=usuario_id).exists():
            return JsonResponse({
                'error': f'Usuario con id {usuario_id} no existe'
            }, status=400)
        
        if not ModelosIa.objects.filter(pk=modelo_ia_id).exists():
            return JsonResponse({
                'error': f'Modelo IA con id {modelo_ia_id} no existe'
            }, status=400)
        
        try:
            lenguaje = Lenguajes.objects.get(pk=lenguaje_id)
            extension_esperada = lenguaje.extension
        except Lenguajes.DoesNotExist:
            return JsonResponse({
                'error': f'Lenguaje con id {lenguaje_id} no existe'
            }, status=400)
        
        # Función para validar y extraer código
        def obtener_codigo(nombre_campo, campo_texto, campo_archivo, extension_esperada):
            codigo = request.POST.get(campo_texto)
            archivo = request.FILES.get(campo_archivo)
            
            if archivo:
                _, extension_archivo = os.path.splitext(archivo.name)
                extension_archivo = extension_archivo.lower()
                
                if extension_esperada:
                    if not extension_esperada.startswith('.'):
                        extension_esperada_con_punto = f'.{extension_esperada}'
                    else:
                        extension_esperada_con_punto = extension_esperada
                    
                    if extension_archivo != extension_esperada_con_punto.lower():
                        raise ValueError(
                            f'El archivo {nombre_campo} debe tener extensión '
                            f'{extension_esperada_con_punto}, pero tiene {extension_archivo}'
                        )
                
                try:
                    contenido = archivo.read().decode('utf-8')
                    return contenido
                except UnicodeDecodeError:
                    raise ValueError(
                        f'El archivo {nombre_campo} no está en formato UTF-8 válido'
                    )
            
            elif codigo:
                return codigo
            
            else:
                return None
        
        # --- CÓDIGO 1 ---
        codigo_1 = obtener_codigo('codigo_1', 'codigo_1', 'archivo_1', extension_esperada)
        
        if not codigo_1:
            return JsonResponse({
                'error': 'Debes proporcionar codigo_1 como texto o archivo_1'
            }, status=400)
        
        # --- CÓDIGO 2 ---
        codigo_2 = obtener_codigo('codigo_2', 'codigo_2', 'archivo_2', extension_esperada)
        
        if not codigo_2:
            return JsonResponse({
                'error': 'Debes proporcionar codigo_2 como texto o archivo_2'
            }, status=400)
        
        # Crear la comparación individual
        # IMPORTANTE: Usa id_modelo_ia_id (con _id al final) porque el campo se llama id_modelo_ia
        comparacion = ComparacionesIndividuales.objects.create(
            usuario_id=usuario_id,
            lenguaje_id=lenguaje_id,
            id_modelo_ia_id=modelo_ia_id,  # ← OJO: id_modelo_ia_id (con _id al final)
            nombre_comparacion=nombre_comparacion,
            codigo_1=codigo_1,
            codigo_2=codigo_2,
            estado=estado,
            fecha_creacion=timezone.now()
        )
        
        return JsonResponse({
            'mensaje': 'Comparación individual creada exitosamente',
            'id': comparacion.pk,
            'nombre_comparacion': comparacion.nombre_comparacion,
            'fecha_creacion': comparacion.fecha_creacion.isoformat(),
            'lenguaje': lenguaje.nombre
        }, status=201)
        
    except ValueError as ve:
        return JsonResponse({'error': str(ve)}, status=400)
    except Exception as e:
        import traceback
        return JsonResponse({
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)

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
        
        # Validaciones
        if not nombre:
            return JsonResponse({
                'error': 'El campo nombre es requerido'
            }, status=400)
        
        # Verificar si ya existe
        if Lenguajes.objects.filter(nombre=nombre).exists():
            return JsonResponse({
                'error': f'El lenguaje "{nombre}" ya existe'
            }, status=400)
        
        # Crear el lenguaje
        lenguaje = Lenguajes.objects.create(
            nombre=nombre,
            extension=extension
        )
        
        return JsonResponse({
            'mensaje': 'Lenguaje creado exitosamente',
            'id': lenguaje.id,
            'nombre': lenguaje.nombre,
            'extension': lenguaje.extension
        }, status=201)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

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
        # Obtener datos del FormData
        nombre = request.POST.get('nombre')
        version = request.POST.get('version')
        proveedor_id = request.POST.get('proveedor_id')
        descripcion = request.POST.get('descripcion')
        endpoint_api = request.POST.get('endpoint_api')
        tipo_autenticacion = request.POST.get('tipo_autenticacion', 'api_key')
        headers_adicionales = request.POST.get('headers_adicionales')
        parametros_default = request.POST.get('parametros_default')
        limite_tokens = request.POST.get('limite_tokens')
        soporta_streaming = request.POST.get('soporta_streaming', 'false')
        activo = request.POST.get('activo', 'true')
        
        # Validaciones
        if not all([nombre, endpoint_api]):
            return JsonResponse({
                'error': 'Faltan campos requeridos: nombre, endpoint_api'
            }, status=400)
        
        # Verificar si ya existe
        if ModelosIa.objects.filter(nombre=nombre).exists():
            return JsonResponse({
                'error': f'El modelo "{nombre}" ya existe'
            }, status=400)
        
        # Convertir campos JSON si vienen como string
        if headers_adicionales:
            try:
                headers_adicionales = json.loads(headers_adicionales)
            except json.JSONDecodeError:
                return JsonResponse({
                    'error': 'headers_adicionales debe ser un JSON válido'
                }, status=400)
        
        if parametros_default:
            try:
                parametros_default = json.loads(parametros_default)
            except json.JSONDecodeError:
                return JsonResponse({
                    'error': 'parametros_default debe ser un JSON válido'
                }, status=400)
        
        # Convertir booleanos
        soporta_streaming = soporta_streaming.lower() in ['true', '1', 'yes']
        activo = activo.lower() in ['true', '1', 'yes']
        
        # Crear el modelo IA
        modelo = ModelosIa.objects.create(
            nombre=nombre,
            version=version,
            proveedor_id=proveedor_id if proveedor_id else None,
            descripcion=descripcion,
            endpoint_api=endpoint_api,
            tipo_autenticacion=tipo_autenticacion,
            headers_adicionales=headers_adicionales,
            parametros_default=parametros_default,
            limite_tokens=int(limite_tokens) if limite_tokens else None,
            soporta_streaming=soporta_streaming,
            activo=activo,
            fecha_creacion=timezone.now()
        )
        
        return JsonResponse({
            'mensaje': 'Modelo de IA creado exitosamente',
            'id': modelo.id,
            'nombre': modelo.nombre,
            'version': modelo.version,
            'endpoint_api': modelo.endpoint_api
        }, status=201)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
@csrf_exempt
@require_http_methods(["POST"])
def crear_proveedor_ia(request):
    """Crear un nuevo proveedor de IA"""
    payload = validar_token(request)
    
    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    
    if 'error' in payload:
        return JsonResponse(payload, status=401)
    
    try:
        # Obtener datos del FormData
        nombre = request.POST.get('nombre')
        descripcion = request.POST.get('descripcion', '')
        logo_url = request.POST.get('logo_url', '')
        sitio_web = request.POST.get('sitio_web', '')
        activo = request.POST.get('activo', 'true').lower() == 'true'
        
        # Validaciones
        if not nombre:
            return JsonResponse({
                'error': 'El campo nombre es requerido'
            }, status=400)
        
        # Verificar si ya existe
        if ProveedoresIa.objects.filter(nombre=nombre).exists():
            return JsonResponse({
                'error': f'El proveedor "{nombre}" ya existe'
            }, status=400)
        
        # Crear el proveedor
        proveedor = ProveedoresIa.objects.create(
            nombre=nombre,
            descripcion=descripcion if descripcion else None,
            logo_url=logo_url if logo_url else None,
            sitio_web=sitio_web if sitio_web else None,
            activo=activo,
            fecha_creacion=timezone.now()
        )
        
        return JsonResponse({
            'mensaje': 'Proveedor de IA creado exitosamente',
            'id': proveedor.id_proveedor,
            'nombre': proveedor.nombre,
            'descripcion': proveedor.descripcion,
            'logo_url': proveedor.logo_url,
            'sitio_web': proveedor.sitio_web,
            'activo': proveedor.activo
        }, status=201)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["PATCH"])
def marcar_individual_reciente(request, comparacion_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'No autorizado'}, status=401)
    
    try:
        comparacion = ComparacionesIndividuales.objects.get(id=comparacion_id)
        if comparacion.usuario_id != (payload.get('usuario_id') or payload.get('user_id')):
            return JsonResponse({'error': 'Sin permisos'}, status=403)
        
        comparacion.estado = 'Reciente'
        comparacion.save()
        return JsonResponse({'mensaje': 'Marcado como Reciente', 'id': comparacion.id}, status=200)
    except ComparacionesIndividuales.DoesNotExist:
        return JsonResponse({'error': 'No encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["PATCH"])
def marcar_individual_destacado(request, comparacion_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'No autorizado'}, status=401)
    
    try:
        comparacion = ComparacionesIndividuales.objects.get(id=comparacion_id)
        if comparacion.usuario_id != (payload.get('usuario_id') or payload.get('user_id')):
            return JsonResponse({'error': 'Sin permisos'}, status=403)
        
        comparacion.estado = 'Destacado'
        comparacion.save()
        return JsonResponse({'mensaje': 'Marcado como Destacado', 'id': comparacion.id}, status=200)
    except ComparacionesIndividuales.DoesNotExist:
        return JsonResponse({'error': 'No encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["PATCH"])
def marcar_individual_oculto(request, comparacion_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'No autorizado'}, status=401)
    
    try:
        comparacion = ComparacionesIndividuales.objects.get(id=comparacion_id)
        if comparacion.usuario_id != (payload.get('usuario_id') or payload.get('user_id')):
            return JsonResponse({'error': 'Sin permisos'}, status=403)
        
        comparacion.estado = 'Oculto'
        comparacion.save()
        return JsonResponse({'mensaje': 'Marcado como Oculto', 'id': comparacion.id}, status=200)
    except ComparacionesIndividuales.DoesNotExist:
        return JsonResponse({'error': 'No encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["PATCH"])
def marcar_grupal_reciente(request, comparacion_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'No autorizado'}, status=401)
    
    try:
        comparacion = ComparacionesGrupales.objects.get(id=comparacion_id)
        if comparacion.usuario_id != (payload.get('usuario_id') or payload.get('user_id')):
            return JsonResponse({'error': 'Sin permisos'}, status=403)
        
        comparacion.estado = 'Reciente'
        comparacion.save()
        return JsonResponse({'mensaje': 'Marcado como Reciente', 'id': comparacion.id}, status=200)
    except ComparacionesGrupales.DoesNotExist:
        return JsonResponse({'error': 'No encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["PATCH"])
def marcar_grupal_destacado(request, comparacion_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'No autorizado'}, status=401)
    
    try:
        comparacion = ComparacionesGrupales.objects.get(id=comparacion_id)
        if comparacion.usuario_id != (payload.get('usuario_id') or payload.get('user_id')):
            return JsonResponse({'error': 'Sin permisos'}, status=403)
        
        comparacion.estado = 'Destacado'
        comparacion.save()
        return JsonResponse({'mensaje': 'Marcado como Destacado', 'id': comparacion.id}, status=200)
    except ComparacionesGrupales.DoesNotExist:
        return JsonResponse({'error': 'No encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["PATCH"])
def marcar_grupal_oculto(request, comparacion_id):
    payload = validar_token(request)
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'No autorizado'}, status=401)
    
    try:
        comparacion = ComparacionesGrupales.objects.get(id=comparacion_id)
        if comparacion.usuario_id != (payload.get('usuario_id') or payload.get('user_id')):
            return JsonResponse({'error': 'Sin permisos'}, status=403)
        
        comparacion.estado = 'Oculto'
        comparacion.save()
        return JsonResponse({'mensaje': 'Marcado como Oculto', 'id': comparacion.id}, status=200)
    except ComparacionesGrupales.DoesNotExist:
        return JsonResponse({'error': 'No encontrada'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    

@require_http_methods(["GET"])
def listar_modelos_admin(request):
    """Listar todos los modelos de IA creados por admin (visibles para todos)"""
    payload = validar_token(request)
    
    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    
    if 'error' in payload:
        return JsonResponse(payload, status=401)
    
    try:
        # Obtener el rol de admin
        rol_admin = Roles.objects.filter(nombre='admin').first()
        
        if not rol_admin:
            return JsonResponse({'error': 'Rol admin no encontrado'}, status=404)
        
        # Obtener todos los usuarios con rol admin
        usuarios_admin = Usuarios.objects.filter(rol=rol_admin).values_list('id', flat=True)
        
        # Filtrar modelos creados por usuarios admin y que estén activos
        modelos = ModelosIa.objects.filter(
            id_usuario__in=usuarios_admin,
            activo=True
        ).select_related('proveedor').values(
            'id',
            'nombre',
            'descripcion',
            'color_ia',
            'imagen_ia',
            'proveedor__nombre'
        ).order_by('-fecha_creacion')
        
        # Convertir imagen binaria a base64 si existe
        modelos_lista = []
        for modelo in modelos:
            modelo_dict = {
                'id_modelo_ia': modelo['id'],
                'nombre': modelo['nombre'],
                'descripcion': modelo['descripcion'],
                'color': modelo['color_ia'],
                'nombre_proveedor': modelo['proveedor__nombre'],
                'imagen': base64.b64encode(modelo['imagen_ia']).decode('utf-8') if modelo['imagen_ia'] else None
            }
            modelos_lista.append(modelo_dict)
        
        return JsonResponse({
            'modelos': modelos_lista
        }, status=200)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def listar_modelos_usuario(request, usuario_id):
    """Listar modelos de IA creados por un usuario específico (solo visibles para él)"""
    payload = validar_token(request)
    
    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    
    if 'error' in payload:
        return JsonResponse(payload, status=401)
    
    try:
        # Verificar que el usuario existe
        usuario = Usuarios.objects.filter(id=usuario_id).first()
        
        if not usuario:
            return JsonResponse({'error': 'Usuario no encontrado'}, status=404)
        
        # Filtrar modelos creados por este usuario específico y que estén activos
        modelos = ModelosIa.objects.filter(
            id_usuario=usuario_id,
            activo=True
        ).select_related('proveedor').values(
            'id',
            'nombre',
            'descripcion',
            'color_ia',
            'imagen_ia',
            'proveedor__nombre'
        ).order_by('-fecha_creacion')
        
        # Convertir imagen binaria a base64 si existe
        modelos_lista = []
        for modelo in modelos:
            modelo_dict = {
                'id_modelo_ia': modelo['id'],
                'nombre': modelo['nombre'],
                'descripcion': modelo['descripcion'],
                'color': modelo['color_ia'],
                'nombre_proveedor': modelo['proveedor__nombre'],
                'imagen': base64.b64encode(modelo['imagen_ia']).decode('utf-8') if modelo['imagen_ia'] else None
            }
            modelos_lista.append(modelo_dict)
        
        return JsonResponse({
            'modelos': modelos_lista
        }, status=200)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
    
@csrf_exempt
@require_http_methods(["GET"])
def obtener_comparacion_individual(request, comparacion_id):
    """Obtener los datos de una comparación individual específica"""
    payload = validar_token(request)
    
    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    
    if 'error' in payload:
        return JsonResponse(payload, status=401)
    
    try:
        # Obtener la comparación con sus relaciones
        comparacion = ComparacionesIndividuales.objects.select_related(
            'usuario',
            'lenguaje',
            'id_modelo_ia'
        ).get(id=comparacion_id)
        
        # Verificar que el usuario autenticado sea el dueño de la comparación
        usuario_id_token = payload.get('usuario_id')
        if comparacion.usuario.id != usuario_id_token:
            return JsonResponse({
                'error': 'No tienes permiso para ver esta comparación'
            }, status=403)
        
        # Construir la respuesta
        response_data = {
            'id': comparacion.id,
            'nombre_comparacion': comparacion.nombre_comparacion,
            'codigo_1': comparacion.codigo_1,
            'codigo_2': comparacion.codigo_2,
            'estado': comparacion.estado,
            'fecha_creacion': comparacion.fecha_creacion,
            'usuario': {
                'id': comparacion.usuario.id,
                'nombre': comparacion.usuario.nombre if hasattr(comparacion.usuario, 'nombre') else None,
                'email': comparacion.usuario.email if hasattr(comparacion.usuario, 'email') else None
            },
            'lenguaje': {
                'id': comparacion.lenguaje.id,
                'nombre': comparacion.lenguaje.nombre if hasattr(comparacion.lenguaje, 'nombre') else None
            },
            'modelo_ia': {
                'id': comparacion.id_modelo_ia.id if comparacion.id_modelo_ia else None,
                'nombre': comparacion.id_modelo_ia.nombre if comparacion.id_modelo_ia and hasattr(comparacion.id_modelo_ia, 'nombre') else None
            } if comparacion.id_modelo_ia else None
        }
        
        return JsonResponse(response_data, status=200)
        
    except ComparacionesIndividuales.DoesNotExist:
        return JsonResponse({
            'error': f'No se encontró la comparación con ID {comparacion_id}'
        }, status=404)
        
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
            'extension'
        ).order_by('nombre')
        
        return JsonResponse({
            'lenguajes': list(lenguajes)
        }, status=200)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    


@csrf_exempt
@require_http_methods(["POST"])
def crear_comparacion_ia(request, id_comparacion):
    try:
        if not id_comparacion:
            return JsonResponse({
                'error': 'Se requiere id_comparacion'
            }, status=400)
        
        try:
            comparacion = ComparacionesIndividuales.objects.get(
                id=id_comparacion
            )
        except ComparacionesIndividuales.DoesNotExist:
            return JsonResponse({
                'error': f'Comparación {id_comparacion} no encontrada'
            }, status=404)
        
        if not comparacion.id_modelo_ia:
            return JsonResponse({
                'error': 'La comparación no tiene un modelo de IA asignado'
            }, status=400)
        
        modelo_ia = comparacion.id_modelo_ia
        
        config = None
        proveedor = None
        prompt_config = None
        
        try:
            config = ConfiguracionClaude.objects.select_related('id_prompt').get(
                id_modelo_ia_id=modelo_ia.id,
                activo=True
            )
            proveedor = 'Claude'
            prompt_config = config.id_prompt
        except ConfiguracionClaude.DoesNotExist:
            pass
        
        if not config:
            try:
                config = ConfiguracionOpenai.objects.select_related('id_prompt').get(
                    id_modelo_ia_id=modelo_ia.id,
                    activo=True
                )
                proveedor = 'OpenAI'
                prompt_config = config.id_prompt
            except ConfiguracionOpenai.DoesNotExist:
                pass
        
        if not config:
            try:
                config = ConfiguracionGemini.objects.select_related('id_prompt').get(
                    id_modelo_ia_id=modelo_ia.id,
                    activo=True
                )
                proveedor = 'Gemini'
                prompt_config = config.id_prompt
            except ConfiguracionGemini.DoesNotExist:
                pass
        
        if not config:
            try:
                config = ConfiguracionDeepseek.objects.select_related('id_prompt').get(
                    id_modelo_ia_id=modelo_ia.id,
                    activo=True
                )
                proveedor = 'DeepSeek'
                prompt_config = config.id_prompt
            except ConfiguracionDeepseek.DoesNotExist:
                pass
        
        if not config or not prompt_config:
            return JsonResponse({
                'error': 'No hay configuración activa para este modelo de IA'
            }, status=404)
        
        if not prompt_config.activo:
            return JsonResponse({
                'error': 'El prompt configurado no está activo'
            }, status=400)
        
        prompt_procesado = prompt_config.template_prompt.replace(
            '{{codigo_a}}', comparacion.codigo_1
        ).replace(
            '{{codigo_b}}', comparacion.codigo_2
        )
        
        headers = {}
        payload = {}

        # La clave la aporta quien despliega el sistema: la registrada en la
        # configuracion del modelo o, en su defecto, la variable de entorno del
        # proveedor. El sistema no distribuye credenciales propias.
        try:
            clave = clave_api(config, proveedor)
        except CredencialAusente as falta_clave:
            return JsonResponse({'error': str(falta_clave)}, status=409)
        
        if proveedor == 'Claude':
            headers = {
                'Content-Type': 'application/json',
                'x-api-key': clave,
                'anthropic-version': config.anthropic_version.strip()
            }
            payload = {
                'model': config.model_name.strip(),
                'max_tokens': config.max_tokens,
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt_procesado
                    }
                ]
            }
            
        elif proveedor == 'OpenAI':
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {clave}'
            }
            payload = {
                'model': config.model_name.strip(),
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt_procesado
                    }
                ],
                'max_tokens': config.max_tokens,
                'temperature': float(config.temperature)
            }
            
        elif proveedor == 'Gemini':
            headers = {
                'Content-Type': 'application/json'
            }
            endpoint_url = f"{config.endpoint_url.strip()}/{config.model_name.strip()}:generateContent?key={clave}"
            payload = {
                'contents': [
                    {
                        'parts': [
                            {
                                'text': prompt_procesado
                            }
                        ]
                    }
                ],
                'generationConfig': {
                    'maxOutputTokens': config.max_tokens,
                    'temperature': float(config.temperature)
                }
            }
            
        elif proveedor == 'DeepSeek':
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {clave}'
            }
            payload = {
                'model': config.model_name.strip(),
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt_procesado
                    }
                ],
                'max_tokens': config.max_tokens,
                'temperature': float(config.temperature)
            }
        
        inicio = time.time()
        
        url = endpoint_url if proveedor == 'Gemini' else config.endpoint_url.strip()
        
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=60
        )
        
        tiempo_respuesta = time.time() - inicio
        
        if response.status_code != 200:
            return JsonResponse({
                'error': f'Error de la API {proveedor}: {response.status_code}',
                'detalle': response.text
            }, status=response.status_code)
        
        response_data = response.json()
        respuesta_ia = None
        tokens_usados = 0
        
        if proveedor == 'Claude':
            respuesta_ia = response_data['content'][0]['text']
            tokens_usados = (
                response_data.get('usage', {}).get('input_tokens', 0) + 
                response_data.get('usage', {}).get('output_tokens', 0)
            )
            
        elif proveedor == 'OpenAI':
            respuesta_ia = response_data['choices'][0]['message']['content']
            tokens_usados = response_data.get('usage', {}).get('total_tokens', 0)
            
        elif proveedor == 'Gemini':
            respuesta_ia = response_data['candidates'][0]['content']['parts'][0]['text']
            tokens_usados = (
                response_data.get('usageMetadata', {}).get('promptTokenCount', 0) +
                response_data.get('usageMetadata', {}).get('candidatesTokenCount', 0)
            )
            
        elif proveedor == 'DeepSeek':
            respuesta_ia = response_data['choices'][0]['message']['content']
            tokens_usados = response_data.get('usage', {}).get('total_tokens', 0)
        
        porcentaje_similitud = None
        patron_similitud = r'SIMILITUD GENERAL:\s*(\d+)'
        match = re.search(patron_similitud, respuesta_ia, re.IGNORECASE)
        
        if match:
            porcentaje_similitud = int(match.group(1))
        else:
            patron_alternativo = r'similitud general[:\s]*(\d+)%?'
            match_alt = re.search(patron_alternativo, respuesta_ia, re.IGNORECASE)
            if match_alt:
                porcentaje_similitud = int(match_alt.group(1))
        
        if porcentaje_similitud is not None:
            ResultadosSimilitudIndividual.objects.filter(
                id_comparacion_individual=comparacion
            ).delete()
            
            resultado = ResultadosSimilitudIndividual.objects.create(
                id_comparacion_individual=comparacion,
                porcentaje_similitud=porcentaje_similitud,
                explicacion=respuesta_ia
            )
            
            mensaje_guardado = 'Resultado guardado exitosamente'
        else:
            mensaje_guardado = 'No se pudo extraer el porcentaje de similitud. Respuesta no guardada.'
        
        return JsonResponse({
            'mensaje': 'Comparación exitosa',
            'guardado': mensaje_guardado,
            'comparacion_id': id_comparacion,
            'modelo_usado': modelo_ia.nombre,
            'proveedor': proveedor,
            'model_name': config.model_name,
            'prompt_usado': {
                'version': prompt_config.version,
                'descripcion': prompt_config.descripcion
            },
            'tiempo_respuesta_segundos': round(tiempo_respuesta, 2),
            'tokens_usados': tokens_usados,
            'porcentaje_similitud': porcentaje_similitud,
            'respuesta_ia': respuesta_ia,
            'codigos_comparados': {
                'codigo_1': comparacion.codigo_1[:100] + '...' if len(comparacion.codigo_1) > 100 else comparacion.codigo_1,
                'codigo_2': comparacion.codigo_2[:100] + '...' if len(comparacion.codigo_2) > 100 else comparacion.codigo_2
            }
        }, status=200)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'JSON inválido en el body'
        }, status=400)
    except requests.Timeout:
        return JsonResponse({
            'error': 'Timeout al llamar a la API de IA'
        }, status=504)
    except requests.RequestException as e:
        return JsonResponse({
            'error': f'Error en la petición HTTP: {str(e)}'
        }, status=500)
    except Exception as e:
        return JsonResponse({
            'error': f'Error interno: {str(e)}'
        }, status=500)
    
@csrf_exempt
@require_http_methods(["GET"])
def obtener_resultados_similitud_individual(request, comparacion_id):
    """Obtener los resultados de similitud de una comparación individual"""
    payload = validar_token(request)
    
    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    
    if 'error' in payload:
        return JsonResponse(payload, status=401)
    
    try:
        # Obtener la comparación individual
        comparacion = ComparacionesIndividuales.objects.select_related(
            'usuario'
        ).get(id=comparacion_id)
        
        # Verificar que el usuario autenticado sea el dueño de la comparación
        usuario_id_token = payload.get('usuario_id')
        if comparacion.usuario.id != usuario_id_token:
            return JsonResponse({
                'error': 'No tienes permiso para ver estos resultados'
            }, status=403)
        
        # Obtener todos los resultados de similitud para esta comparación
        resultados = ResultadosSimilitudIndividual.objects.filter(
            id_comparacion_individual=comparacion_id
        )
        
        # Construir la lista de resultados
        resultados_list = []
        for resultado in resultados:
            resultados_list.append({
                'porcentaje_similitud': resultado.porcentaje_similitud,
                'explicacion': resultado.explicacion
            })
        
        return JsonResponse({
            'resultados': resultados_list
        }, status=200)
        
    except ComparacionesIndividuales.DoesNotExist:
        return JsonResponse({
            'error': f'No se encontró la comparación con ID {comparacion_id}'
        }, status=404)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
@csrf_exempt
@require_http_methods(["POST"])
def crear_lenguaje_docente(request):
    """Crear un nuevo lenguaje - Solo para el docente autenticado"""
    payload = validar_token(request)
    
    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    
    if 'error' in payload:
        return JsonResponse(payload, status=401)
    
    try:
        # Obtener el usuario del token
        usuario_id = payload.get('usuario_id')
        
        if not usuario_id:
            return JsonResponse({
                'error': 'Usuario no identificado en el token'
            }, status=401)
        
        # Obtener datos del request
        nombre = request.POST.get('nombre')
        extension = request.POST.get('extension')
        
        # Validaciones
        if not nombre:
            return JsonResponse({
                'error': 'El campo nombre es requerido'
            }, status=400)
        
        # Obtener IDs de todos los usuarios admin
        usuarios_admin_ids = list(Usuarios.objects.filter(
            rol__nombre__iexact='admin'
        ).values_list('id', flat=True))
        
        # Verificar si ya existe un lenguaje con ese nombre creado por un ADMIN
        # (Los lenguajes de otros docentes NO importan)
        if Lenguajes.objects.filter(nombre=nombre, usuario_id__in=usuarios_admin_ids).exists():
            return JsonResponse({
                'error': f'El lenguaje "{nombre}" ya existe (creado por administrador)'
            }, status=400)
        
        # Verificar si YO (el docente actual) ya tengo un lenguaje con ese nombre
        if Lenguajes.objects.filter(nombre=nombre, usuario_id=usuario_id).exists():
            return JsonResponse({
                'error': f'Ya tienes un lenguaje llamado "{nombre}"'
            }, status=400)
        
        # Obtener el usuario
        try:
            usuario = Usuarios.objects.get(id=usuario_id)
        except Usuarios.DoesNotExist:
            return JsonResponse({
                'error': 'Usuario no encontrado'
            }, status=404)
        
        # Crear el lenguaje
        lenguaje = Lenguajes.objects.create(
            nombre=nombre,
            extension=extension,
            usuario=usuario,
            estado=True  # Por defecto activo
        )
        
        return JsonResponse({
            'mensaje': 'Lenguaje creado exitosamente',
            'lenguaje': {
                'id': lenguaje.id,
                'nombre': lenguaje.nombre,
                'extension': lenguaje.extension,
                'estado': lenguaje.estado
            }
        }, status=201)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def listar_lenguajes_docente(request):
    """Listar SOLO los lenguajes creados por el docente autenticado"""
    payload = validar_token(request)
    
    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    
    if 'error' in payload:
        return JsonResponse(payload, status=401)
    
    try:
        # Obtener el usuario del token
        usuario_id = payload.get('usuario_id')
        
        if not usuario_id:
            return JsonResponse({
                'error': 'Usuario no identificado en el token'
            }, status=401)
        
        # Obtener SOLO los lenguajes creados por este usuario
        lenguajes = Lenguajes.objects.filter(
            usuario_id=usuario_id
        ).values(
            'id', 
            'nombre', 
            'extension',
            'estado'
        ).order_by('nombre')
        
        return JsonResponse({
            'lenguajes': list(lenguajes),
            'total': len(lenguajes)
        }, status=200)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.http.multipartparser import MultiPartParser

@csrf_exempt
@require_http_methods(["PUT"])
def editar_lenguaje_docente(request, lenguaje_id):
    """Editar un lenguaje - Solo si pertenece al docente autenticado"""
    
    payload = validar_token(request)
    
    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    
    if 'error' in payload:
        return JsonResponse(payload, status=401)
    
    try:
        usuario_id = payload.get('usuario_id')
        
        if not usuario_id:
            return JsonResponse({
                'error': 'Usuario no identificado en el token'
            }, status=401)
        
        try:
            lenguaje = Lenguajes.objects.get(id=lenguaje_id, usuario_id=usuario_id)
        except Lenguajes.DoesNotExist:
            return JsonResponse({
                'error': 'Lenguaje no encontrado o no tienes permisos para editarlo'
            }, status=404)
        
        # SOLUCIÓN: Parsear multipart/form-data manualmente
        content_type = request.META.get('CONTENT_TYPE', '')
        
        if 'multipart/form-data' in content_type:
            # Usar MultiPartParser para parsear correctamente
            parser = MultiPartParser(request.META, request, request.upload_handlers)
            post_data, files = parser.parse()
            nombre = post_data.get('nombre')
            extension = post_data.get('extension')
        else:
            # Fallback para otros content-types
            nombre = request.POST.get('nombre')
            extension = request.POST.get('extension')
        
        # Validaciones
        if not nombre:
            return JsonResponse({
                'error': 'El campo nombre es requerido'
            }, status=400)
        
        # Verificar duplicados
        if Lenguajes.objects.filter(nombre=nombre).exclude(id=lenguaje_id).exists():
            return JsonResponse({
                'error': f'El lenguaje "{nombre}" ya existe'
            }, status=400)
        
        # Actualizar
        lenguaje.nombre = nombre
        if extension is not None:
            lenguaje.extension = extension
        lenguaje.save()
        
        return JsonResponse({
            'mensaje': 'Lenguaje actualizado exitosamente',
            'lenguaje': {
                'id': lenguaje.id,
                'nombre': lenguaje.nombre,
                'extension': lenguaje.extension,
                'estado': lenguaje.estado
            }
        }, status=200)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["PUT", "POST"])
def cambiar_estado_lenguaje_docente(request, lenguaje_id):
    """Cambiar el estado de un lenguaje - Solo si pertenece al docente"""
    payload = validar_token(request)
    
    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    
    if 'error' in payload:
        return JsonResponse(payload, status=401)
    
    try:
        # Obtener el usuario del token
        usuario_id = payload.get('usuario_id')
        
        if not usuario_id:
            return JsonResponse({
                'error': 'Usuario no identificado en el token'
            }, status=401)
        
        # Buscar el lenguaje Y verificar que sea del usuario
        try:
            lenguaje = Lenguajes.objects.get(id=lenguaje_id, usuario_id=usuario_id)
        except Lenguajes.DoesNotExist:
            return JsonResponse({
                'error': 'Lenguaje no encontrado o no tienes permisos para modificarlo'
            }, status=404)
        
        # Cambiar el estado (toggle)
        lenguaje.estado = not lenguaje.estado
        lenguaje.save()
        
        estado_texto = "activado" if lenguaje.estado else "desactivado"
        
        return JsonResponse({
            'mensaje': f'Lenguaje {estado_texto} exitosamente',
            'lenguaje': {
                'id': lenguaje.id,
                'nombre': lenguaje.nombre,
                'estado': lenguaje.estado
            }
        }, status=200)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
# Mapeo de lenguajes soportados
LENGUAJES_SOPORTADOS = {
    'python': {'nombre': 'Python', 'extensiones': ['.py']},
    'javascript': {'nombre': 'JavaScript', 'extensiones': ['.js']},
    'java': {'nombre': 'Java', 'extensiones': ['.java']},
    'c': {'nombre': 'C', 'extensiones': ['.c', '.h']},
    'cpp': {'nombre': 'C++', 'extensiones': ['.cpp', '.cc', '.cxx', '.hpp']},
    'c++': {'nombre': 'C++', 'extensiones': ['.cpp', '.cc', '.cxx', '.hpp']},
    'csharp': {'nombre': 'C#', 'extensiones': ['.cs']},
    'c#': {'nombre': 'C#', 'extensiones': ['.cs']},
    'php': {'nombre': 'PHP', 'extensiones': ['.php']},
    'ruby': {'nombre': 'Ruby', 'extensiones': ['.rb']},
    'go': {'nombre': 'Go', 'extensiones': ['.go']},
    'rust': {'nombre': 'Rust', 'extensiones': ['.rs']},
    'swift': {'nombre': 'Swift', 'extensiones': ['.swift']},
    'kotlin': {'nombre': 'Kotlin', 'extensiones': ['.kt']},
    'typescript': {'nombre': 'TypeScript', 'extensiones': ['.ts']},
}

from django.utils import timezone

@csrf_exempt
@require_http_methods(["POST"])
def analizar_big_o_individual(request, comparacion_id):
    """Analizar Big O de una comparación y guardar resultados"""
    payload = validar_token(request)
    
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido'}, status=401)
    
    try:
        comparacion = ComparacionesIndividuales.objects.get(pk=comparacion_id)
        
        lenguaje = comparacion.lenguaje.nombre.lower()
        
        if lenguaje not in LENGUAJES_SOPORTADOS:
            extension = comparacion.lenguaje.extension
            lenguaje_detectado = detectar_lenguaje_por_extension(extension)
            
            if not lenguaje_detectado:
                return JsonResponse({
                    'advertencia': f'Lenguaje "{comparacion.lenguaje.nombre}" no completamente soportado.',
                    'lenguaje_original': comparacion.lenguaje.nombre,
                    'usando_analisis': 'generico'
                }, status=200)
            
            lenguaje = lenguaje_detectado
        
        analisis_1 = analizar_codigo_big_o(comparacion.codigo_1, lenguaje)
        analisis_2 = analizar_codigo_big_o(comparacion.codigo_2, lenguaje)
        
        ganador = determinar_ganador(
            analisis_1['complejidad_temporal'],
            analisis_2['complejidad_temporal']
        )
        
        resultado = {
            'mensaje': 'Análisis Big O completado',
            'codigo_1': analisis_1,
            'codigo_2': analisis_2,
            'ganador': ganador,
            'lenguaje': comparacion.lenguaje.nombre,
            'lenguaje_analizado': LENGUAJES_SOPORTADOS[lenguaje]['nombre']
        }
        
        # Guardar en base de datos
        resultado_bd = ResultadosEficienciaIndividual.objects.create(
            id_comparacion_individual_id=comparacion_id,
            codigo_1_complejidad_temporal=analisis_1['complejidad_temporal'],
            codigo_1_complejidad_espacial=analisis_1['complejidad_espacial'],
            codigo_1_nivel_anidamiento=analisis_1['nivel_anidamiento'],
            codigo_1_patrones_detectados=analisis_1['patrones_detectados'],
            codigo_1_estructuras_datos=analisis_1['estructuras_datos'],
            codigo_1_confianza_analisis=analisis_1['confianza_analisis'],
            codigo_2_complejidad_temporal=analisis_2['complejidad_temporal'],
            codigo_2_complejidad_espacial=analisis_2['complejidad_espacial'],
            codigo_2_nivel_anidamiento=analisis_2['nivel_anidamiento'],
            codigo_2_patrones_detectados=analisis_2['patrones_detectados'],
            codigo_2_estructuras_datos=analisis_2['estructuras_datos'],
            codigo_2_confianza_analisis=analisis_2['confianza_analisis'],
            ganador=ganador,
            lenguaje=comparacion.lenguaje.nombre,
            lenguaje_analizado=LENGUAJES_SOPORTADOS[lenguaje]['nombre'],
            fecha_analisis=timezone.now()
        )
        
        # ← IMPORTANTE: Agregar el ID del resultado a la respuesta
        resultado['resultado_id'] = resultado_bd.id_resultado_eficiencia_individual
        
        return JsonResponse(resultado, status=200)
        
    except ComparacionesIndividuales.DoesNotExist:
        return JsonResponse({'error': 'Comparación no encontrada'}, status=404)
    except Exception as e:
        import traceback
        print("ERROR:", str(e))
        print(traceback.format_exc())
        return JsonResponse({
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)


def detectar_lenguaje_por_extension(extension: str) -> str:
    """Detecta el lenguaje por su extensión"""
    if not extension:
        return None
    
    extension = extension.lower()
    if not extension.startswith('.'):
        extension = f'.{extension}'
    
    for lenguaje, info in LENGUAJES_SOPORTADOS.items():
        if extension in info['extensiones']:
            return lenguaje
    
    return None


def analizar_codigo_big_o(codigo: str, lenguaje: str) -> Dict:
    """Analiza un código y retorna su complejidad Big O"""
    lineas = codigo.split('\n')
    
    # Analizar cada función por separado
    funciones = extraer_funciones(codigo, lineas, lenguaje)
    
    if funciones:
        # Si hay múltiples funciones, tomar la de mayor complejidad
        complejidad_temporal = max(
            [calcular_complejidad_temporal(func['codigo'], func['lineas'], lenguaje) 
             for func in funciones],
            key=lambda x: orden_complejidad(x)
        )
    else:
        # Analizar el código completo
        complejidad_temporal = calcular_complejidad_temporal(codigo, lineas, lenguaje)
    
    complejidad_espacial = calcular_complejidad_espacial(codigo, lineas, lenguaje)
    patrones = detectar_patrones(codigo, lineas, lenguaje)
    nivel_anidamiento = contar_loops_anidados(lineas, lenguaje)
    estructuras = detectar_estructuras_datos(codigo, lenguaje)
    
    return {
        'complejidad_temporal': complejidad_temporal,
        'complejidad_espacial': complejidad_espacial,
        'patrones_detectados': patrones,
        'nivel_anidamiento': nivel_anidamiento,
        'estructuras_datos': estructuras,
        'confianza_analisis': calcular_confianza(codigo, lenguaje)
    }


def extraer_funciones(codigo: str, lineas: List[str], lenguaje: str) -> List[Dict]:
    """Extrae funciones individuales del código para analizarlas por separado"""
    funciones = []
    
    if lenguaje == 'python':
        funcion_actual = None
        indentacion_funcion = None
        
        for i, linea in enumerate(lineas):
            # Detectar inicio de función
            if re.match(r'^\s*def\s+(\w+)\s*\(', linea):
                if funcion_actual:
                    funciones.append(funcion_actual)
                
                espacios = len(linea) - len(linea.lstrip())
                funcion_actual = {
                    'nombre': re.search(r'def\s+(\w+)', linea).group(1),
                    'lineas': [linea],
                    'codigo': linea + '\n',
                    'indentacion': espacios
                }
                indentacion_funcion = espacios
            
            # Agregar líneas a la función actual
            elif funcion_actual:
                espacios = len(linea) - len(linea.lstrip())
                
                # Si la indentación vuelve al nivel de la función o menos, terminar
                if linea.strip() and espacios <= indentacion_funcion and not linea.strip().startswith('#'):
                    funciones.append(funcion_actual)
                    funcion_actual = None
                else:
                    funcion_actual['lineas'].append(linea)
                    funcion_actual['codigo'] += linea + '\n'
        
        # Agregar última función
        if funcion_actual:
            funciones.append(funcion_actual)
    
    return funciones


def orden_complejidad(complejidad: str) -> int:
    """Retorna el orden numérico de una complejidad"""
    orden = {
        'O(1)': 1,
        'O(log n)': 2,
        'O(n)': 3,
        'O(n log n)': 4,
        'O(n^2)': 5,
        'O(n^3)': 6,
        'O(2^n)': 7,
        'O(n!)': 8
    }
    return orden.get(complejidad, 999)


def calcular_confianza(codigo: str, lenguaje: str) -> str:
    """Calcula qué tan confiable es el análisis"""
    if lenguaje in ['python', 'javascript', 'java', 'c', 'cpp', 'c++']:
        return 'Alta'
    elif lenguaje in LENGUAJES_SOPORTADOS:
        return 'Media'
    else:
        return 'Baja - Análisis genérico'


def contar_loops_anidados(lineas: List[str], lenguaje: str) -> int:
    """Cuenta el nivel máximo de loops anidados"""
    max_nivel = 0
    
    patrones_loop = {
        'python': r'^\s*(for\s+.*:|while\s+.*:)',
        'javascript': r'^\s*(for\s*\(|while\s*\()',
        'typescript': r'^\s*(for\s*\(|while\s*\()',
        'java': r'^\s*(for\s*\(|while\s*\()',
        'c': r'^\s*(for\s*\(|while\s*\()',
        'cpp': r'^\s*(for\s*\(|while\s*\()',
        'c++': r'^\s*(for\s*\(|while\s*\()',
    }
    
    patron = patrones_loop.get(lenguaje, patrones_loop.get('python'))
    
    if lenguaje == 'python':
        stack_indentacion = []
        
        for linea in lineas:
            linea_limpia = linea.rstrip()
            if not linea_limpia or linea_limpia.strip().startswith('#'):
                continue
            
            espacios = len(linea) - len(linea.lstrip())
            
            # Detectar loop
            if re.search(patron, linea):
                stack_indentacion.append(espacios)
                nivel_actual = len(stack_indentacion)
                max_nivel = max(max_nivel, nivel_actual)
            else:
                # Salir de loops cuando la indentación disminuye
                while stack_indentacion and espacios <= stack_indentacion[-1]:
                    stack_indentacion.pop()
    else:
        nivel_actual = 0
        for linea in lineas:
            if re.search(patron, linea):
                nivel_actual += 1
                max_nivel = max(max_nivel, nivel_actual)
            
            if '}' in linea:
                nivel_actual = max(0, nivel_actual - 1)
    
    return max_nivel


def detectar_recursion(codigo: str, lineas: List[str], lenguaje: str) -> bool:
    """Detecta llamadas recursivas"""
    patrones_funcion = {
        'python': r'def\s+(\w+)\s*\(',
        'javascript': r'(function\s+(\w+)\s*\(|const\s+(\w+)\s*=.*=>)',
        'java': r'(public|private|protected|static)?\s*\w+\s+(\w+)\s*\(',
        'c': r'\w+\s+(\w+)\s*\([^)]*\)\s*\{',
        'cpp': r'\w+\s+(\w+)\s*\([^)]*\)\s*\{',
        'c++': r'\w+\s+(\w+)\s*\([^)]*\)\s*\{',
    }
    
    patron = patrones_funcion.get(lenguaje, patrones_funcion.get('python'))
    
    funciones = []
    for linea in lineas:
        matches = re.finditer(patron, linea)
        for match in matches:
            for grupo in match.groups():
                if grupo and grupo not in ['public', 'private', 'protected', 'static', 'function', 'const', 'def']:
                    funciones.append(grupo)
    
    for nombre_funcion in funciones:
        for linea in lineas:
            if 'def ' in linea or 'function ' in linea:
                continue
            
            if re.search(rf'\b{nombre_funcion}\s*\(', linea):
                return True
    
    return False


def calcular_complejidad_temporal(codigo: str, lineas: List[str], lenguaje: str) -> str:
    """Calcula Big O temporal"""
    loops = contar_loops_anidados(lineas, lenguaje)
    tiene_recursion = detectar_recursion(codigo, lineas, lenguaje)
    tiene_division_iterativa = detectar_division_iterativa_en_loop(codigo, lineas)
    
    if tiene_recursion:
        if es_recursion_multiple(codigo):
            return "O(2^n)"
        elif es_recursion_dividir_conquistar(codigo):
            return "O(n log n)"
        else:
            return "O(n)"
    
    elif loops >= 3:
        return "O(n^3)"
    elif loops == 2:
        return "O(n^2)"
    elif loops == 1:
        if tiene_division_iterativa:
            return "O(n log n)"
        return "O(n)"
    else:
        return "O(1)"


def detectar_division_iterativa_en_loop(codigo: str, lineas: List[str]) -> bool:
    """Detecta si hay división iterativa DENTRO de un loop"""
    en_loop = False
    
    for linea in lineas:
        if re.search(r'^\s*(for|while)\s+', linea):
            en_loop = True
        
        if en_loop:
            if re.search(r'//=\s*2|/=\s*2', linea):
                return True
            
            if re.search(r'(mid|mitad)\s*=.*//\s*2', linea):
                return True
        
        if en_loop and linea.strip() and not linea.strip().startswith('#'):
            espacios = len(linea) - len(linea.lstrip())
            if espacios == 0:
                en_loop = False
    
    return False


def calcular_complejidad_espacial(codigo: str, lineas: List[str], lenguaje: str) -> str:
    """Calcula Big O espacial"""
    arrays_auxiliares = contar_arrays_auxiliares_significativos(codigo, lineas, lenguaje)
    tiene_recursion = detectar_recursion(codigo, lineas, lenguaje)
    tiene_matriz = detectar_matriz(codigo, lenguaje)
    
    if tiene_matriz:
        return "O(n^2)"
    elif tiene_recursion:
        return "O(n)"
    elif arrays_auxiliares > 0:
        return "O(n)"
    else:
        return "O(1)"


def contar_arrays_auxiliares_significativos(codigo: str, lineas: List[str], lenguaje: str) -> int:
    """Cuenta solo arrays auxiliares que crecen proporcionalmente con la entrada"""
    
    if lenguaje == 'python':
        contador = 0
        
        for linea in lineas:
            if re.search(r'=\s*\[.+\]', linea) and not re.search(r'=\s*\[[^\]]{0,5}\]', linea):
                contador += 1
            
            elif re.search(r'=\s*\[\s*\]', linea):
                nombre_lista = re.search(r'(\w+)\s*=\s*\[\s*\]', linea)
                if nombre_lista:
                    lista = nombre_lista.group(1)
                    if re.search(rf'{lista}\.append\(', codigo):
                        contador += 1
        
        return contador
    
    return 0


def es_recursion_multiple(codigo: str) -> bool:
    """Detecta recursión múltiple"""
    return len(re.findall(r'\w+\([^)]*-\s*\d+\)', codigo)) >= 2


def es_recursion_dividir_conquistar(codigo: str) -> bool:
    """Detecta recursión divide y conquista"""
    patrones = [r'//\s*2', r'/\s*2', r'mid', r'mitad', r'medio', r'pivot']
    return any(re.search(p, codigo, re.IGNORECASE) for p in patrones)


def detectar_matriz(codigo: str, lenguaje: str) -> bool:
    """Detecta matrices 2D"""
    patrones = {
        'python': r'\[\s*\[\s*\]|\[\s*\]\s*\*\s*\d+',
        'javascript': r'new\s+Array\(.*\)\.fill\(\[|\.map\(\s*\(\)\s*=>\s*\[',
        'java': r'new\s+\w+\[.*\]\[.*\]',
        'c': r'\w+\s+\w+\[.*\]\[.*\]',
        'cpp': r'vector<\s*vector<|new\s+\w+\[.*\]\[.*\]',
        'c++': r'vector<\s*vector<|new\s+\w+\[.*\]\[.*\]',
    }
    
    patron = patrones.get(lenguaje, r'\[\s*\[\s*\]')
    return bool(re.search(patron, codigo))


def detectar_patrones(codigo: str, lineas: List[str], lenguaje: str) -> List[Dict]:
    """Detecta patrones algorítmicos"""
    patrones = []
    
    if re.search(r'(binary|binaria|mid|mitad)', codigo, re.IGNORECASE):
        patrones.append({'patron': 'Búsqueda Binaria', 'complejidad': 'O(log n)'})
    
    if re.search(r'(sort|ordenar|sorted|quicksort|mergesort)', codigo, re.IGNORECASE):
        patrones.append({'patron': 'Ordenamiento', 'complejidad': 'O(n log n)'})
    
    if contar_loops_anidados(lineas, lenguaje) >= 2:
        patrones.append({'patron': 'Fuerza Bruta', 'complejidad': 'O(n^2) o superior'})
    
    if re.search(r'(dict|map|hash|set)\s*[\(\{<]', codigo, re.IGNORECASE):
        patrones.append({'patron': 'Hash Table', 'complejidad': 'O(1) búsquedas'})
    
    if re.search(r'(fibonacci|fib)', codigo, re.IGNORECASE):
        patrones.append({'patron': 'Fibonacci', 'complejidad': 'O(2^n) o O(n) con memo'})
    
    if re.search(r'(dynamic|dinamica|memo|dp\[)', codigo, re.IGNORECASE):
        patrones.append({'patron': 'Programación Dinámica', 'complejidad': 'Variable'})
    
    return patrones


def detectar_estructuras_datos(codigo: str, lenguaje: str) -> List[str]:
    """Detecta estructuras de datos"""
    estructuras = []
    
    estructuras_patrones = {
        'Array/Lista': r'\[|list\(|Array|vector<|ArrayList',
        'Diccionario/Map': r'\{.*:.*\}|dict\(|Map|HashMap|map<',
        'Set': r'set\(|Set|HashSet|unordered_set',
        'Queue': r'queue|Queue|deque',
        'Stack': r'stack|Stack',
        'Heap': r'heap|Heap|PriorityQueue',
        'Árbol': r'tree|Tree|node|Node|TreeNode',
        'Grafo': r'graph|Graph|grafo|adjacency'
    }
    
    for estructura, patron in estructuras_patrones.items():
        if re.search(patron, codigo, re.IGNORECASE):
            estructuras.append(estructura)
    
    return list(set(estructuras))


def determinar_ganador(comp1: str, comp2: str) -> str:
    """Determina qué código es más eficiente"""
    orden = {
        'O(1)': 1,
        'O(log n)': 2,
        'O(n)': 3,
        'O(n log n)': 4,
        'O(n^2)': 5,
        'O(n^3)': 6,
        'O(2^n)': 7,
        'O(n!)': 8
    }
    
    v1 = orden.get(comp1, 999)
    v2 = orden.get(comp2, 999)
    
    if v1 < v2:
        return 'codigo_1'
    elif v2 < v1:
        return 'codigo_2'
    else:
        return 'empate'

@csrf_exempt
@require_http_methods(["POST"])
def crear_comentario_eficiencia_individual(request, id_resultado_eficiencia):
    try:
        # 1. Obtener el resultado de eficiencia
        try:
            resultado_eficiencia = ResultadosEficienciaIndividual.objects.select_related(
                'id_comparacion_individual',
                'id_comparacion_individual__lenguaje',
                'id_comparacion_individual__id_modelo_ia'
            ).get(id_resultado_eficiencia_individual=id_resultado_eficiencia)
        except ResultadosEficienciaIndividual.DoesNotExist:
            return JsonResponse({
                'error': f'Resultado de eficiencia {id_resultado_eficiencia} no encontrado'
            }, status=404)
        
        comparacion = resultado_eficiencia.id_comparacion_individual
        
        # 2. Obtener el modelo IA
        if not comparacion.id_modelo_ia:
            return JsonResponse({
                'error': 'La comparación no tiene un modelo de IA asignado'
            }, status=400)
        
        modelo_ia = comparacion.id_modelo_ia
        
        # 3. Obtener la configuración según el tipo de modelo
        config = None
        proveedor = None
        prompt_eficiencia = None
        
        # Intentar obtener configuración de cada proveedor
        try:
            config = ConfiguracionClaude.objects.select_related('id_prompt_eficiencia').get(
                id_modelo_ia_id=modelo_ia.id,
                activo=True
            )
            proveedor = 'Claude'
            prompt_eficiencia = config.id_prompt_eficiencia
        except ConfiguracionClaude.DoesNotExist:
            pass
        
        if not config:
            try:
                config = ConfiguracionOpenai.objects.select_related('id_prompt_eficiencia').get(
                    id_modelo_ia_id=modelo_ia.id,
                    activo=True
                )
                proveedor = 'OpenAI'
                prompt_eficiencia = config.id_prompt_eficiencia
            except ConfiguracionOpenai.DoesNotExist:
                pass
        
        if not config:
            try:
                config = ConfiguracionGemini.objects.select_related('id_prompt_eficiencia').get(
                    id_modelo_ia_id=modelo_ia.id,
                    activo=True
                )
                proveedor = 'Gemini'
                prompt_eficiencia = config.id_prompt_eficiencia
            except ConfiguracionGemini.DoesNotExist:
                pass
        
        if not config:
            try:
                config = ConfiguracionDeepseek.objects.select_related('id_prompt_eficiencia').get(
                    id_modelo_ia_id=modelo_ia.id,
                    activo=True
                )
                proveedor = 'DeepSeek'
                prompt_eficiencia = config.id_prompt_eficiencia
            except ConfiguracionDeepseek.DoesNotExist:
                pass
        
        if not config:
            return JsonResponse({
                'error': 'No hay configuración activa para este modelo de IA'
            }, status=404)
        
        # 4. Verificar que el prompt de eficiencia exista y esté activo
        if not prompt_eficiencia:
            return JsonResponse({
                'error': 'No hay prompt de eficiencia configurado para este modelo'
            }, status=400)
        
        if not prompt_eficiencia.activo:
            return JsonResponse({
                'error': 'El prompt de eficiencia configurado no está activo'
            }, status=400)
        
        # 5. Reemplazar placeholders en el prompt con los datos de la comparación y análisis
        prompt_procesado = prompt_eficiencia.template_prompt.format(
            lenguaje=comparacion.lenguaje.nombre if comparacion.lenguaje else 'No especificado',
            codigo_1=comparacion.codigo_1,
            codigo_2=comparacion.codigo_2,
            codigo_1_complejidad_temporal=resultado_eficiencia.codigo_1_complejidad_temporal,
            codigo_1_complejidad_espacial=resultado_eficiencia.codigo_1_complejidad_espacial,
            codigo_1_nivel_anidamiento=resultado_eficiencia.codigo_1_nivel_anidamiento or 0,
            codigo_1_patrones_detectados=json.dumps(resultado_eficiencia.codigo_1_patrones_detectados or {}, indent=2),
            codigo_1_estructuras_datos=json.dumps(resultado_eficiencia.codigo_1_estructuras_datos or {}, indent=2),
            codigo_1_confianza_analisis=resultado_eficiencia.codigo_1_confianza_analisis or 'No especificada',
            codigo_2_complejidad_temporal=resultado_eficiencia.codigo_2_complejidad_temporal,
            codigo_2_complejidad_espacial=resultado_eficiencia.codigo_2_complejidad_espacial,
            codigo_2_nivel_anidamiento=resultado_eficiencia.codigo_2_nivel_anidamiento or 0,
            codigo_2_patrones_detectados=json.dumps(resultado_eficiencia.codigo_2_patrones_detectados or {}, indent=2),
            codigo_2_estructuras_datos=json.dumps(resultado_eficiencia.codigo_2_estructuras_datos or {}, indent=2),
            codigo_2_confianza_analisis=resultado_eficiencia.codigo_2_confianza_analisis or 'No especificada'
        )
        
        # 6. Preparar headers y payload según el proveedor
        headers = {}
        payload = {}

        # La clave la aporta quien despliega el sistema: la registrada en la
        # configuracion del modelo o, en su defecto, la variable de entorno del
        # proveedor. El sistema no distribuye credenciales propias.
        try:
            clave = clave_api(config, proveedor)
        except CredencialAusente as falta_clave:
            return JsonResponse({'error': str(falta_clave)}, status=409)
        
        if proveedor == 'Claude':
            headers = {
                'Content-Type': 'application/json',
                'x-api-key': clave,
                'anthropic-version': config.anthropic_version.strip()
            }
            payload = {
                'model': config.model_name.strip(),
                'max_tokens': config.max_tokens,
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt_procesado
                    }
                ]
            }
            
        elif proveedor == 'OpenAI':
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {clave}'
            }
            payload = {
                'model': config.model_name,
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt_procesado
                    }
                ],
                'max_tokens': config.max_tokens,
                'temperature': float(config.temperature)
            }
            
        elif proveedor == 'Gemini':
            headers = {
                'Content-Type': 'application/json'
            }
            # Gemini usa la API key en la URL
            endpoint_url = f"{config.endpoint_url}/{config.model_name}:generateContent?key={clave}"
            payload = {
                'contents': [
                    {
                        'parts': [
                            {
                                'text': prompt_procesado
                            }
                        ]
                    }
                ],
                'generationConfig': {
                    'maxOutputTokens': config.max_tokens,
                    'temperature': float(config.temperature)
                }
            }
            
        elif proveedor == 'DeepSeek':
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {clave}'
            }
            payload = {
                'model': config.model_name,
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt_procesado
                    }
                ],
                'max_tokens': config.max_tokens,
                'temperature': float(config.temperature)
            }
        
        # 7. Hacer la petición
        inicio = time.time()
        
        # Para Gemini, usamos la URL modificada
        url = endpoint_url if proveedor == 'Gemini' else config.endpoint_url
        
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=120  # Más tiempo para análisis más complejos
        )
        
        tiempo_respuesta = time.time() - inicio
        
        # 8. Verificar respuesta
        if response.status_code != 200:
            return JsonResponse({
                'error': f'Error de la API {proveedor}: {response.status_code}',
                'detalle': response.text
            }, status=response.status_code)
        
        # 9. Extraer la respuesta según el proveedor
        response_data = response.json()
        comentario_ia = None
        tokens_usados = 0
        
        if proveedor == 'Claude':
            comentario_ia = response_data['content'][0]['text']
            tokens_usados = (
                response_data.get('usage', {}).get('input_tokens', 0) + 
                response_data.get('usage', {}).get('output_tokens', 0)
            )
            
        elif proveedor == 'OpenAI':
            comentario_ia = response_data['choices'][0]['message']['content']
            tokens_usados = response_data.get('usage', {}).get('total_tokens', 0)
            
        elif proveedor == 'Gemini':
            comentario_ia = response_data['candidates'][0]['content']['parts'][0]['text']
            tokens_usados = (
                response_data.get('usageMetadata', {}).get('promptTokenCount', 0) +
                response_data.get('usageMetadata', {}).get('candidatesTokenCount', 0)
            )
            
        elif proveedor == 'DeepSeek':
            comentario_ia = response_data['choices'][0]['message']['content']
            tokens_usados = response_data.get('usage', {}).get('total_tokens', 0)
        
        # 10. Guardar el comentario en la base de datos
        # Eliminar comentario anterior si existe (para evitar duplicados)
        ComentariosEficienciaIndividual.objects.filter(
            id_resultado_eficiencia_individual=resultado_eficiencia
        ).delete()
        
        # Crear nuevo comentario
        comentario = ComentariosEficienciaIndividual.objects.create(
            id_resultado_eficiencia_individual=resultado_eficiencia,
            comentario=comentario_ia
        )
        
        # 11. Retornar resultado
        return JsonResponse({
            'mensaje': 'Comentario de eficiencia generado exitosamente',
            'comentario_id': comentario.id_comentario_eficiencia,
            'resultado_eficiencia_id': id_resultado_eficiencia,
            'modelo_usado': modelo_ia.nombre,
            'proveedor': proveedor,
            'model_name': config.model_name,
            'prompt_usado': {
                'id': prompt_eficiencia.id_prompt_eficiencia,
                'version': prompt_eficiencia.version,
                'descripcion': prompt_eficiencia.descripcion,
                'tipo_analisis': prompt_eficiencia.tipo_analisis
            },
            'tiempo_respuesta_segundos': round(tiempo_respuesta, 2),
            'tokens_usados': tokens_usados,
            'analisis_big_o': {
                'codigo_1': {
                    'temporal': resultado_eficiencia.codigo_1_complejidad_temporal,
                    'espacial': resultado_eficiencia.codigo_1_complejidad_espacial,
                    'ganador': resultado_eficiencia.ganador == 'codigo_1'
                },
                'codigo_2': {
                    'temporal': resultado_eficiencia.codigo_2_complejidad_temporal,
                    'espacial': resultado_eficiencia.codigo_2_complejidad_espacial,
                    'ganador': resultado_eficiencia.ganador == 'codigo_2'
                }
            },
            'comentario': comentario_ia,  # ← AGREGAR ESTA LÍNEA
            'comentario_preview': comentario_ia[:500] + '...' if len(comentario_ia) > 500 else comentario_ia
        }, status=200)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'JSON inválido en el body'
        }, status=400)
    except requests.Timeout:
        return JsonResponse({
            'error': 'Timeout al llamar a la API de IA (análisis muy extenso)'
        }, status=504)
    except requests.RequestException as e:
        return JsonResponse({
            'error': f'Error en la petición HTTP: {str(e)}'
        }, status=500)
    except KeyError as e:
        return JsonResponse({
            'error': f'Falta un campo requerido en el prompt: {str(e)}'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': f'Error interno: {str(e)}'
        }, status=500)
    
@csrf_exempt
@require_http_methods(["GET"])
def obtener_resultados_eficiencia_individual(request, comparacion_id):
    """Obtener los resultados de eficiencia de una comparación individual"""
    payload = validar_token(request)
    
    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    
    if 'error' in payload:
        return JsonResponse(payload, status=401)
    
    try:
        # Obtener la comparación individual
        comparacion = ComparacionesIndividuales.objects.select_related(
            'usuario'
        ).get(id=comparacion_id)
        
        # Verificar que el usuario autenticado sea el dueño de la comparación
        usuario_id_token = payload.get('usuario_id')
        if comparacion.usuario.id != usuario_id_token:
            return JsonResponse({
                'error': 'No tienes permiso para ver estos resultados'
            }, status=403)
        
        # Obtener todos los resultados de eficiencia para esta comparación
        resultados = ResultadosEficienciaIndividual.objects.filter(
            id_comparacion_individual=comparacion_id
        )
        
        # Construir la lista de resultados
        resultados_list = []
        for resultado in resultados:
            resultados_list.append({
                'id_resultado': resultado.id_resultado_eficiencia_individual,
                'codigo_1': {
                    'complejidad_temporal': resultado.codigo_1_complejidad_temporal,
                    'complejidad_espacial': resultado.codigo_1_complejidad_espacial,
                    'nivel_anidamiento': resultado.codigo_1_nivel_anidamiento,
                    'patrones_detectados': resultado.codigo_1_patrones_detectados,
                    'estructuras_datos': resultado.codigo_1_estructuras_datos,
                    'confianza_analisis': resultado.codigo_1_confianza_analisis
                },
                'codigo_2': {
                    'complejidad_temporal': resultado.codigo_2_complejidad_temporal,
                    'complejidad_espacial': resultado.codigo_2_complejidad_espacial,
                    'nivel_anidamiento': resultado.codigo_2_nivel_anidamiento,
                    'patrones_detectados': resultado.codigo_2_patrones_detectados,
                    'estructuras_datos': resultado.codigo_2_estructuras_datos,
                    'confianza_analisis': resultado.codigo_2_confianza_analisis
                },
                'ganador': resultado.ganador,
                'lenguaje': resultado.lenguaje,
                'lenguaje_analizado': resultado.lenguaje_analizado,
                'fecha_analisis': resultado.fecha_analisis.isoformat() if resultado.fecha_analisis else None
            })
        
        return JsonResponse({
            'resultados': resultados_list
        }, status=200)
        
    except ComparacionesIndividuales.DoesNotExist:
        return JsonResponse({
            'error': f'No se encontró la comparación con ID {comparacion_id}'
        }, status=404)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
@csrf_exempt
@require_http_methods(["GET"])
def obtener_comentarios_eficiencia_individual(request, comparacion_id):
    """Obtener los comentarios de eficiencia de una comparación individual"""
    payload = validar_token(request)
    
    if not payload:
        return JsonResponse({'error': 'Token requerido'}, status=401)
    
    if 'error' in payload:
        return JsonResponse(payload, status=401)
    
    try:
        # Obtener la comparación individual
        comparacion = ComparacionesIndividuales.objects.select_related(
            'usuario'
        ).get(id=comparacion_id)
        
        # Verificar que el usuario autenticado sea el dueño de la comparación
        usuario_id_token = payload.get('usuario_id')
        if comparacion.usuario.id != usuario_id_token:
            return JsonResponse({
                'error': 'No tienes permiso para ver estos comentarios'
            }, status=403)
        
        # Obtener los resultados de eficiencia para esta comparación
        resultados_eficiencia = ResultadosEficienciaIndividual.objects.filter(
            id_comparacion_individual=comparacion_id
        )
        
        # Obtener todos los comentarios relacionados a estos resultados
        comentarios = ComentariosEficienciaIndividual.objects.filter(
            id_resultado_eficiencia_individual__in=resultados_eficiencia
        ).select_related('id_resultado_eficiencia_individual')
        
        # Construir la lista de comentarios
        comentarios_list = []
        for comentario in comentarios:
            comentarios_list.append({
                'id_comentario': comentario.id_comentario_eficiencia,
                'id_resultado_eficiencia': comentario.id_resultado_eficiencia_individual.id_resultado_eficiencia_individual,
                'comentario': comentario.comentario,
                'fecha_generacion': comentario.fecha_generacion.isoformat() if comentario.fecha_generacion else None
            })
        
        return JsonResponse({
            'comentarios': comentarios_list
        }, status=200)
        
    except ComparacionesIndividuales.DoesNotExist:
        return JsonResponse({
            'error': f'No se encontró la comparación con ID {comparacion_id}'
        }, status=404)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def crear_comparacion_grupal_ia(request, id_comparacion_grupal):
    try:
        # El ID de la comparación grupal viene desde la URL
        if not id_comparacion_grupal:
            return JsonResponse({
                'error': 'Se requiere id_comparacion_grupal'
            }, status=400)
        
        # 1. Obtener la comparación grupal
        try:
            comparacion = ComparacionesGrupales.objects.get(
                id=id_comparacion_grupal
            )
        except ComparacionesGrupales.DoesNotExist:
            return JsonResponse({
                'error': f'Comparación grupal {id_comparacion_grupal} no encontrada'
            }, status=404)
        
        # 2. Obtener todos los códigos fuente asociados
        codigos_fuente = CodigosFuente.objects.filter(
            comparacion_grupal_id=id_comparacion_grupal
        ).order_by('orden')
        
        if codigos_fuente.count() < 2:
            return JsonResponse({
                'error': 'Se requieren al menos 2 códigos para realizar la comparación'
            }, status=400)
        
        # 3. Obtener el modelo IA
        if not comparacion.id_modelo_ia:
            return JsonResponse({
                'error': 'La comparación no tiene un modelo de IA asignado'
            }, status=400)
        
        modelo_ia = comparacion.id_modelo_ia
        
        # 4. Obtener la configuración según el tipo de modelo
        config = None
        proveedor = None
        prompt_config = None
        
        try:
            config = ConfiguracionClaude.objects.select_related('id_prompt_grupal').get(
                id_modelo_ia_id=modelo_ia.id,
                activo=True
            )
            proveedor = 'Claude'
            prompt_config = config.id_prompt_grupal
        except ConfiguracionClaude.DoesNotExist:
            pass
        
        if not config:
            try:
                config = ConfiguracionOpenai.objects.select_related('id_prompt_grupal').get(
                    id_modelo_ia_id=modelo_ia.id,
                    activo=True
                )
                proveedor = 'OpenAI'
                prompt_config = config.id_prompt_grupal
            except ConfiguracionOpenai.DoesNotExist:
                pass
        
        if not config:
            try:
                config = ConfiguracionGemini.objects.select_related('id_prompt_grupal').get(
                    id_modelo_ia_id=modelo_ia.id,
                    activo=True
                )
                proveedor = 'Gemini'
                prompt_config = config.id_prompt_grupal
            except ConfiguracionGemini.DoesNotExist:
                pass
        
        if not config:
            try:
                config = ConfiguracionDeepseek.objects.select_related('id_prompt_grupal').get(
                    id_modelo_ia_id=modelo_ia.id,
                    activo=True
                )
                proveedor = 'DeepSeek'
                prompt_config = config.id_prompt_grupal
            except ConfiguracionDeepseek.DoesNotExist:
                pass
        
        if not config or not prompt_config:
            return JsonResponse({
                'error': 'No hay configuración activa para este modelo de IA o no tiene prompt grupal configurado'
            }, status=404)
        
        # 5. Verificar que el prompt esté activo
        if not prompt_config.activo:
            return JsonResponse({
                'error': 'El prompt grupal configurado no está activo'
            }, status=400)
        
        # 6. Construir el array de códigos para el prompt
        codigos_array = []
        for idx, codigo in enumerate(codigos_fuente, start=1):
            nombre_archivo = codigo.nombre_archivo or f"Código {idx}"
            codigos_array.append(
                f"### CÓDIGO {idx}: {nombre_archivo}\n```\n{codigo.codigo}\n```"
            )
        
        codigos_texto = "\n\n".join(codigos_array)
        
        # 7. Reemplazar placeholders en el prompt
        prompt_procesado = prompt_config.template_prompt.replace(
            '{{codigos_array}}', codigos_texto
        )
        
        for idx, codigo in enumerate(codigos_fuente, start=1):
            nombre_archivo = codigo.nombre_archivo or f"Código {idx}"
            prompt_procesado = prompt_procesado.replace(
                f'{{{{nombre_archivo_{idx}}}}}', nombre_archivo
            ).replace(
                f'{{{{codigo_{idx}}}}}', codigo.codigo
            )
        
        # 8. Preparar headers y payload según el proveedor
        headers = {}
        payload = {}

        # La clave la aporta quien despliega el sistema: la registrada en la
        # configuracion del modelo o, en su defecto, la variable de entorno del
        # proveedor. El sistema no distribuye credenciales propias.
        try:
            clave = clave_api(config, proveedor)
        except CredencialAusente as falta_clave:
            return JsonResponse({'error': str(falta_clave)}, status=409)
        endpoint_url = config.endpoint_url
        
        if proveedor == 'Claude':
            headers = {
                'Content-Type': 'application/json',
                'x-api-key': clave,
                'anthropic-version': config.anthropic_version
            }
            payload = {
                'model': config.model_name,
                'max_tokens': config.max_tokens,
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt_procesado
                    }
                ]
            }
            
        elif proveedor == 'OpenAI':
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {clave}'
            }
            payload = {
                'model': config.model_name,
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt_procesado
                    }
                ],
                'max_tokens': config.max_tokens,
                'temperature': float(config.temperature)
            }
            
        elif proveedor == 'Gemini':
            headers = {
                'Content-Type': 'application/json'
            }
            endpoint_url = f"{config.endpoint_url}/{config.model_name}:generateContent?key={clave}"
            payload = {
                'contents': [
                    {
                        'parts': [
                            {
                                'text': prompt_procesado
                            }
                        ]
                    }
                ],
                'generationConfig': {
                    'maxOutputTokens': config.max_tokens,
                    'temperature': float(config.temperature)
                }
            }
            
        elif proveedor == 'DeepSeek':
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {clave}'
            }
            payload = {
                'model': config.model_name,
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt_procesado
                    }
                ],
                'max_tokens': config.max_tokens,
                'temperature': float(config.temperature)
            }
        
        # 9. Hacer la petición a la API
        inicio = time.time()
        
        response = requests.post(
            endpoint_url,
            headers=headers,
            json=payload,
            timeout=120
        )
        
        tiempo_respuesta = time.time() - inicio
        
        # 10. Verificar respuesta
        if response.status_code != 200:
            return JsonResponse({
                'error': f'Error de la API {proveedor}: {response.status_code}',
                'detalle': response.text
            }, status=response.status_code)
        
        # 11. Extraer la respuesta según el proveedor
        response_data = response.json()
        respuesta_ia = None
        tokens_usados = 0
        
        if proveedor == 'Claude':
            respuesta_ia = response_data['content'][0]['text']
            tokens_usados = (
                response_data.get('usage', {}).get('input_tokens', 0) + 
                response_data.get('usage', {}).get('output_tokens', 0)
            )
            
        elif proveedor == 'OpenAI':
            respuesta_ia = response_data['choices'][0]['message']['content']
            tokens_usados = response_data.get('usage', {}).get('total_tokens', 0)
            
        elif proveedor == 'Gemini':
            respuesta_ia = response_data['candidates'][0]['content']['parts'][0]['text']
            tokens_usados = (
                response_data.get('usageMetadata', {}).get('promptTokenCount', 0) +
                response_data.get('usageMetadata', {}).get('candidatesTokenCount', 0)
            )
            
        elif proveedor == 'DeepSeek':
            respuesta_ia = response_data['choices'][0]['message']['content']
            tokens_usados = response_data.get('usage', {}).get('total_tokens', 0)
        
        # 12. Procesar respuesta JSON de la IA
        datos_estructurados = None
        resumen = None
        mas_similares_list = []
        # ── NUEVO: código base de referencia ──
        codigo_base = None

        try:
            # Limpiar respuesta
            respuesta_limpia = respuesta_ia.strip()
            
            # Remover markdown si existe
            if '```json' in respuesta_limpia:
                respuesta_limpia = respuesta_limpia.split('```json')[1].split('```')[0].strip()
            elif '```' in respuesta_limpia:
                respuesta_limpia = respuesta_limpia.split('```')[1].split('```')[0].strip()
            
            # Parsear JSON
            datos_estructurados = json.loads(respuesta_limpia)
            resumen = datos_estructurados.get('resumen', '')
            mas_similares_list = datos_estructurados.get('mas_similares', [])

            # ── NUEVO: extraer codigo_base si la IA lo generó ──
            if 'codigo_base' in datos_estructurados:
                codigo_base = datos_estructurados['codigo_base']
            
        except json.JSONDecodeError as e:
            print(f"Error al parsear JSON de la IA: {e}")
            resumen = "Error al procesar respuesta estructurada de la IA"
            mas_similares_list = []
        
        # Función auxiliar para determinar nivel de similitud
        def obtener_nivel_similitud(porcentaje):
            if porcentaje >= 91:
                return 'muy_alta'
            elif porcentaje >= 70:
                return 'alta'
            elif porcentaje >= 40:
                return 'media'
            elif porcentaje >= 20:
                return 'baja'
            else:
                return 'muy_baja'
        
        # Crear diccionario de códigos por orden para búsqueda rápida
        codigos_por_orden = {}
        for idx, codigo in enumerate(codigos_fuente, start=1):
            nombre_archivo = codigo.nombre_archivo or f"Código {idx}"
            codigos_por_orden[idx] = nombre_archivo
        
        # 13. Guardar resultado en la base de datos
        try:
            # Eliminar resultado anterior si existe
            ResultadosSimilitudGrupal.objects.filter(
                id_comparacion_grupal=comparacion
            ).delete()
            
            # Formatear mas_similares para guardarlo como texto
            mas_similares_texto = ""
            if mas_similares_list:
                if (len(mas_similares_list) == 1 and 
                    mas_similares_list[0].get('par') == 'Ninguno'):
                    mas_similares_texto = mas_similares_list[0].get('razon', 'No se encontraron similitudes notables')
                else:
                    mas_similares_texto = "\n".join([
                        f"• {item['par']} ({item['similitud']}%): {item['razon']}" 
                        for item in mas_similares_list
                    ])
            else:
                mas_similares_texto = "No se encontraron similitudes notables entre los códigos"
            
            # Crear nuevo resultado principal
            resultado = ResultadosSimilitudGrupal.objects.create(
                id_comparacion_grupal=comparacion,
                resumen_general=resumen,
                codigos_mas_similares=mas_similares_texto,
                respuesta_completa=respuesta_ia,
                tokens_usados=tokens_usados,
                tiempo_respuesta_segundos=round(tiempo_respuesta, 2)
            )
            
            # Guardar comparaciones pareadas
            comparaciones_guardadas = []
            if datos_estructurados and 'matriz_similitud' in datos_estructurados:
                for comparacion_item in datos_estructurados['matriz_similitud']:
                    similitud = comparacion_item.get('similitud', 0)
                    nivel = comparacion_item.get('nivel', obtener_nivel_similitud(similitud))
                    orden_a = comparacion_item.get('orden_a', 0)
                    orden_b = comparacion_item.get('orden_b', 0)
                    
                    codigo_a_nombre = comparacion_item.get('codigo_a', codigos_por_orden.get(orden_a, f'Código {orden_a}'))
                    codigo_b_nombre = comparacion_item.get('codigo_b', codigos_por_orden.get(orden_b, f'Código {orden_b}'))
                    
                    comp = ComparacionesPareadas.objects.create(
                        id_resultado_similitud_grupal=resultado,
                        codigo_a_nombre=codigo_a_nombre,
                        codigo_a_orden=orden_a,
                        codigo_b_nombre=codigo_b_nombre,
                        codigo_b_orden=orden_b,
                        porcentaje_similitud=similitud,
                        nivel_similitud=nivel
                    )
                    
                    comparaciones_guardadas.append({
                        'codigo_a': codigo_a_nombre,
                        'codigo_a_nombre': codigo_a_nombre,
                        'orden_a': orden_a,
                        'codigo_b': codigo_b_nombre,
                        'codigo_b_nombre': codigo_b_nombre,
                        'orden_b': orden_b,
                        'similitud': int(comp.porcentaje_similitud),
                        'nivel': comp.nivel_similitud
                    })
            
            mensaje_guardado = 'Resultado guardado exitosamente'
            resultado_id = resultado.id_resultado_similitud_grupal
            
        except Exception as e:
            mensaje_guardado = f'Error al guardar resultado: {str(e)}'
            resultado_id = None
            comparaciones_guardadas = []
        
        # 14. Preparar matriz para respuesta (formato tabla)
        matriz_tabla = {}
        if datos_estructurados and 'matriz_similitud' in datos_estructurados:
            for item in datos_estructurados['matriz_similitud']:
                similitud = item.get('similitud', 0)
                nivel = item.get('nivel', obtener_nivel_similitud(similitud))
                orden_a = item.get('orden_a', 0)
                orden_b = item.get('orden_b', 0)
                
                key = f"{orden_a}-{orden_b}"
                matriz_tabla[key] = {
                    'similitud': similitud,
                    'nivel': nivel
                }
                key_inv = f"{orden_b}-{orden_a}"
                matriz_tabla[key_inv] = {
                    'similitud': similitud,
                    'nivel': nivel
                }
        
        # 15. Preparar resumen de códigos comparados
        codigos_resumen = []
        for idx, codigo in enumerate(codigos_fuente, start=1):
            nombre_archivo = codigo.nombre_archivo or f"Código {idx}"
            preview = codigo.codigo[:100] + '...' if len(codigo.codigo) > 100 else codigo.codigo
            codigos_resumen.append({
                'orden': idx,
                'nombre_archivo': nombre_archivo,
                'preview': preview,
                'longitud': len(codigo.codigo)
            })
        
        # 16. Retornar resultado
        return JsonResponse({
            'mensaje': 'Comparación grupal exitosa',
            'guardado': mensaje_guardado,
            'resumen_general': resumen,
            'codigos_mas_similares': mas_similares_list,
            'matriz_similitud': comparaciones_guardadas,
            'matriz_tabla': matriz_tabla,
            'codigos_comparados': codigos_resumen,
            # ── NUEVO: retornar codigo_base al frontend ──
            'codigo_base': codigo_base,
        }, status=200)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'JSON inválido en el body'
        }, status=400)
    except requests.Timeout:
        return JsonResponse({
            'error': 'Timeout al llamar a la API de IA (análisis grupal requiere más tiempo)'
        }, status=504)
    except requests.RequestException as e:
        return JsonResponse({
            'error': f'Error en la petición HTTP: {str(e)}'
        }, status=500)
    except Exception as e:
        return JsonResponse({
            'error': f'Error interno: {str(e)}'
        }, status=500)
    
@csrf_exempt
@require_http_methods(["POST"])
def analizar_big_o_grupal(request, comparacion_grupal_id):
    """Analizar Big O de una comparación grupal y guardar resultados"""
    payload = validar_token(request)
    
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido'}, status=401)
    
    try:
        comparacion_grupal = ComparacionesGrupales.objects.get(pk=comparacion_grupal_id)
        
        # Obtener todos los códigos de la comparación grupal ordenados
        codigos_fuente = CodigosFuente.objects.filter(
            comparacion_grupal=comparacion_grupal_id
        ).order_by('orden')
        
        if codigos_fuente.count() < 2:
            return JsonResponse({
                'error': 'Se necesitan al menos 2 códigos para analizar'
            }, status=400)
        
        lenguaje = comparacion_grupal.lenguaje.nombre.lower()
        
        # Detectar lenguaje si no está soportado
        if lenguaje not in LENGUAJES_SOPORTADOS:
            extension = comparacion_grupal.lenguaje.extension
            lenguaje_detectado = detectar_lenguaje_por_extension(extension)
            
            if not lenguaje_detectado:
                return JsonResponse({
                    'advertencia': f'Lenguaje "{comparacion_grupal.lenguaje.nombre}" no completamente soportado.',
                    'lenguaje_original': comparacion_grupal.lenguaje.nombre,
                    'usando_analisis': 'generico'
                }, status=200)
            
            lenguaje = lenguaje_detectado
        
        # Analizar cada código
        analisis_codigos = []
        for codigo_fuente in codigos_fuente:
            analisis = analizar_codigo_big_o(codigo_fuente.codigo, lenguaje)
            analisis['id_codigo_fuente'] = codigo_fuente.id
            analisis['orden'] = codigo_fuente.orden
            analisis['nombre_archivo'] = codigo_fuente.nombre_archivo
            analisis_codigos.append(analisis)
        
        # Determinar ganador(es) y rankings
        ganadores_info = determinar_ganadores_grupal(analisis_codigos)
        
        # Calcular estadísticas generales
        complejidades_temporales = [a['complejidad_temporal'] for a in analisis_codigos]
        niveles_anidamiento = [a['nivel_anidamiento'] for a in analisis_codigos]
        
        mejor_complejidad = min(complejidades_temporales, key=orden_complejidad)
        peor_complejidad = max(complejidades_temporales, key=orden_complejidad)
        
        # Determinar confianza general (la más baja de todas)
        confianzas = [a['confianza_analisis'] for a in analisis_codigos]
        confianza_general = determinar_confianza_general(confianzas)
        
        # Crear resultado principal
        resultado_grupal = ResultadosEficienciaGrupal.objects.create(
            id_comparacion_grupal=comparacion_grupal,
            fecha_analisis=timezone.now(),
            total_codigos=len(analisis_codigos),
            ganador=ganadores_info['ganador'],
            tipo_ganador=ganadores_info['tipo_ganador'],
            complejidad_temporal_mejor=mejor_complejidad,
            complejidad_temporal_peor=peor_complejidad,
            nivel_anidamiento_maximo=max(niveles_anidamiento),
            nivel_anidamiento_minimo=min(niveles_anidamiento),
            confianza_analisis_general=confianza_general
        )
        
        # Guardar detalles de cada código
        detalles_guardados = []
        for analisis in analisis_codigos:
            detalle = DetallesCodigoEficienciaGrupal.objects.create(
                id_resultado_eficiencia_grupal=resultado_grupal,
                id_codigo_fuente_id=analisis['id_codigo_fuente'],
                orden=analisis['orden'],
                complejidad_temporal=analisis['complejidad_temporal'],
                complejidad_espacial=analisis['complejidad_espacial'],
                nivel_anidamiento=analisis['nivel_anidamiento'],
                patrones_detectados=analisis['patrones_detectados'],
                estructuras_datos=analisis['estructuras_datos'],
                confianza_analisis=analisis['confianza_analisis'],
                es_ganador=analisis['es_ganador'],
                es_empate=analisis['es_empate'],
                ranking_eficiencia=analisis['ranking_eficiencia']
            )
            
            detalles_guardados.append({
                'id_detalle': detalle.id_detalle_codigo_eficiencia_grupal,
                'orden': analisis['orden'],
                'nombre_archivo': analisis['nombre_archivo'],
                'complejidad_temporal': analisis['complejidad_temporal'],
                'complejidad_espacial': analisis['complejidad_espacial'],
                'nivel_anidamiento': analisis['nivel_anidamiento'],
                'patrones_detectados': analisis['patrones_detectados'],
                'estructuras_datos': analisis['estructuras_datos'],
                'confianza_analisis': analisis['confianza_analisis'],
                'es_ganador': analisis['es_ganador'],
                'es_empate': analisis['es_empate'],
                'ranking_eficiencia': analisis['ranking_eficiencia']
            })
        
        # Preparar respuesta
        resultado = {
            'mensaje': 'Análisis Big O grupal completado',
            'resultado_id': resultado_grupal.id_resultado_eficiencia_grupal,
            'total_codigos': len(analisis_codigos),
            'ganador': ganadores_info['ganador'],
            'tipo_ganador': ganadores_info['tipo_ganador'],
            'complejidad_temporal_mejor': mejor_complejidad,
            'complejidad_temporal_peor': peor_complejidad,
            'nivel_anidamiento_maximo': max(niveles_anidamiento),
            'nivel_anidamiento_minimo': min(niveles_anidamiento),
            'confianza_analisis_general': confianza_general,
            'codigos_analizados': detalles_guardados,
            'lenguaje': comparacion_grupal.lenguaje.nombre,
            'lenguaje_analizado': LENGUAJES_SOPORTADOS[lenguaje]['nombre']
        }
        
        return JsonResponse(resultado, status=200)
        
    except ComparacionesGrupales.DoesNotExist:
        return JsonResponse({'error': 'Comparación grupal no encontrada'}, status=404)
    except Exception as e:
        import traceback
        print("ERROR:", str(e))
        print(traceback.format_exc())
        return JsonResponse({
            'error': str(e),
            'traceback': traceback.format_exc()
        }, status=500)


def determinar_ganadores_grupal(analisis_codigos: List[Dict]) -> Dict:
    """
    Determina el/los ganador(es) en una comparación grupal
    Retorna: {
        'ganador': orden del ganador o None,
        'tipo_ganador': 'unico' | 'empate_multiple' | 'empate_todos'
    }
    """
    # Ordenar por complejidad temporal
    complejidades = [(a['orden'], a['complejidad_temporal']) for a in analisis_codigos]
    mejor_complejidad = min(complejidades, key=lambda x: orden_complejidad(x[1]))[1]
    
    # Encontrar todos los códigos con la mejor complejidad
    ganadores = [
        orden for orden, comp in complejidades 
        if orden_complejidad(comp) == orden_complejidad(mejor_complejidad)
    ]
    
    # Marcar ganadores y empates en cada análisis
    for analisis in analisis_codigos:
        if analisis['orden'] in ganadores:
            if len(ganadores) == 1:
                analisis['es_ganador'] = True
                analisis['es_empate'] = False
                analisis['ranking_eficiencia'] = 1
            else:
                analisis['es_ganador'] = False
                analisis['es_empate'] = True
                analisis['ranking_eficiencia'] = 1
        else:
            analisis['es_ganador'] = False
            analisis['es_empate'] = False
            # Calcular ranking para los no ganadores
            complejidad_actual = orden_complejidad(analisis['complejidad_temporal'])
            ranking = 1 + sum(
                1 for a in analisis_codigos 
                if orden_complejidad(a['complejidad_temporal']) < complejidad_actual
            )
            analisis['ranking_eficiencia'] = ranking
    
    # Determinar tipo de ganador
    if len(ganadores) == 1:
        return {
            'ganador': ganadores[0],
            'tipo_ganador': 'unico'
        }
    elif len(ganadores) == len(analisis_codigos):
        return {
            'ganador': None,
            'tipo_ganador': 'empate_todos'
        }
    else:
        return {
            'ganador': None,
            'tipo_ganador': 'empate_multiple'
        }


def determinar_confianza_general(confianzas: List[str]) -> str:
    """
    Determina la confianza general del análisis grupal
    Toma la confianza más baja de todas
    """
    orden_confianza = {
        'Baja - Análisis genérico': 1,
        'Baja': 2,
        'Media': 3,
        'Alta': 4
    }
    
    confianza_minima = min(confianzas, key=lambda c: orden_confianza.get(c, 0))
    return confianza_minima

@csrf_exempt
@require_http_methods(["POST"])
def crear_comentario_eficiencia_grupal(request, id_resultado_eficiencia_grupal):
    try:
        # 1. Obtener el resultado de eficiencia grupal
        try:
            resultado_eficiencia = ResultadosEficienciaGrupal.objects.select_related(
                'id_comparacion_grupal',
                'id_comparacion_grupal__usuario',
                'id_comparacion_grupal__lenguaje',
                'id_comparacion_grupal__id_modelo_ia'
            ).get(id_resultado_eficiencia_grupal=id_resultado_eficiencia_grupal)
        except ResultadosEficienciaGrupal.DoesNotExist:
            return JsonResponse({
                'error': f'Resultado de eficiencia grupal {id_resultado_eficiencia_grupal} no encontrado'
            }, status=404)
        
        comparacion = resultado_eficiencia.id_comparacion_grupal
        
        # 2. Obtener todos los códigos y sus detalles de eficiencia
        codigos_fuente = CodigosFuente.objects.filter(
            comparacion_grupal=comparacion
        ).order_by('orden')
        
        detalles_eficiencia = DetallesCodigoEficienciaGrupal.objects.filter(
            id_resultado_eficiencia_grupal=resultado_eficiencia
        ).select_related('id_codigo_fuente').order_by('orden')
        
        if not codigos_fuente.exists():
            return JsonResponse({
                'error': 'No hay códigos fuente para esta comparación grupal'
            }, status=404)
        
        # 3. Obtener el modelo IA
        if not comparacion.id_modelo_ia:
            return JsonResponse({
                'error': 'La comparación no tiene un modelo de IA asignado'
            }, status=400)
        
        modelo_ia = comparacion.id_modelo_ia
        
        # 4. Obtener la configuración según el tipo de modelo
        config = None
        proveedor = None
        prompt_eficiencia = None
        
        # Intentar obtener configuración de cada proveedor
        if not config:
            try:
                config = ConfiguracionClaude.objects.get(
                    id_modelo_ia_id=modelo_ia.id,
                    activo=True
                )
                proveedor = 'Claude'
                prompt_eficiencia = PromptEficienciaAlgoritmica.objects.get(
                    id_prompt_eficiencia=config.id_prompt_eficiencia_id
                )
            except (ConfiguracionClaude.DoesNotExist, PromptEficienciaAlgoritmica.DoesNotExist):
                pass
        
        if not config:
            try:
                config = ConfiguracionOpenai.objects.get(
                    id_modelo_ia_id=modelo_ia.id,
                    activo=True
                )
                proveedor = 'OpenAI'
                prompt_eficiencia = PromptEficienciaAlgoritmica.objects.get(
                    id_prompt_eficiencia=config.id_prompt_eficiencia_id
                )
            except (ConfiguracionOpenai.DoesNotExist, PromptEficienciaAlgoritmica.DoesNotExist):
                pass
        
        if not config:
            try:
                config = ConfiguracionGemini.objects.get(
                    id_modelo_ia_id=modelo_ia.id,
                    activo=True
                )
                proveedor = 'Gemini'
                prompt_eficiencia = PromptEficienciaAlgoritmica.objects.get(
                    id_prompt_eficiencia=config.id_prompt_eficiencia_id
                )
            except (ConfiguracionGemini.DoesNotExist, PromptEficienciaAlgoritmica.DoesNotExist):
                pass
        
        if not config:
            try:
                config = ConfiguracionDeepseek.objects.get(
                    id_modelo_ia_id=modelo_ia.id,
                    activo=True
                )
                proveedor = 'DeepSeek'
                prompt_eficiencia = PromptEficienciaAlgoritmica.objects.get(
                    id_prompt_eficiencia=config.id_prompt_eficiencia_id
                )
            except (ConfiguracionDeepseek.DoesNotExist, PromptEficienciaAlgoritmica.DoesNotExist):
                pass
        
        if not config:
            return JsonResponse({
                'error': 'No hay configuración activa para este modelo de IA'
            }, status=404)
        
        # 5. Verificar que el prompt de eficiencia exista, esté activo y sea de tipo 'grupal'
        # Buscar el prompt de tipo grupal más reciente y activo
        prompt_eficiencia = PromptEficienciaAlgoritmica.objects.filter(
            tipo_analisis='grupal',
            activo=True
        ).order_by('-fecha_creacion').first()
        
        if not prompt_eficiencia:
            return JsonResponse({
                'error': 'No hay prompt de eficiencia de tipo grupal activo en el sistema'
            }, status=400)
        
        # 6. Construir el array de códigos para el prompt
        codigos_array_texto = ""
        for idx, codigo in enumerate(codigos_fuente, 1):
            codigos_array_texto += f"\n--- CÓDIGO {idx} ---\n"
            codigos_array_texto += f"Nombre archivo: {codigo.nombre_archivo or 'Sin nombre'}\n"
            codigos_array_texto += f"Orden: {codigo.orden}\n"
            codigos_array_texto += f"Código:\n{codigo.codigo}\n"
        
        # 7. Construir los resultados de eficiencia para el prompt
        resultados_eficiencia_texto = ""
        for detalle in detalles_eficiencia:
            resultados_eficiencia_texto += f"\n--- CÓDIGO {detalle.orden} ---\n"
            resultados_eficiencia_texto += f"Nombre archivo: {detalle.id_codigo_fuente.nombre_archivo or 'Sin nombre'}\n"
            resultados_eficiencia_texto += f"Complejidad Temporal: {detalle.complejidad_temporal}\n"
            resultados_eficiencia_texto += f"Complejidad Espacial: {detalle.complejidad_espacial}\n"
            resultados_eficiencia_texto += f"Nivel de Anidamiento: {detalle.nivel_anidamiento}\n"
            resultados_eficiencia_texto += f"Es Ganador: {'Sí' if detalle.es_ganador else 'No'}\n"
            resultados_eficiencia_texto += f"Es Empate: {'Sí' if detalle.es_empate else 'No'}\n"
            resultados_eficiencia_texto += f"Ranking: {detalle.ranking_eficiencia or 'N/A'}\n"
            resultados_eficiencia_texto += f"Confianza: {detalle.confianza_analisis or 'N/A'}\n"
            if detalle.patrones_detectados:
                resultados_eficiencia_texto += f"Patrones detectados: {json.dumps(detalle.patrones_detectados, indent=2)}\n"
            if detalle.estructuras_datos:
                resultados_eficiencia_texto += f"Estructuras de datos: {json.dumps(detalle.estructuras_datos, indent=2)}\n"
        
        # 8. Reemplazar placeholders en el prompt
        prompt_procesado = prompt_eficiencia.template_prompt.format(
            codigos_array=codigos_array_texto,
            resultados_eficiencia=resultados_eficiencia_texto,
            total_codigos=resultado_eficiencia.total_codigos,
            lenguaje=comparacion.lenguaje.nombre if comparacion.lenguaje else 'No especificado'
        )
        
        # 9. Preparar headers y payload según el proveedor
        headers = {}
        payload = {}

        # La clave la aporta quien despliega el sistema: la registrada en la
        # configuracion del modelo o, en su defecto, la variable de entorno del
        # proveedor. El sistema no distribuye credenciales propias.
        try:
            clave = clave_api(config, proveedor)
        except CredencialAusente as falta_clave:
            return JsonResponse({'error': str(falta_clave)}, status=409)
        endpoint_url = config.endpoint_url
        
        if proveedor == 'Claude':
            headers = {
                'Content-Type': 'application/json',
                'x-api-key': clave,
                'anthropic-version': config.anthropic_version
            }
            payload = {
                'model': config.model_name,
                'max_tokens': config.max_tokens,
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt_procesado
                    }
                ]
            }
            
        elif proveedor == 'OpenAI':
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {clave}'
            }
            payload = {
                'model': config.model_name,
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt_procesado
                    }
                ],
                'max_tokens': config.max_tokens,
                'temperature': float(config.temperature)
            }
            
        elif proveedor == 'Gemini':
            headers = {
                'Content-Type': 'application/json'
            }
            endpoint_url = f"{config.endpoint_url}/{config.model_name}:generateContent?key={clave}"
            payload = {
                'contents': [
                    {
                        'parts': [
                            {
                                'text': prompt_procesado
                            }
                        ]
                    }
                ],
                'generationConfig': {
                    'maxOutputTokens': config.max_tokens,
                    'temperature': float(config.temperature)
                }
            }
            
        elif proveedor == 'DeepSeek':
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {clave}'
            }
            payload = {
                'model': config.model_name,
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt_procesado
                    }
                ],
                'max_tokens': config.max_tokens,
                'temperature': float(config.temperature)
            }
        
        # 10. Hacer la petición a la IA
        inicio = time.time()
        
        response = requests.post(
            endpoint_url,
            headers=headers,
            json=payload,
            timeout=180  # Más tiempo para análisis grupal
        )
        
        tiempo_respuesta = time.time() - inicio
        
        # 11. Verificar respuesta
        if response.status_code != 200:
            return JsonResponse({
                'error': f'Error de la API {proveedor}: {response.status_code}',
                'detalle': response.text
            }, status=response.status_code)
        
        # 12. Extraer la respuesta según el proveedor
        response_data = response.json()
        respuesta_ia = None
        tokens_usados = 0
        
        if proveedor == 'Claude':
            respuesta_ia = response_data['content'][0]['text']
            tokens_usados = (
                response_data.get('usage', {}).get('input_tokens', 0) + 
                response_data.get('usage', {}).get('output_tokens', 0)
            )
            
        elif proveedor == 'OpenAI':
            respuesta_ia = response_data['choices'][0]['message']['content']
            tokens_usados = response_data.get('usage', {}).get('total_tokens', 0)
            
        elif proveedor == 'Gemini':
            respuesta_ia = response_data['candidates'][0]['content']['parts'][0]['text']
            tokens_usados = (
                response_data.get('usageMetadata', {}).get('promptTokenCount', 0) +
                response_data.get('usageMetadata', {}).get('candidatesTokenCount', 0)
            )
            
        elif proveedor == 'DeepSeek':
            respuesta_ia = response_data['choices'][0]['message']['content']
            tokens_usados = response_data.get('usage', {}).get('total_tokens', 0)
        
        # 13. Parsear el JSON de la respuesta
        try:
            # Limpiar markdown si viene con ```json
            respuesta_limpia = respuesta_ia.strip()
            if respuesta_limpia.startswith('```json'):
                respuesta_limpia = respuesta_limpia[7:]
            if respuesta_limpia.startswith('```'):
                respuesta_limpia = respuesta_limpia[3:]
            if respuesta_limpia.endswith('```'):
                respuesta_limpia = respuesta_limpia[:-3]
            
            datos_ia = json.loads(respuesta_limpia.strip())
        except json.JSONDecodeError as e:
            return JsonResponse({
                'error': 'La IA no devolvió un JSON válido',
                'detalle': str(e),
                'respuesta_ia': respuesta_ia[:500]
            }, status=500)
        
        # 14. Guardar en la base de datos
        # Eliminar comentario anterior si existe
        ComentariosIaGrupal.objects.filter(
            id_resultado_eficiencia_grupal=resultado_eficiencia
        ).delete()
        
        # Extraer datos del análisis comparativo
        analisis_comp = datos_ia.get('analisis_comparativo', {})
        mejor_codigo = analisis_comp.get('mejor_codigo', {})
        peor_codigo = analisis_comp.get('peor_codigo', {})
        patrones = datos_ia.get('patrones_comunes', {})
        
        # Crear el comentario grupal principal
        comentario_grupal = ComentariosIaGrupal.objects.create(
            id_comparacion_grupal=comparacion,
            id_resultado_eficiencia_grupal=resultado_eficiencia,
            id_prompt_eficiencia=prompt_eficiencia,
            resumen_comparativo=analisis_comp.get('resumen_comparativo', ''),
            mejor_codigo_orden=mejor_codigo.get('orden'),
            mejor_codigo_razon=mejor_codigo.get('razon', ''),
            peor_codigo_orden=peor_codigo.get('orden'),
            peor_codigo_razon=peor_codigo.get('razon', ''),
            patrones_eficientes=patrones.get('eficientes', []),
            patrones_ineficientes=patrones.get('ineficientes', []),
            recomendaciones_generales=datos_ia.get('recomendaciones_generales', []),
            ranking_ia=datos_ia.get('ranking_eficiencia', []),
            respuesta_completa_ia=datos_ia
        )
        
        # 15. Guardar comentarios individuales de cada código
        comentarios_individuales = datos_ia.get('comentarios_individuales', [])
        comentarios_creados = []
        
        for comentario_data in comentarios_individuales:
            orden = comentario_data.get('orden')
            
            # Buscar el código fuente correspondiente
            try:
                codigo_fuente = CodigosFuente.objects.get(
                    comparacion_grupal=comparacion,
                    orden=orden
                )
                
                # Buscar el detalle de eficiencia correspondiente
                detalle_eficiencia = DetallesCodigoEficienciaGrupal.objects.get(
                    id_resultado_eficiencia_grupal=resultado_eficiencia,
                    orden=orden
                )
                
                # Crear el comentario individual
                comentario_individual = ComentariosCodigoGrupal.objects.create(
                    id_comentario_grupal=comentario_grupal,
                    id_codigo_fuente=codigo_fuente,
                    id_detalle_codigo_eficiencia_grupal=detalle_eficiencia,
                    orden=orden,
                    nombre_archivo=comentario_data.get('nombre_archivo', codigo_fuente.nombre_archivo),
                    comentario_general=comentario_data.get('comentario_general', ''),
                    puntos_fuertes=comentario_data.get('puntos_fuertes', []),
                    puntos_debiles=comentario_data.get('puntos_debiles', []),
                    recomendaciones=comentario_data.get('recomendaciones', []),
                    nota_eficiencia=comentario_data.get('nota_eficiencia')
                )
                
                comentarios_creados.append({
                    'id': comentario_individual.id_comentario_codigo_grupal,
                    'orden': orden,
                    'nombre_archivo': comentario_individual.nombre_archivo,
                    'nota_eficiencia': float(comentario_individual.nota_eficiencia) if comentario_individual.nota_eficiencia else None
                })
                
            except CodigosFuente.DoesNotExist:
                print(f"Advertencia: Código con orden {orden} no encontrado")
                continue
            except DetallesCodigoEficienciaGrupal.DoesNotExist:
                print(f"Advertencia: Detalle de eficiencia con orden {orden} no encontrado")
                continue
        
        # 16. Retornar resultado
        return JsonResponse({
            'mensaje': 'Comentarios de eficiencia grupal generados exitosamente',
            'comentario_grupal_id': comentario_grupal.id_comentario_grupal,
            'resultado_eficiencia_grupal_id': id_resultado_eficiencia_grupal,
            'comparacion_grupal_id': comparacion.id,
            'modelo_usado': modelo_ia.nombre,
            'proveedor': proveedor,
            'model_name': config.model_name,
            'prompt_usado': {
                'id': prompt_eficiencia.id_prompt_eficiencia,
                'version': prompt_eficiencia.version,
                'descripcion': prompt_eficiencia.descripcion,
                'tipo_analisis': prompt_eficiencia.tipo_analisis
            },
            'estadisticas': {
                'total_codigos_analizados': resultado_eficiencia.total_codigos,
                'comentarios_individuales_creados': len(comentarios_creados),
                'tiempo_respuesta_segundos': round(tiempo_respuesta, 2),
                'tokens_usados': tokens_usados
            },
            'analisis_completo': {
                'resumen_comparativo': comentario_grupal.resumen_comparativo,
                'mejor_codigo': {
                    'orden': comentario_grupal.mejor_codigo_orden,
                    'razon': comentario_grupal.mejor_codigo_razon
                },
                'peor_codigo': {
                    'orden': comentario_grupal.peor_codigo_orden,
                    'razon': comentario_grupal.peor_codigo_razon
                },
                'patrones_eficientes': comentario_grupal.patrones_eficientes,
                'patrones_ineficientes': comentario_grupal.patrones_ineficientes,
                'recomendaciones_generales': comentario_grupal.recomendaciones_generales,
                'ranking_ia': comentario_grupal.ranking_ia
            },
            'comentarios_individuales': [
                {
                    'id': com['id'],
                    'orden': com['orden'],
                    'nombre_archivo': com['nombre_archivo'],
                    'nota_eficiencia': com['nota_eficiencia']
                } for com in comentarios_creados
            ],
            'respuesta_completa_ia': datos_ia
        }, status=200)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'JSON inválido en el body'
        }, status=400)
    except requests.Timeout:
        return JsonResponse({
            'error': 'Timeout al llamar a la API de IA (análisis muy extenso)'
        }, status=504)
    except requests.RequestException as e:
        return JsonResponse({
            'error': f'Error en la petición HTTP: {str(e)}'
        }, status=500)
    except KeyError as e:
        return JsonResponse({
            'error': f'Falta un campo requerido en el prompt o respuesta: {str(e)}'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'error': f'Error interno: {str(e)}'
        }, status=500)
    
@csrf_exempt
@require_http_methods(["GET"])
def obtener_comparacion_grupal(request, comparacion_grupal_id):
    """Obtener información básica de una comparación grupal y sus códigos"""
    payload = validar_token(request)
    
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido'}, status=401)
    
    try:
        # Obtener la comparación grupal con sus relaciones
        comparacion = ComparacionesGrupales.objects.select_related(
            'usuario',
            'lenguaje',
            'id_modelo_ia'
        ).get(pk=comparacion_grupal_id)
        
        # Obtener todos los códigos fuente asociados
        codigos_fuente = CodigosFuente.objects.filter(
            comparacion_grupal=comparacion
        ).order_by('orden')
        
        # Serializar códigos
        codigos_data = []
        for codigo in codigos_fuente:
            codigos_data.append({
                'id': codigo.id,
                'orden': codigo.orden,
                'nombre_archivo': codigo.nombre_archivo,
                'codigo': codigo.codigo,
                'longitud': len(codigo.codigo),
                'preview': codigo.codigo[:200] + '...' if len(codigo.codigo) > 200 else codigo.codigo
            })
        
        # Preparar respuesta
        resultado = {
            'id': comparacion.id,
            'nombre_comparacion': comparacion.nombre_comparacion,
            'estado': comparacion.estado,
            'fecha_creacion': comparacion.fecha_creacion.isoformat(),
            'usuario_id': comparacion.usuario.id if comparacion.usuario else None,
            'lenguaje': {
                'id': comparacion.lenguaje.id,
                'nombre': comparacion.lenguaje.nombre,
                'extension': comparacion.lenguaje.extension
            } if comparacion.lenguaje else None,
            'modelo_ia': {
                'id': comparacion.id_modelo_ia.id,
                'nombre': comparacion.id_modelo_ia.nombre
            } if comparacion.id_modelo_ia else None,
            'total_codigos': codigos_fuente.count(),
            'codigos': codigos_data
        }
        
        return JsonResponse(resultado, status=200)
        
    except ComparacionesGrupales.DoesNotExist:
        return JsonResponse({
            'error': f'Comparación grupal con id {comparacion_grupal_id} no encontrada'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def obtener_resultado_similitud_grupal(request, comparacion_grupal_id):
    """Obtener el resultado de análisis de similitud de una comparación grupal"""
    payload = validar_token(request)
    
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido'}, status=401)
    
    try:
        # Verificar que existe la comparación
        comparacion = ComparacionesGrupales.objects.get(pk=comparacion_grupal_id)
        
        # Obtener el resultado de similitud
        try:
            resultado_similitud = ResultadosSimilitudGrupal.objects.get(
                id_comparacion_grupal=comparacion
            )
        except ResultadosSimilitudGrupal.DoesNotExist:
            return JsonResponse({
                'mensaje': 'No se ha realizado análisis de similitud para esta comparación',
                'existe_analisis': False
            }, status=200)
        
        # Obtener las comparaciones pareadas
        comparaciones_pareadas = ComparacionesPareadas.objects.filter(
            id_resultado_similitud_grupal=resultado_similitud
        ).order_by('codigo_a_orden', 'codigo_b_orden')
        
        # Serializar comparaciones pareadas
        matriz_similitud = []
        matriz_tabla = {}
        
        for comp in comparaciones_pareadas:
            similitud_int = int(comp.porcentaje_similitud)
            
            matriz_similitud.append({
                'codigo_a': comp.codigo_a_nombre,
                'orden_a': comp.codigo_a_orden,
                'codigo_b': comp.codigo_b_nombre,
                'orden_b': comp.codigo_b_orden,
                'similitud': similitud_int,
                'nivel': comp.nivel_similitud
            })
            
            key = f"{comp.codigo_a_orden}-{comp.codigo_b_orden}"
            matriz_tabla[key] = {
                'similitud': similitud_int,
                'nivel': comp.nivel_similitud
            }
            
            key_inv = f"{comp.codigo_b_orden}-{comp.codigo_a_orden}"
            matriz_tabla[key_inv] = {
                'similitud': similitud_int,
                'nivel': comp.nivel_similitud
            }
        
        # Parsear códigos más similares
        mas_similares = []
        if resultado_similitud.codigos_mas_similares:
            lineas = resultado_similitud.codigos_mas_similares.strip().split('\n')
            for linea in lineas:
                if linea.strip():
                    mas_similares.append(linea.strip())

        # ── NUEVO: extraer codigo_base desde respuesta_completa guardada ──
        codigo_base = None
        if resultado_similitud.respuesta_completa:
            try:
                respuesta_limpia = resultado_similitud.respuesta_completa.strip()
                if '```json' in respuesta_limpia:
                    respuesta_limpia = respuesta_limpia.split('```json')[1].split('```')[0].strip()
                elif '```' in respuesta_limpia:
                    respuesta_limpia = respuesta_limpia.split('```')[1].split('```')[0].strip()
                datos_completos = json.loads(respuesta_limpia)
                codigo_base = datos_completos.get('codigo_base', None)
            except (json.JSONDecodeError, Exception):
                codigo_base = None

        # Preparar respuesta
        resultado = {
            'existe_analisis': True,
            'id_resultado': resultado_similitud.id_resultado_similitud_grupal,
            'fecha_creacion': resultado_similitud.fecha_creacion.isoformat() if resultado_similitud.fecha_creacion else None,
            'resumen_general': resultado_similitud.resumen_general,
            'codigos_mas_similares': mas_similares,
            'codigos_mas_similares_raw': resultado_similitud.codigos_mas_similares,
            'tokens_usados': resultado_similitud.tokens_usados,
            'tiempo_respuesta_segundos': float(resultado_similitud.tiempo_respuesta_segundos) if resultado_similitud.tiempo_respuesta_segundos else None,
            'matriz_similitud': matriz_similitud,
            'matriz_tabla': matriz_tabla,
            'total_comparaciones': len(matriz_similitud),
            'respuesta_completa_ia': resultado_similitud.respuesta_completa,
            # ── NUEVO: código base extraído del JSON guardado ──
            'codigo_base': codigo_base,
        }
        
        return JsonResponse(resultado, status=200)
        
    except ComparacionesGrupales.DoesNotExist:
        return JsonResponse({
            'error': f'Comparación grupal con id {comparacion_grupal_id} no encontrada'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def obtener_resultado_eficiencia_grupal(request, comparacion_grupal_id):
    """Obtener el resultado de análisis Big O de una comparación grupal"""
    payload = validar_token(request)
    
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido'}, status=401)
    
    try:
        # Verificar que existe la comparación
        comparacion = ComparacionesGrupales.objects.get(pk=comparacion_grupal_id)
        
        # Obtener el resultado de eficiencia
        try:
            resultado_eficiencia = ResultadosEficienciaGrupal.objects.get(
                id_comparacion_grupal=comparacion
            )
        except ResultadosEficienciaGrupal.DoesNotExist:
            return JsonResponse({
                'mensaje': 'No se ha realizado análisis de eficiencia para esta comparación',
                'existe_analisis': False
            }, status=200)
        
        # Obtener los detalles de cada código
        detalles = DetallesCodigoEficienciaGrupal.objects.filter(
            id_resultado_eficiencia_grupal=resultado_eficiencia
        ).select_related('id_codigo_fuente').order_by('orden')
        
        # Serializar detalles
        codigos_analizados = []
        for detalle in detalles:
            codigos_analizados.append({
                'id_detalle': detalle.id_detalle_codigo_eficiencia_grupal,
                'orden': detalle.orden,
                'nombre_archivo': detalle.id_codigo_fuente.nombre_archivo if detalle.id_codigo_fuente else None,
                'complejidad_temporal': detalle.complejidad_temporal,
                'complejidad_espacial': detalle.complejidad_espacial,
                'nivel_anidamiento': detalle.nivel_anidamiento,
                'patrones_detectados': detalle.patrones_detectados,
                'estructuras_datos': detalle.estructuras_datos,
                'confianza_analisis': detalle.confianza_analisis,
                'es_ganador': detalle.es_ganador,
                'es_empate': detalle.es_empate,
                'ranking_eficiencia': detalle.ranking_eficiencia
            })
        
        # Preparar respuesta
        resultado = {
            'existe_analisis': True,
            'id_resultado': resultado_eficiencia.id_resultado_eficiencia_grupal,
            'fecha_analisis': resultado_eficiencia.fecha_analisis.isoformat(),
            'total_codigos': resultado_eficiencia.total_codigos,
            'ganador': resultado_eficiencia.ganador,
            'tipo_ganador': resultado_eficiencia.tipo_ganador,
            'complejidad_temporal_mejor': resultado_eficiencia.complejidad_temporal_mejor,
            'complejidad_temporal_peor': resultado_eficiencia.complejidad_temporal_peor,
            'nivel_anidamiento_maximo': resultado_eficiencia.nivel_anidamiento_maximo,
            'nivel_anidamiento_minimo': resultado_eficiencia.nivel_anidamiento_minimo,
            'confianza_analisis_general': resultado_eficiencia.confianza_analisis_general,
            'codigos_analizados': codigos_analizados
        }
        
        return JsonResponse(resultado, status=200)
        
    except ComparacionesGrupales.DoesNotExist:
        return JsonResponse({
            'error': f'Comparación grupal con id {comparacion_grupal_id} no encontrada'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def obtener_comentarios_eficiencia_grupal(request, comparacion_grupal_id):
    """Obtener los comentarios de IA sobre eficiencia de una comparación grupal"""
    payload = validar_token(request)
    
    if not payload or 'error' in payload:
        return JsonResponse({'error': 'Token inválido'}, status=401)
    
    try:
        # Verificar que existe la comparación
        comparacion = ComparacionesGrupales.objects.get(pk=comparacion_grupal_id)
        
        # Obtener el resultado de eficiencia primero
        try:
            resultado_eficiencia = ResultadosEficienciaGrupal.objects.get(
                id_comparacion_grupal=comparacion
            )
        except ResultadosEficienciaGrupal.DoesNotExist:
            return JsonResponse({
                'mensaje': 'No se ha realizado análisis de eficiencia para esta comparación',
                'existe_analisis': False,
                'existe_comentarios': False
            }, status=200)
        
        # Obtener el comentario grupal
        try:
            comentario_grupal = ComentariosIaGrupal.objects.select_related(
                'id_prompt_eficiencia'
            ).get(
                id_resultado_eficiencia_grupal=resultado_eficiencia
            )
        except ComentariosIaGrupal.DoesNotExist:
            return JsonResponse({
                'mensaje': 'No se han generado comentarios de IA para esta comparación',
                'existe_analisis': True,
                'existe_comentarios': False
            }, status=200)
        
        # Obtener los comentarios individuales de cada código
        comentarios_individuales = ComentariosCodigoGrupal.objects.filter(
            id_comentario_grupal=comentario_grupal
        ).select_related(
            'id_codigo_fuente',
            'id_detalle_codigo_eficiencia_grupal'
        ).order_by('orden')
        
        # Serializar comentarios individuales
        comentarios_data = []
        for comentario in comentarios_individuales:
            comentarios_data.append({
                'id': comentario.id_comentario_codigo_grupal,
                'orden': comentario.orden,
                'nombre_archivo': comentario.nombre_archivo,
                'comentario_general': comentario.comentario_general,
                'puntos_fuertes': comentario.puntos_fuertes,
                'puntos_debiles': comentario.puntos_debiles,
                'recomendaciones': comentario.recomendaciones,
                'nota_eficiencia': float(comentario.nota_eficiencia) if comentario.nota_eficiencia else None
            })
        
        # Preparar respuesta
        resultado = {
            'existe_analisis': True,
            'existe_comentarios': True,
            'id_comentario_grupal': comentario_grupal.id_comentario_grupal,
            'fecha_analisis': comentario_grupal.fecha_analisis.isoformat() if comentario_grupal.fecha_analisis else None,
            'prompt_usado': {
                'id': comentario_grupal.id_prompt_eficiencia.id_prompt_eficiencia,
                'version': comentario_grupal.id_prompt_eficiencia.version,
                'descripcion': comentario_grupal.id_prompt_eficiencia.descripcion,
                'tipo_analisis': comentario_grupal.id_prompt_eficiencia.tipo_analisis
            } if comentario_grupal.id_prompt_eficiencia else None,
            'analisis_comparativo': {
                'resumen_comparativo': comentario_grupal.resumen_comparativo,
                'mejor_codigo': {
                    'orden': comentario_grupal.mejor_codigo_orden,
                    'razon': comentario_grupal.mejor_codigo_razon
                },
                'peor_codigo': {
                    'orden': comentario_grupal.peor_codigo_orden,
                    'razon': comentario_grupal.peor_codigo_razon
                }
            },
            'patrones': {
                'eficientes': comentario_grupal.patrones_eficientes,
                'ineficientes': comentario_grupal.patrones_ineficientes
            },
            'recomendaciones_generales': comentario_grupal.recomendaciones_generales,
            'ranking_ia': comentario_grupal.ranking_ia,
            'comentarios_individuales': comentarios_data,
            'total_comentarios': len(comentarios_data),
            'respuesta_completa_ia': comentario_grupal.respuesta_completa_ia
        }
        
        return JsonResponse(resultado, status=200)
        
    except ComparacionesGrupales.DoesNotExist:
        return JsonResponse({
            'error': f'Comparación grupal con id {comparacion_grupal_id} no encontrada'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)