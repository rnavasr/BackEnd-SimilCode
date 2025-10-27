-- ============================================
-- BASE DE DATOS: Sistema de Comparación de Código con IA
-- ============================================

-- Habilitar extensión para encriptación
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ============================================
-- TABLAS DE CONFIGURACIÓN GENERAL
-- ============================================

-- Tabla de roles
CREATE TABLE roles (
    id_rol SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    descripcion TEXT
);

-- Tabla de datos personales para docentes
CREATE TABLE datos_personales (
    id_datos_personales SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    telefono VARCHAR(20),
    institucion VARCHAR(200)
);

-- Tabla de usuarios
CREATE TABLE usuarios (
    id_usuario SERIAL PRIMARY KEY,
    usuario VARCHAR(50) NOT NULL UNIQUE,
    contrasenia VARCHAR(255) NOT NULL,
    id_datos_personales INTEGER NOT NULL REFERENCES datos_personales(id_datos_personales) ON DELETE CASCADE,
    id_rol INTEGER NOT NULL REFERENCES roles(id_rol),
    activo BOOLEAN DEFAULT true,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- TABLAS DE PROVEEDORES Y MODELOS DE IA
-- ============================================

-- Tabla de proveedores de IA
CREATE TABLE proveedores_ia (
    id_proveedor SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    descripcion TEXT,
    logo_url VARCHAR(255),
    sitio_web VARCHAR(255),
    activo BOOLEAN DEFAULT true,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de modelos de IA (mejorada)
CREATE TABLE modelos_ia (
    id_modelo_ia SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    version VARCHAR(50),
    id_proveedor INTEGER REFERENCES proveedores_ia(id_proveedor),
    descripcion TEXT,
    endpoint_api VARCHAR(255) NOT NULL,
    tipo_autenticacion VARCHAR(50) DEFAULT 'api_key',
    headers_adicionales JSONB,
    parametros_default JSONB,
    limite_tokens INTEGER,
    soporta_streaming BOOLEAN DEFAULT false,
    activo BOOLEAN DEFAULT true,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de credenciales encriptadas
CREATE TABLE credenciales_api (
    id_credencial SERIAL PRIMARY KEY,
    id_modelo_ia INTEGER UNIQUE NOT NULL REFERENCES modelos_ia(id_modelo_ia) ON DELETE CASCADE,
    api_key_encrypted BYTEA NOT NULL,
    api_secret_encrypted BYTEA,
    headers_auth JSONB,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ultima_rotacion TIMESTAMP,
    expira_en TIMESTAMP,
    CONSTRAINT check_expiration CHECK (expira_en IS NULL OR expira_en > CURRENT_TIMESTAMP)
);

-- Tabla de configuración de API (estructura de request/response)
CREATE TABLE configuracion_api (
    id_config SERIAL PRIMARY KEY,
    id_modelo_ia INTEGER UNIQUE NOT NULL REFERENCES modelos_ia(id_modelo_ia) ON DELETE CASCADE,
    metodo_http VARCHAR(10) DEFAULT 'POST',
    path_endpoint VARCHAR(255),
    formato_request JSONB NOT NULL,
    formato_response JSONB NOT NULL,
    timeout_segundos INTEGER DEFAULT 30
);

-- Tabla de historial de uso de APIs
CREATE TABLE uso_apis (
    id_uso SERIAL PRIMARY KEY,
    id_modelo_ia INTEGER REFERENCES modelos_ia(id_modelo_ia),
    id_usuario INTEGER REFERENCES usuarios(id_usuario),
    tokens_consumidos INTEGER,
    tiempo_respuesta_ms INTEGER,
    costo DECIMAL(10, 4),
    exitoso BOOLEAN,
    mensaje_error TEXT,
    fecha_uso TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- TABLAS DE LENGUAJES Y COMPARACIONES
-- ============================================

-- Tabla de lenguajes de programación
CREATE TABLE lenguajes (
    id_lenguaje SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    extension VARCHAR(10)
);

-- Tabla de comparaciones individuales (2 códigos)
CREATE TABLE comparaciones_individuales (
    id_comparacion_individual SERIAL PRIMARY KEY,
    id_usuario INTEGER NOT NULL REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    id_modelo_ia INTEGER NOT NULL REFERENCES modelos_ia(id_modelo_ia),
    id_lenguaje INTEGER NOT NULL REFERENCES lenguajes(id_lenguaje),
    nombre_comparacion VARCHAR(200),
    codigo_1 TEXT NOT NULL,
    codigo_2 TEXT NOT NULL,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de comparaciones grupales (múltiples códigos)
CREATE TABLE comparaciones_grupales (
    id_comparacion_grupal SERIAL PRIMARY KEY,
    id_usuario INTEGER NOT NULL REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    id_modelo_ia INTEGER NOT NULL REFERENCES modelos_ia(id_modelo_ia),
    id_lenguaje INTEGER NOT NULL REFERENCES lenguajes(id_lenguaje),
    nombre_comparacion VARCHAR(200),
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de códigos fuente para comparaciones grupales
CREATE TABLE codigos_fuente (
    id_codigo_fuente SERIAL PRIMARY KEY,
    id_comparacion_grupal INTEGER NOT NULL REFERENCES comparaciones_grupales(id_comparacion_grupal) ON DELETE CASCADE,
    codigo TEXT NOT NULL,
    nombre_archivo VARCHAR(200),
    orden INTEGER
);

-- ============================================
-- TABLAS DE RESULTADOS
-- ============================================

-- Tabla de resultados de similitud para comparaciones individuales
CREATE TABLE resultados_similitud_individual (
    id_resultado_similitud_individual SERIAL PRIMARY KEY,
    id_comparacion_individual INTEGER NOT NULL REFERENCES comparaciones_individuales(id_comparacion_individual) ON DELETE CASCADE,
    porcentaje_similitud DECIMAL(5, 2) NOT NULL,
    explicacion TEXT,
    probabilidad_similitud VARCHAR(10) CHECK (probabilidad_similitud IN ('bajo', 'medio', 'alto'))
);

-- Tabla de resultados de similitud para comparaciones grupales
CREATE TABLE resultados_similitud_grupal (
    id_resultado_similitud_grupal SERIAL PRIMARY KEY,
    id_comparacion_grupal INTEGER NOT NULL REFERENCES comparaciones_grupales(id_comparacion_grupal) ON DELETE CASCADE,
    id_codigo_fuente_1 INTEGER NOT NULL REFERENCES codigos_fuente(id_codigo_fuente) ON DELETE CASCADE,
    id_codigo_fuente_2 INTEGER NOT NULL REFERENCES codigos_fuente(id_codigo_fuente) ON DELETE CASCADE,
    porcentaje_similitud DECIMAL(5, 2) NOT NULL,
    explicacion TEXT
);

-- Tabla de resultados de eficiencia para comparaciones individuales
CREATE TABLE resultados_eficiencia_individual (
    id_resultado_eficiencia_individual SERIAL PRIMARY KEY,
    id_comparacion_individual INTEGER NOT NULL REFERENCES comparaciones_individuales(id_comparacion_individual) ON DELETE CASCADE,
    numero_codigo INTEGER CHECK (numero_codigo IN (1, 2)),
    complejidad_temporal VARCHAR(50),
    complejidad_espacial VARCHAR(50),
    puntuacion_eficiencia INTEGER CHECK (puntuacion_eficiencia >= 0 AND puntuacion_eficiencia <= 100),
    es_mas_eficiente BOOLEAN
);

-- Tabla de resultados de eficiencia para comparaciones grupales
CREATE TABLE resultados_eficiencia_grupal (
    id_resultado_eficiencia_grupal SERIAL PRIMARY KEY,
    id_comparacion_grupal INTEGER NOT NULL REFERENCES comparaciones_grupales(id_comparacion_grupal) ON DELETE CASCADE,
    id_codigo_fuente INTEGER NOT NULL REFERENCES codigos_fuente(id_codigo_fuente) ON DELETE CASCADE,
    complejidad_temporal VARCHAR(50),
    complejidad_espacial VARCHAR(50),
    puntuacion_eficiencia INTEGER CHECK (puntuacion_eficiencia >= 0 AND puntuacion_eficiencia <= 100),
    es_mas_eficiente BOOLEAN
);

-- Tabla de pruebas de modelos (para objetivo específico 1)
CREATE TABLE pruebas_modelos (
    id_prueba_modelo SERIAL PRIMARY KEY,
    id_modelo_ia INTEGER NOT NULL REFERENCES modelos_ia(id_modelo_ia),
    id_usuario INTEGER NOT NULL REFERENCES usuarios(id_usuario),
    precision DECIMAL(5, 2),
    tiempo_respuesta_ms INTEGER,
    efectividad DECIMAL(5, 2),
    observaciones TEXT,
    fecha_prueba TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- FUNCIONES DE ENCRIPTACIÓN
-- ============================================

-- Función para encriptar API key
CREATE OR REPLACE FUNCTION encriptar_api_key(
    p_api_key TEXT,
    p_key_password TEXT
) RETURNS BYTEA AS $$
BEGIN
    RETURN pgp_sym_encrypt(p_api_key, p_key_password);
END;
$$ LANGUAGE plpgsql;

-- Función para desencriptar API key
CREATE OR REPLACE FUNCTION desencriptar_api_key(
    p_api_key_encrypted BYTEA,
    p_key_password TEXT
) RETURNS TEXT AS $$
BEGIN
    RETURN pgp_sym_decrypt(p_api_key_encrypted, p_key_password);
END;
$$ LANGUAGE plpgsql;

-- Insertar algunos roles básicos
INSERT INTO roles (nombre, descripcion) VALUES 
('admin', 'Administrador del sistema'),
('usuario', 'Usuario regular')


-- Si tienen tablas en postgres y quieren traerlas al backend, pueden usar el siguiente comando:
python manage.py inspectdb > models.py


-- Crear un archivo de requerimientos para el proyecto
pip freeze > requirements.txt   