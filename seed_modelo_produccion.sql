-- =====================================================================
-- seed_modelo_produccion.sql
-- ---------------------------------------------------------------------
-- Registra el modelo de lenguaje integrado en SimilCode y lo marca como
-- recomendado. La seleccion del modelo de produccion es un dato de
-- configuracion, no una constante del codigo: la aplicacion resuelve el
-- proveedor a partir de la fila de configuracion asociada a cada modelo.
--
-- Idempotente: puede ejecutarse mas de una vez sin duplicar filas. Una
-- reejecucion no sobrescribe la credencial ya establecida.
--
-- CREDENCIAL
--   Este archivo no contiene ninguna clave de API y no debe contenerla nunca.
--   La aporta quien instala el sistema, por cualquiera de estas dos vias:
--     a) Administracion > Modelos de IA, campo "API Key".
--     b) La variable de entorno OPENAI_API_KEY del servidor.
--   Mientras no exista ninguna de las dos, el sistema rechaza las peticiones
--   con un mensaje explicito en lugar de contactar al proveedor.
--
-- REQUISITO PREVIO
--   Debe existir al menos un prompt activo en prompt_comparacion y otro en
--   prompt_eficiencia_algoritmica; la configuracion se enlaza con ellos.
--
-- Uso:
--   psql -U <usuario> -d <base> -f seed_modelo_produccion.sql
-- =====================================================================

BEGIN;

-- 1. Proveedor -------------------------------------------------------
INSERT INTO proveedores_ia (nombre, descripcion, sitio_web, activo)
VALUES ('OpenAI',
        'Proveedor de modelos de lenguaje de proposito general.',
        'https://openai.com',
        true)
ON CONFLICT (nombre) DO NOTHING;

-- 2. Modelo ----------------------------------------------------------
--    El identificador incluye la fecha de version, de modo que la
--    configuracion evaluada queda fijada de forma no ambigua.
INSERT INTO modelos_ia (proveedor_id, nombre, version, descripcion,
                        color_ia, activo, recomendado)
SELECT p.id,
       'GPT-5.5',
       'gpt-5.5-2026-04-23',
       'Modelo integrado en SimilCode para la comparacion de codigo y la '
       'estimacion de complejidad algoritmica.',
       '#10A37F',
       true,
       true
FROM proveedores_ia p
WHERE p.nombre = 'OpenAI'
ON CONFLICT (nombre) DO UPDATE
   SET version     = EXCLUDED.version,
       descripcion = EXCLUDED.descripcion,
       activo      = true,
       recomendado = true;

-- 3. Un solo modelo recomendado por ambito ---------------------------
UPDATE modelos_ia
   SET recomendado = false
 WHERE nombre <> 'GPT-5.5'
   AND id_usuario IS NOT DISTINCT FROM
       (SELECT id_usuario FROM modelos_ia WHERE nombre = 'GPT-5.5');

-- 4. Configuracion del proveedor -------------------------------------
--    Se enlaza con los prompts activos de comparacion y de eficiencia,
--    tanto individuales como grupales.
INSERT INTO configuracion_openai (
        id_modelo_ia, id_prompt, id_prompt_grupal,
        id_prompt_eficiencia, id_prompt_eficiencia_grupal,
        endpoint_url, api_key, model_name,
        max_tokens, temperature, activo)
SELECT m.id,
       (SELECT id_prompt FROM prompt_comparacion
         WHERE activo = true
         ORDER BY (tipo = 'individual') DESC, id_prompt DESC LIMIT 1),
       (SELECT id_prompt FROM prompt_comparacion
         WHERE activo = true
         ORDER BY (tipo = 'grupal') DESC, id_prompt DESC LIMIT 1),
       (SELECT id_prompt_eficiencia FROM prompt_eficiencia_algoritmica
         WHERE activo = true
         ORDER BY (tipo_analisis = 'individual') DESC,
                  id_prompt_eficiencia DESC LIMIT 1),
       (SELECT id_prompt_eficiencia FROM prompt_eficiencia_algoritmica
         WHERE activo = true
         ORDER BY (tipo_analisis = 'grupal') DESC,
                  id_prompt_eficiencia DESC LIMIT 1),
       'https://api.openai.com/v1/chat/completions',
       '',
       'gpt-5.5-2026-04-23',
       4000,
       0.00,
       true
FROM modelos_ia m
WHERE m.nombre = 'GPT-5.5'
ON CONFLICT (id_modelo_ia) DO UPDATE
   SET model_name          = EXCLUDED.model_name,
       endpoint_url        = EXCLUDED.endpoint_url,
       max_tokens          = EXCLUDED.max_tokens,
       temperature         = EXCLUDED.temperature,
       activo              = true,
       fecha_modificacion  = CURRENT_TIMESTAMP;

COMMIT;

-- 5. Comprobacion ----------------------------------------------------
SELECT m.nombre, m.version, m.recomendado, m.activo,
       c.model_name, c.endpoint_url, c.temperature, c.activo AS config_activa,
       CASE WHEN btrim(coalesce(c.api_key, '')) = ''
            THEN 'sin clave en la base: se usara OPENAI_API_KEY del entorno'
            ELSE 'clave registrada en la base' END AS estado_credencial
  FROM modelos_ia m
  JOIN configuracion_openai c ON c.id_modelo_ia = m.id
 WHERE m.nombre = 'GPT-5.5';