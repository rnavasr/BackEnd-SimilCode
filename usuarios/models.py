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

class DatosPersonales(models.Model):
    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    email = models.CharField(unique=True, max_length=150, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    institucion = models.CharField(max_length=200)
    ci = models.CharField(max_length=10, blank=True, null=True)
    facultad_area = models.CharField(max_length=150, blank=True, null=True)
    fecha_registro = models.DateTimeField(blank=True, null=True)
    estado = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'datos_personales'  
        app_label = 'app'   

class Lenguajes(models.Model):
    nombre = models.CharField(unique=True, max_length=50)
    extension = models.CharField(max_length=10, blank=True, null=True)
    usuario = models.ForeignKey('Usuarios', models.DO_NOTHING, db_column='id_usuario', blank=True, null=True)
    estado = models.BooleanField(default=True)
    
    class Meta:
        managed = False
        db_table = 'lenguajes'
        app_label = 'app'

class ModelosIa(models.Model):
    nombre = models.CharField(unique=True, max_length=100)
    version = models.CharField(max_length=50, blank=True, null=True)
    proveedor = models.ForeignKey('ProveedoresIa', models.DO_NOTHING, blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
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

class PromptComparacion(models.Model):
    id_prompt = models.AutoField(primary_key=True)
    template_prompt = models.TextField()
    descripcion = models.TextField(blank=True, null=True)
    version = models.CharField(max_length=20, blank=True, null=True)
    activo = models.BooleanField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(blank=True, null=True)
    fecha_modificacion = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'prompt_comparacion'
        app_label = 'app'

class ConfiguracionClaude(models.Model):
    id_config_claude = models.AutoField(primary_key=True)
    id_modelo_ia = models.OneToOneField('ModelosIa', models.DO_NOTHING, db_column='id_modelo_ia')
    id_prompt = models.ForeignKey('PromptComparacion', models.DO_NOTHING, db_column='id_prompt')
    endpoint_url = models.CharField(max_length=500)
    api_key = models.CharField(max_length=500)
    model_name = models.CharField(max_length=100)
    max_tokens = models.IntegerField(blank=True, null=True)
    anthropic_version = models.CharField(max_length=20, blank=True, null=True)
    activo = models.BooleanField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(blank=True, null=True)
    fecha_modificacion = models.DateTimeField(blank=True, null=True)
    id_prompt_eficiencia = models.ForeignKey('PromptEficienciaAlgoritmica', models.DO_NOTHING, db_column='id_prompt_eficiencia', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'configuracion_claude'
        app_label = 'app'

class ConfiguracionDeepseek(models.Model):
    id_config_deepseek = models.AutoField(primary_key=True)
    id_modelo_ia = models.OneToOneField('ModelosIa', models.DO_NOTHING, db_column='id_modelo_ia')
    id_prompt = models.ForeignKey('PromptComparacion', models.DO_NOTHING, db_column='id_prompt')
    endpoint_url = models.CharField(max_length=500)
    api_key = models.CharField(max_length=500)
    model_name = models.CharField(max_length=100)
    max_tokens = models.IntegerField(blank=True, null=True)
    temperature = models.DecimalField(max_digits=3, decimal_places=2, blank=True, null=True)
    activo = models.BooleanField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(blank=True, null=True)
    fecha_modificacion = models.DateTimeField(blank=True, null=True)
    id_prompt_eficiencia = models.ForeignKey('PromptEficienciaAlgoritmica', models.DO_NOTHING, db_column='id_prompt_eficiencia', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'configuracion_deepseek'
        app_label = 'app'

class ConfiguracionGemini(models.Model):
    id_config_gemini = models.AutoField(primary_key=True)
    id_modelo_ia = models.OneToOneField('ModelosIa', models.DO_NOTHING, db_column='id_modelo_ia')
    id_prompt = models.ForeignKey('PromptComparacion', models.DO_NOTHING, db_column='id_prompt')
    endpoint_url = models.CharField(max_length=500)
    api_key = models.CharField(max_length=500)
    model_name = models.CharField(max_length=100)
    max_tokens = models.IntegerField(blank=True, null=True)
    temperature = models.DecimalField(max_digits=3, decimal_places=2, blank=True, null=True)
    activo = models.BooleanField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(blank=True, null=True)
    fecha_modificacion = models.DateTimeField(blank=True, null=True)
    id_prompt_eficiencia = models.ForeignKey('PromptEficienciaAlgoritmica', models.DO_NOTHING, db_column='id_prompt_eficiencia', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'configuracion_gemini'
        app_label = 'app'

class ConfiguracionOpenai(models.Model):
    id_config_openai = models.AutoField(primary_key=True)
    id_modelo_ia = models.OneToOneField('ModelosIa', models.DO_NOTHING, db_column='id_modelo_ia')
    id_prompt = models.ForeignKey('PromptComparacion', models.DO_NOTHING, db_column='id_prompt')
    endpoint_url = models.CharField(max_length=500)
    api_key = models.CharField(max_length=500)
    model_name = models.CharField(max_length=100)
    max_tokens = models.IntegerField(blank=True, null=True)
    temperature = models.DecimalField(max_digits=3, decimal_places=2, blank=True, null=True)
    activo = models.BooleanField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(blank=True, null=True)
    fecha_modificacion = models.DateTimeField(blank=True, null=True)
    id_prompt_eficiencia = models.ForeignKey('PromptEficienciaAlgoritmica', models.DO_NOTHING, db_column='id_prompt_eficiencia', blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'configuracion_openai'
        app_label = 'app'

class ComentariosEficienciaIndividual(models.Model):
    id_comentario_eficiencia = models.AutoField(primary_key=True)
    id_resultado_eficiencia_individual = models.ForeignKey('ResultadosEficienciaIndividual', models.DO_NOTHING, db_column='id_resultado_eficiencia_individual')
    comentario = models.TextField()
    fecha_generacion = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'comentarios_eficiencia_individual'
        app_label = 'app'

class PromptEficienciaAlgoritmica(models.Model):
    id_prompt_eficiencia = models.AutoField(primary_key=True)
    template_prompt = models.TextField()
    descripcion = models.TextField(blank=True, null=True)
    version = models.CharField(max_length=20, blank=True, null=True)
    tipo_analisis = models.CharField(max_length=50, blank=True, null=True)
    activo = models.BooleanField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(blank=True, null=True)
    fecha_modificacion = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'prompt_eficiencia_algoritmica'
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
    id_resultado_eficiencia_individual = models.AutoField(primary_key=True)
    id_comparacion_individual = models.ForeignKey(ComparacionesIndividuales, models.DO_NOTHING, db_column='id_comparacion_individual')
    codigo_1_complejidad_temporal = models.CharField(max_length=50)
    codigo_1_complejidad_espacial = models.CharField(max_length=50)
    codigo_1_nivel_anidamiento = models.IntegerField(blank=True, null=True)
    codigo_1_patrones_detectados = models.JSONField(blank=True, null=True)
    codigo_1_estructuras_datos = models.JSONField(blank=True, null=True)
    codigo_1_confianza_analisis = models.CharField(max_length=50, blank=True, null=True)
    codigo_2_complejidad_temporal = models.CharField(max_length=50)
    codigo_2_complejidad_espacial = models.CharField(max_length=50)
    codigo_2_nivel_anidamiento = models.IntegerField(blank=True, null=True)
    codigo_2_patrones_detectados = models.JSONField(blank=True, null=True)
    codigo_2_estructuras_datos = models.JSONField(blank=True, null=True)
    codigo_2_confianza_analisis = models.CharField(max_length=50, blank=True, null=True)
    ganador = models.CharField(max_length=20, blank=True, null=True)
    lenguaje = models.CharField(max_length=50, blank=True, null=True)
    lenguaje_analizado = models.CharField(max_length=50, blank=True, null=True)
    fecha_analisis = models.DateTimeField(blank=True, null=True)

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
    id_resultado_similitud_individual = models.AutoField(primary_key=True)
    id_comparacion_individual = models.ForeignKey(ComparacionesIndividuales, models.DO_NOTHING, db_column='id_comparacion_individual')
    porcentaje_similitud = models.IntegerField()
    explicacion = models.TextField(blank=True, null=True)

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