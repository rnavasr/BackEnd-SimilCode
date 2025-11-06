# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class CodigosFuente(models.Model):
    comparacion_grupal = models.ForeignKey('ComparacionesGrupales', models.DO_NOTHING)
    codigo = models.TextField()
    nombre_archivo = models.CharField(max_length=200, blank=True, null=True)
    orden = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'codigos_fuente'
        app_label = 'app'

class ComparacionesGrupales(models.Model):
    usuario = models.ForeignKey('Usuarios', models.DO_NOTHING)
    lenguaje = models.ForeignKey('Lenguajes', models.DO_NOTHING)
    nombre_comparacion = models.CharField(max_length=200, blank=True, null=True)
    fecha_creacion = models.DateTimeField(blank=True, null=True)
    estado = models.CharField(max_length=20, blank=True, null=True)
    id_modelo_ia = models.ForeignKey('ModelosIa', models.DO_NOTHING, db_column='id_modelo_ia', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'comparaciones_grupales'
        app_label = 'app'

class ComparacionesIndividuales(models.Model):
    usuario = models.ForeignKey('Usuarios', models.DO_NOTHING)
    lenguaje = models.ForeignKey('Lenguajes', models.DO_NOTHING)
    nombre_comparacion = models.CharField(max_length=200, blank=True, null=True)
    codigo_1 = models.TextField()
    codigo_2 = models.TextField()
    fecha_creacion = models.DateTimeField(blank=True, null=True)
    estado = models.CharField(max_length=20, blank=True, null=True)
    id_modelo_ia = models.ForeignKey('ModelosIa', models.DO_NOTHING, db_column='id_modelo_ia', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'comparaciones_individuales'
        app_label = 'app'

class ConfiguracionApi(models.Model):
    modelo_ia = models.OneToOneField('ModelosIa', models.DO_NOTHING)
    metodo_http = models.CharField(max_length=10, blank=True, null=True)
    path_endpoint = models.CharField(max_length=255, blank=True, null=True)
    formato_request = models.JSONField()
    formato_response = models.JSONField()
    timeout_segundos = models.IntegerField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'configuracion_api'
        app_label = 'app'

class CredencialesApi(models.Model):
    modelo_ia = models.OneToOneField('ModelosIa', models.DO_NOTHING)
    api_key_encrypted = models.BinaryField()
    api_secret_encrypted = models.BinaryField(blank=True, null=True)
    headers_auth = models.JSONField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(blank=True, null=True)
    ultima_rotacion = models.DateTimeField(blank=True, null=True)
    expira_en = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'credenciales_api'
        app_label = 'app'

class DatosPersonales(models.Model):
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    email = models.CharField(unique=True, max_length=150, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    institucion = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'datos_personales'
        app_label = 'app'        

class Lenguajes(models.Model):
    nombre = models.CharField(unique=True, max_length=50)
    extension = models.CharField(max_length=10, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'lenguajes'
        app_label = 'app'

class ModelosIa(models.Model):
    nombre = models.CharField(unique=True, max_length=100)
    version = models.CharField(max_length=50, blank=True, null=True)
    proveedor = models.ForeignKey('ProveedoresIa', models.DO_NOTHING, blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    endpoint_api = models.CharField(max_length=255)
    tipo_autenticacion = models.CharField(max_length=50, blank=True, null=True)
    headers_adicionales = models.JSONField(blank=True, null=True)
    parametros_default = models.JSONField(blank=True, null=True)
    limite_tokens = models.IntegerField(blank=True, null=True)
    soporta_streaming = models.BooleanField(blank=True, null=True)
    activo = models.BooleanField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(blank=True, null=True)
    recomendado = models.BooleanField(blank=True, null=True)
    imagen_ia = models.BinaryField(blank=True, null=True)
    color_ia = models.CharField(max_length=7, blank=True, null=True)
    id_usuario = models.ForeignKey('Usuarios', models.DO_NOTHING, db_column='id_usuario', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'modelos_ia'
        app_label = 'app'

class ProveedoresIa(models.Model):
    nombre = models.CharField(unique=True, max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    logo_url = models.CharField(max_length=255, blank=True, null=True)
    sitio_web = models.CharField(max_length=255, blank=True, null=True)
    activo = models.BooleanField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'proveedores_ia'
        app_label = 'app'

class PruebasModelos(models.Model):
    modelo_ia = models.ForeignKey(ModelosIa, models.DO_NOTHING)
    usuario = models.ForeignKey('Usuarios', models.DO_NOTHING)
    precision = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    tiempo_respuesta_ms = models.IntegerField(blank=True, null=True)
    efectividad = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    fecha_prueba = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'pruebas_modelos'
        app_label = 'app'

class ResultadosEficienciaGrupal(models.Model):
    comparacion_grupal = models.ForeignKey(ComparacionesGrupales, models.DO_NOTHING)
    codigo_fuente = models.ForeignKey(CodigosFuente, models.DO_NOTHING)
    complejidad_temporal = models.CharField(max_length=50, blank=True, null=True)
    complejidad_espacial = models.CharField(max_length=50, blank=True, null=True)
    puntuacion_eficiencia = models.IntegerField(blank=True, null=True)
    es_mas_eficiente = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'resultados_eficiencia_grupal'
        app_label = 'app'

class ResultadosEficienciaIndividual(models.Model):
    comparacion_individual = models.ForeignKey(ComparacionesIndividuales, models.DO_NOTHING)
    numero_codigo = models.IntegerField(blank=True, null=True)
    complejidad_temporal = models.CharField(max_length=50, blank=True, null=True)
    complejidad_espacial = models.CharField(max_length=50, blank=True, null=True)
    puntuacion_eficiencia = models.IntegerField(blank=True, null=True)
    es_mas_eficiente = models.BooleanField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'resultados_eficiencia_individual'
        app_label = 'app'

class ResultadosSimilitudGrupal(models.Model):
    comparacion_grupal = models.ForeignKey(ComparacionesGrupales, models.DO_NOTHING)
    codigo_fuente_1 = models.ForeignKey(CodigosFuente, models.DO_NOTHING)
    codigo_fuente_2 = models.ForeignKey(CodigosFuente, models.DO_NOTHING, related_name='resultadossimilitudgrupal_codigo_fuente_2_set')
    porcentaje_similitud = models.DecimalField(max_digits=5, decimal_places=2)
    explicacion = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'resultados_similitud_grupal'
        app_label = 'app'

class ResultadosSimilitudIndividual(models.Model):
    comparacion_individual = models.ForeignKey(ComparacionesIndividuales, models.DO_NOTHING)
    porcentaje_similitud = models.DecimalField(max_digits=5, decimal_places=2)
    explicacion = models.TextField(blank=True, null=True)
    probabilidad_similitud = models.CharField(max_length=10, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'resultados_similitud_individual'
        app_label = 'app'

class Roles(models.Model):
    nombre = models.CharField(unique=True, max_length=50)
    descripcion = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'roles'
        app_label = 'app'

class UsoApis(models.Model):
    modelo_ia = models.ForeignKey(ModelosIa, models.DO_NOTHING, blank=True, null=True)
    usuario = models.ForeignKey('Usuarios', models.DO_NOTHING, blank=True, null=True)
    tokens_consumidos = models.IntegerField(blank=True, null=True)
    tiempo_respuesta_ms = models.IntegerField(blank=True, null=True)
    costo = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    exitoso = models.BooleanField(blank=True, null=True)
    mensaje_error = models.TextField(blank=True, null=True)
    fecha_uso = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'uso_apis'
        app_label = 'app'

class Usuarios(models.Model):
    usuario = models.CharField(unique=True, max_length=50)
    contrasenia = models.CharField(max_length=255)
    datos_personales = models.ForeignKey(DatosPersonales, models.DO_NOTHING)
    rol = models.ForeignKey(Roles, models.DO_NOTHING)
    activo = models.BooleanField(blank=True, null=True)
    fecha_registro = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'usuarios'
        app_label = 'app'        