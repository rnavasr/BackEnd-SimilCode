from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.hashers import make_password, check_password
from django.db import transaction
from datetime import datetime, timedelta
import jwt,json,base64,os
from django.conf import settings
from usuarios.models import *
from usuarios.models import ComparacionesGrupales, ComparacionesIndividuales, Lenguajes, ModelosIa, ProveedoresIa,ConfiguracionApi, PromptComparacion
from django.utils import timezone
from django.db.models import Q
import requests
import json
import time

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
            'nombre': usuario.datos_personales.nombre,
            'apellido': usuario.datos_personales.apellido,
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
    """Crear una nueva comparación grupal"""
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
        
        # Validaciones
        if not all([usuario_id, modelo_ia_id, lenguaje_id]):
            return JsonResponse({
                'error': 'Faltan campos requeridos: usuario_id, modelo_ia_id, lenguaje_id'
            }, status=400)
        
        # Crear la comparación grupal
        comparacion = ComparacionesGrupales.objects.create(
            usuario_id=usuario_id,
            modelo_ia_id=modelo_ia_id,
            lenguaje_id=lenguaje_id,
            nombre_comparacion=nombre_comparacion,
            estado=estado,
            fecha_creacion=timezone.now()
        )
        
        return JsonResponse({
            'mensaje': 'Comparación grupal creada exitosamente',
            'id': comparacion.id,
            'nombre_comparacion': comparacion.nombre_comparacion,
            'fecha_creacion': comparacion.fecha_creacion
        }, status=201)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

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
def probar_comparacion_ia(request):
    try:
        # Obtener el ID de la comparación
        data = json.loads(request.body)
        id_comparacion = data.get('id_comparacion')
        
        if not id_comparacion:
            return JsonResponse({
                'error': 'Se requiere id_comparacion'
            }, status=400)
        
        # 1. Obtener la comparación
        try:
            comparacion = ComparacionesIndividuales.objects.get(
                id=id_comparacion
            )
        except ComparacionesIndividuales.DoesNotExist:
            return JsonResponse({
                'error': f'Comparación {id_comparacion} no encontrada'
            }, status=404)
        
        # 2. Obtener el modelo IA
        if not comparacion.id_modelo_ia:
            return JsonResponse({
                'error': 'La comparación no tiene un modelo de IA asignado'
            }, status=400)
        
        modelo_ia = comparacion.id_modelo_ia
        
        # 3. Obtener la configuración de API del modelo
        try:
            config_api = ConfiguracionApi.objects.get(
                id_modelo_ia_id=modelo_ia.id
            )
        except ConfiguracionApi.DoesNotExist:
            return JsonResponse({
                'error': 'No hay configuración de API para este modelo'
            }, status=404)
        
        # 4. Obtener el prompt
        try:
            prompt_config = PromptComparacion.objects.get(
                id_config_id=config_api.id_config
            )
        except PromptComparacion.DoesNotExist:
            return JsonResponse({
                'error': 'No hay prompt configurado para este modelo'
            }, status=404)
        
        # 5. Reemplazar placeholders en el prompt
        prompt_procesado = prompt_config.template_prompt.replace(
            '{{codigo_a}}', comparacion.codigo_1
        ).replace(
            '{{codigo_b}}', comparacion.codigo_2
        )
        
        # 6. Detectar si es OpenAI o Anthropic según la URL
        es_anthropic = 'anthropic.com' in config_api.endpoint_url.lower()
        es_openai = 'openai.com' in config_api.endpoint_url.lower()
        
        # 7. Preparar headers y payload según el proveedor
        if es_anthropic:
            # Para Claude/Anthropic
            headers = {
                'Content-Type': 'application/json',
                'x-api-key': config_api.api_key,
                'anthropic-version': '2023-06-01'
            }
            
            payload = {
                'model': 'claude-3-haiku-20240307',
                'max_tokens': 4000,
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt_procesado
                    }
                ]
            }
            
        elif es_openai:
            # Para OpenAI/ChatGPT
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {config_api.api_key}'
            }
            
            payload = {
                'model': 'gpt-3.5-turbo',
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt_procesado
                    }
                ],
                'max_tokens': 4000,
                'temperature': 0.7
            }
        else:
            return JsonResponse({
                'error': 'Proveedor de IA no soportado'
            }, status=400)
        
        # 8. Hacer la petición
        inicio = time.time()
        
        response = requests.post(
            config_api.endpoint_url,
            headers=headers,
            json=payload,
            timeout=60
        )
        
        tiempo_respuesta = time.time() - inicio
        
        # 9. Verificar respuesta
        if response.status_code != 200:
            return JsonResponse({
                'error': f'Error de la API: {response.status_code}',
                'detalle': response.text
            }, status=response.status_code)
        
        # 10. Extraer la respuesta según el proveedor
        response_data = response.json()
        
        if es_anthropic:
            # Respuesta de Claude
            respuesta_ia = response_data['content'][0]['text']
            tokens_usados = (
                response_data.get('usage', {}).get('input_tokens', 0) + 
                response_data.get('usage', {}).get('output_tokens', 0)
            )
            
        elif es_openai:
            # Respuesta de OpenAI
            respuesta_ia = response_data['choices'][0]['message']['content']
            tokens_usados = response_data.get('usage', {}).get('total_tokens', 0)
        
        # 11. Retornar resultado (solo para prueba, NO guardamos aún)
        return JsonResponse({
            'mensaje': 'Comparación exitosa',
            'comparacion_id': id_comparacion,
            'modelo_usado': modelo_ia.nombre,
            'proveedor': 'Anthropic' if es_anthropic else 'OpenAI',
            'tiempo_respuesta_segundos': round(tiempo_respuesta, 2),
            'tokens_usados': tokens_usados,
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