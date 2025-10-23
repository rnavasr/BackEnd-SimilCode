-- Tabla de roles
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    descripcion TEXT
);

-- Tabla de datos personales  
CREATE TABLE datos_personales (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL
);

-- Tabla de usuarios (relacionada con las dos anteriores)
CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    usuario VARCHAR(50) NOT NULL UNIQUE,
    contrasenia VARCHAR(255) NOT NULL,
    datos_personales_id INTEGER NOT NULL REFERENCES datos_personales(id),
    rol_id INTEGER NOT NULL REFERENCES roles(id),
    activo BOOLEAN DEFAULT true
);

-- Insertar algunos roles básicos
INSERT INTO roles (nombre, descripcion) VALUES 
('admin', 'Administrador del sistema'),
('usuario', 'Usuario regular')


-- Si tienen tablas en postgres y quieren traerlas al backend, pueden usar el siguiente comando:
python manage.py inspectdb > models.py


-- Crear un archivo de requerimientos para el proyecto
pip freeze > requirements.txt   