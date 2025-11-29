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

CREATE TABLE modelos_ia (
    id_modelo_ia SERIAL PRIMARY KEY,
    id_proveedor INTEGER REFERENCES proveedores_ia(id_proveedor),
    id_usuario INTEGER NOT NULL REFERENCES usuarios(id),
    nombre VARCHAR(100) NOT NULL,
    version VARCHAR(50),
    descripcion TEXT,
    color_ia VARCHAR(7),
    imagen_ia BYTEA,
    activo BOOLEAN DEFAULT true,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    recomendado BOOLEAN DEFAULT false
);

CREATE TABLE prompt_comparacion (
    id_prompt SERIAL PRIMARY KEY,
    template_prompt TEXT NOT NULL,
    descripcion TEXT,
    version VARCHAR(20),
    activo BOOLEAN DEFAULT true,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE configuracion_claude (
    id_config_claude SERIAL PRIMARY KEY,
    id_modelo_ia INTEGER UNIQUE NOT NULL REFERENCES modelos_ia(id_modelo_ia) ON DELETE CASCADE,
    id_prompt INTEGER NOT NULL REFERENCES prompt_comparacion(id_prompt) ON DELETE RESTRICT,
    endpoint_url VARCHAR(500) NOT NULL DEFAULT 'https://api.anthropic.com/v1/messages',
    api_key VARCHAR(500) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    max_tokens INTEGER DEFAULT 4000,
    anthropic_version VARCHAR(20) DEFAULT '2023-06-01',
    activo BOOLEAN DEFAULT true,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE configuracion_openai (
    id_config_openai SERIAL PRIMARY KEY,
    id_modelo_ia INTEGER UNIQUE NOT NULL REFERENCES modelos_ia(id_modelo_ia) ON DELETE CASCADE,
    id_prompt INTEGER NOT NULL REFERENCES prompt_comparacion(id_prompt) ON DELETE RESTRICT,
    endpoint_url VARCHAR(500) NOT NULL DEFAULT 'https://api.openai.com/v1/chat/completions',
    api_key VARCHAR(500) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    max_tokens INTEGER DEFAULT 4000,
    temperature DECIMAL(3,2) DEFAULT 0.7,
    activo BOOLEAN DEFAULT true,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE configuracion_gemini (
    id_config_gemini SERIAL PRIMARY KEY,
    id_modelo_ia INTEGER UNIQUE NOT NULL REFERENCES modelos_ia(id_modelo_ia) ON DELETE CASCADE,
    id_prompt INTEGER NOT NULL REFERENCES prompt_comparacion(id_prompt) ON DELETE RESTRICT,
    endpoint_url VARCHAR(500) NOT NULL DEFAULT 'https://generativelanguage.googleapis.com/v1beta/models',
    api_key VARCHAR(500) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    max_tokens INTEGER DEFAULT 4000,
    temperature DECIMAL(3,2) DEFAULT 0.7,
    activo BOOLEAN DEFAULT true,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE configuracion_deepseek (
    id_config_deepseek SERIAL PRIMARY KEY,
    id_modelo_ia INTEGER UNIQUE NOT NULL REFERENCES modelos_ia(id_modelo_ia) ON DELETE CASCADE,
    id_prompt INTEGER NOT NULL REFERENCES prompt_comparacion(id_prompt) ON DELETE RESTRICT,
    endpoint_url VARCHAR(500) NOT NULL DEFAULT 'https://api.deepseek.com/v1/chat/completions',
    api_key VARCHAR(500) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    max_tokens INTEGER DEFAULT 4000,
    temperature DECIMAL(3,2) DEFAULT 0.7,
    activo BOOLEAN DEFAULT true,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

CREATE TABLE comparaciones_individuales (
    id SERIAL PRIMARY KEY,
    id_usuario INTEGER NOT NULL REFERENCES usuarios(id_usuario),
    id_modelo_ia INTEGER REFERENCES modelos_ia(id_modelo_ia),
    id_lenguaje INTEGER NOT NULL REFERENCES lenguajes(id_lenguaje),
    nombre_comparacion VARCHAR(200),
    codigo_1 TEXT NOT NULL,
    codigo_2 TEXT NOT NULL,
    estado VARCHAR(20) DEFAULT 'Reciente',
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT check_solo_un_modelo CHECK (
        (id_modelo_ia IS NOT NULL AND id_modelo_ia_usuario IS NULL) OR
        (id_modelo_ia IS NULL AND id_modelo_ia_usuario IS NOT NULL)
    )
);

CREATE TABLE comparaciones_grupales (
    id_comparacion_grupal SERIAL PRIMARY KEY,
    id_usuario INTEGER NOT NULL REFERENCES usuarios(id_usuario),
    id_modelo_ia INTEGER REFERENCES modelos_ia(id_modelo_ia),
    id_lenguaje INTEGER NOT NULL REFERENCES lenguajes(id_lenguaje),
    nombre_comparacion VARCHAR(200),
    estado VARCHAR(20) DEFAULT 'Reciente',
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT check_solo_un_modelo CHECK (
        (id_modelo_ia IS NOT NULL AND id_modelo_ia_usuario IS NULL) OR
        (id_modelo_ia IS NULL AND id_modelo_ia_usuario IS NOT NULL)
    )
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
    id_comparacion_individual INTEGER NOT NULL REFERENCES comparaciones_individuales(id),
    porcentaje_similitud INT NOT NULL,
    explicacion TEXT
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

-- Insertar algunos roles básicos
INSERT INTO roles (nombre, descripcion) VALUES 
('admin', 'Administrador del sistema'),
('usuario', 'Docente')


-- Si tienen tablas en postgres y quieren traerlas al backend, pueden usar el siguiente comando:
python manage.py inspectdb > models.py

-- Crear un archivo de requerimientos para el proyecto
pip freeze > requirements.txt