# servicios/control_conexion.py
import os
import json
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

class ControlConexion:
    """
    Clase que gestiona las conexiones a la base de datos usando SQLAlchemy.
    """
    
    def __init__(self, entorno=None, configuracion=None):
        """Constructor de la clase."""
        if configuracion is None:
            # Si no se proporciona configuración, intentamos cargarla del archivo
            base_dir = os.path.dirname(os.path.dirname(__file__))
            rutas_posibles = [
                os.path.join(base_dir, 'config', 'config.json'),
                os.path.join(base_dir, 'configuracion', 'config.json'),  # compatibilidad
            ]
            last_err = None
            for ruta_config in rutas_posibles:
                try:
                    with open(ruta_config) as archivo_config:
                        self.configuracion = json.load(archivo_config)
                        break
                except Exception as e:
                    last_err = e
                    continue
            else:
                raise ValueError(f"No se pudo cargar la configuración. Intentos: {rutas_posibles}. Error: {str(last_err)}")
        else:
            self.configuracion = configuracion
        
        self.entorno = entorno
        self.engine = None
        self.session = None
    
    def abrir_bd(self):
        """Método para abrir la base de datos usando SQLAlchemy."""
        try:
            # Obtener el proveedor desde la configuración
            proveedor = self.configuracion.get("DatabaseProvider")
            if not proveedor:
                raise ValueError("Proveedor de base de datos no configurado")
            
            # Obtener la cadena de conexión
            cadena_conexion = self.configuracion.get("ConnectionStrings", {}).get(proveedor)
            if not cadena_conexion:
                raise ValueError("La cadena de conexión es nula o vacía")
            
            print(f"Intentando abrir conexión con el proveedor: {proveedor}")
            # Evitar exponer contraseña en logs
            try:
                masked = cadena_conexion
                if '://' in masked:
                    # postgresql+psycopg://user:pass@host:port/db
                    head, tail = masked.split('://', 1)
                    if '@' in tail and ':' in tail.split('@')[0]:
                        creds, rest = tail.split('@', 1)
                        user = creds.split(':', 1)[0]
                        masked = f"{head}://{user}:****@{rest}"
                print(f"Cadena de conexión: {masked}")
            except Exception:
                print("Cadena de conexión: [oculta por seguridad]")
            
            # Crear el motor de SQLAlchemy
            self.engine = create_engine(cadena_conexion, echo=False)
            
            # Crear una sesión
            self.session = Session(self.engine)
            
            print("Conexión a la base de datos abierta exitosamente")
            return True
        except Exception as ex:
            print(f"Ocurrió una excepción: {str(ex)}")
            raise ValueError(f"Error al abrir la conexión a la base de datos: {str(ex)}")
    
    def cerrar_bd(self):
        """Método para cerrar la conexión a la base de datos."""
        try:
            if self.session:
                self.session.close()
                self.session = None
            
            if self.engine:
                self.engine.dispose()
                self.engine = None
        except Exception as ex:
            raise ValueError(f"Error al cerrar la conexión a la base de datos: {str(ex)}")
    
    def ejecutar_comando_sql(self, consulta_sql, parametros=None):
        """
        Método para ejecutar un comando SQL y devolver el número de filas afectadas.
        
        Args:
            consulta_sql (str): Consulta SQL a ejecutar.
            parametros (list): Lista de parámetros para la consulta.
            
        Returns:
            int: Número de filas afectadas.
        """
        try:
            if not self.session or not self.engine:
                # Intento de apertura perezosa
                self.abrir_bd()
            
            # Crear un objeto de consulta SQLAlchemy
            sql = text(consulta_sql)
            
            # Preparar parámetros
            params = {}
            if parametros:
                if isinstance(parametros, tuple) or isinstance(parametros, list):
                    # Convertir lista de valores a diccionario
                    for i, valor in enumerate(parametros):
                        params[f"p{i}"] = valor
                    
                    # Modificar la consulta para usar parámetros nombrados
                    consulta_modificada = consulta_sql
                    # Reemplazar placeholders tipo '?' primero
                    for i in range(consulta_modificada.count('?')):
                        consulta_modificada = consulta_modificada.replace('?', f":p{i}", 1)
                    # Luego reemplazar placeholders tipo '%s'
                    # Nota: usamos un índice adicional continuando el conteo
                    start_idx = consulta_modificada.count(":p")  # aproximación, pero a falta de parser estricto
                    # Mejor calculamos basado en len(parametros)
                    # Reiniciamos y reemplazamos %s secuencialmente
                    idx = 0
                    tmp = consulta_modificada
                    while '%s' in tmp:
                        tmp = tmp.replace('%s', f":p{idx}", 1)
                        idx += 1
                    consulta_modificada = tmp
                    
                    sql = text(consulta_modificada)
                else:
                    params = parametros
            
            # Ejecutar la consulta
            result = self.session.execute(sql, params)
            self.session.commit()
            
            # Devolver el número de filas afectadas
            return result.rowcount
        except Exception as ex:
            self.session.rollback()
            print(f"Error al ejecutar comando SQL: {str(ex)}")
            raise

    def ejecutar_escalares(self, consulta_sql, parametros=None):
        """
        Ejecutar una consulta que retorna un único valor escalar (por ejemplo, INSERT ... RETURNING id)

        Args:
            consulta_sql (str): Consulta SQL a ejecutar.
            parametros (list|tuple|dict): Parámetros de la consulta.

        Returns:
            any: Primer valor de la primera fila del resultado, o None si no hay filas.
        """
        try:
            if not self.session or not self.engine:
                self.abrir_bd()

            sql = text(consulta_sql)

            params = {}
            if parametros:
                if isinstance(parametros, (tuple, list)):
                    for i, valor in enumerate(parametros):
                        params[f"p{i}"] = valor
                    consulta_modificada = consulta_sql
                    for i in range(consulta_modificada.count('?')):
                        consulta_modificada = consulta_modificada.replace('?', f":p{i}", 1)
                    idx = 0
                    tmp = consulta_modificada
                    while '%s' in tmp:
                        tmp = tmp.replace('%s', f":p{idx}", 1)
                        idx += 1
                    sql = text(tmp)
                else:
                    params = parametros

            result = self.session.execute(sql, params)
            self.session.commit()
            row = result.fetchone()
            return row[0] if row and len(row) > 0 else None
        except Exception as ex:
            try:
                self.session.rollback()
            except Exception:
                pass
            print(f"Error al ejecutar consulta escalar: {str(ex)}")
            raise
    
    def ejecutar_consulta_sql(self, consulta_sql, parametros=None):
        """
        Método para ejecutar una consulta SQL y devolver un DataFrame con los resultados.
        
        Args:
            consulta_sql (str): Consulta SQL a ejecutar.
            parametros (list, optional): Lista de parámetros para la consulta.
            
        Returns:
            pandas.DataFrame: Resultados de la consulta como un DataFrame.
        """
        try:
            if not self.engine:
                # Intento de apertura perezosa
                self.abrir_bd()
            
            # Preparar parámetros
            params = {}
            if parametros:
                if isinstance(parametros, tuple) or isinstance(parametros, list):
                    # Convertir lista de valores a diccionario
                    for i, valor in enumerate(parametros):
                        params[f"p{i}"] = valor
                    
                    # Modificar la consulta para usar parámetros nombrados
                    consulta_modificada = consulta_sql
                    for i in range(consulta_modificada.count('?')):
                        consulta_modificada = consulta_modificada.replace('?', f":p{i}", 1)
                    idx = 0
                    tmp = consulta_modificada
                    while '%s' in tmp:
                        tmp = tmp.replace('%s', f":p{idx}", 1)
                        idx += 1
                    consulta_sql = tmp
                else:
                    params = parametros
            
            # Usar pandas para leer directamente en un DataFrame
            df = pd.read_sql(text(consulta_sql), self.engine, params=params)
            return df
        except Exception as ex:
            print(f"Error al ejecutar consulta SQL: {str(ex)}")
            raise
    
    def crear_parametro(self, nombre, valor):
        """
        Método para crear un parámetro de consulta SQL.
        
        Args:
            nombre (str): Nombre del parámetro.
            valor (object): Valor del parámetro.
            
        Returns:
            tuple: Tupla con el nombre y valor del parámetro.
        """
        # Para mantener compatibilidad con el código existente
        return (nombre, valor)