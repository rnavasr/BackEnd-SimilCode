# -*- coding: utf-8 -*-
"""
Resolucion de credenciales de los proveedores de modelos de lenguaje.

SimilCode no almacena ninguna credencial en su codigo fuente ni la distribuye
con el sistema. Quien despliega una instancia aporta su propia clave, por una
de dos vias:

  1. La interfaz de administracion (Modelos de IA), que la guarda cifrada en
     transito y nunca la devuelve en ninguna respuesta de la API.
  2. Una variable de entorno del servidor, util para despliegues automatizados
     y para reproducir los experimentos sin escribir la clave en la base de
     datos.

La via 1 tiene prioridad sobre la via 2. Si no hay clave por ninguna de las
dos, la peticion se rechaza con un mensaje explicito en lugar de enviarse al
proveedor y recibir un 401 opaco.
"""

import os

VARIABLES_DE_ENTORNO = {
    "Claude": "ANTHROPIC_API_KEY",
    "OpenAI": "OPENAI_API_KEY",
    "Gemini": "GEMINI_API_KEY",
    "DeepSeek": "DEEPSEEK_API_KEY",
}


class CredencialAusente(RuntimeError):
    """No hay clave de API disponible para el proveedor solicitado."""

    def __init__(self, proveedor):
        self.proveedor = proveedor
        variable = VARIABLES_DE_ENTORNO.get(proveedor)
        if variable:
            detalle = (
                "Registrela en Administracion > Modelos de IA, o definala en "
                "la variable de entorno %s del servidor." % variable
            )
        else:
            detalle = "Registrela en Administracion > Modelos de IA."
        super().__init__(
            "No hay una clave de API para %s. %s" % (proveedor, detalle)
        )


def clave_api(config, proveedor):
    """Devuelve la clave de API del proveedor.

    Busca primero en la configuracion almacenada y despues en la variable de
    entorno correspondiente. Lanza CredencialAusente si no encuentra ninguna.
    """
    almacenada = (getattr(config, "api_key", "") or "").strip()
    if almacenada:
        return almacenada

    variable = VARIABLES_DE_ENTORNO.get(proveedor)
    if variable:
        del_entorno = (os.environ.get(variable) or "").strip()
        if del_entorno:
            return del_entorno

    raise CredencialAusente(proveedor)


def hay_credencial(config, proveedor):
    """Indica si el proveedor tiene una clave disponible, sin revelarla."""
    try:
        clave_api(config, proveedor)
        return True
    except CredencialAusente:
        return False
