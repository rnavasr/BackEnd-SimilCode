from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.hashers import make_password, check_password
from django.db import transaction
from datetime import datetime, timedelta
import jwt,json,base64
from django.conf import settings
from usuarios.models import *
from models import ComparacionesGrupales, ComparacionesIndividuales, Lenguajes, ModelosIa, ProveedoresIa
from django.utils import timezone

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
        codigo_1 = request.POST.get('codigo_1')
        codigo_2 = request.POST.get('codigo_2')
        estado = request.POST.get('estado', 'Reciente')
        
        # Validaciones
        if not all([usuario_id, modelo_ia_id, lenguaje_id, codigo_1, codigo_2]):
            return JsonResponse({
                'error': 'Faltan campos requeridos: usuario_id, modelo_ia_id, lenguaje_id, codigo_1, codigo_2'
            }, status=400)
        
        # Crear la comparación individual
        comparacion = ComparacionesIndividuales.objects.create(
            usuario_id=usuario_id,
            modelo_ia_id=modelo_ia_id,
            lenguaje_id=lenguaje_id,
            nombre_comparacion=nombre_comparacion,
            codigo_1=codigo_1,
            codigo_2=codigo_2,
            estado=estado,
            fecha_creacion=timezone.now()
        )
        
        return JsonResponse({
            'mensaje': 'Comparación individual creada exitosamente',
            'id': comparacion.id,
            'nombre_comparacion': comparacion.nombre_comparacion,
            'fecha_creacion': comparacion.fecha_creacion
        }, status=201)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


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