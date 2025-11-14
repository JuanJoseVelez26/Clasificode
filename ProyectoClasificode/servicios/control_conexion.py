# servicios/control_conexion.py
import os
import json
import pandas as pd
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

_ENGINE_CACHE: dict[str, dict[str, any]] = {}
_LOGGED_CONNECTIONS: set[str] = set()

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
        self.session_factory = None
    
    def abrir_bd(self):
        """Método para abrir la base de datos usando SQLAlchemy."""
        try:
            connection_key = None
            
            # Obtener el proveedor desde la configuración
            proveedor = self.configuracion.get("DatabaseProvider")
            if not proveedor:
                raise ValueError("Proveedor de base de datos no configurado")
            
            # Obtener la cadena de conexión
            cadena_conexion = self.configuracion.get("ConnectionStrings", {}).get(proveedor)
            if not cadena_conexion:
                raise ValueError("La cadena de conexión es nula o vacía")
            
            connection_key = f"{proveedor}:{cadena_conexion}"
            
            # Solo mostrar el log la primera vez
            if connection_key not in _LOGGED_CONNECTIONS:
                logging.debug(f"[DB] Intentando abrir conexión con el proveedor: {proveedor}")
                try:
                    masked = cadena_conexion
                    if '://' in masked:
                        head, tail = masked.split('://', 1)
                        if '@' in tail and ':' in tail.split('@')[0]:
                            creds, rest = tail.split('@', 1)
                            user = creds.split(':', 1)[0]
                            masked = f"{head}://{user}:****@{rest}"
                    logging.debug(f"[DB] Cadena de conexión: {masked}")
                except Exception:
                    logging.debug("[DB] Cadena de conexión: [oculta por seguridad]")
                _LOGGED_CONNECTIONS.add(connection_key)
            
            if connection_key in _ENGINE_CACHE:
                cache_entry = _ENGINE_CACHE[connection_key]
                self.engine = cache_entry['engine']
                self.session_factory = cache_entry['session_factory']
            else:
                engine = create_engine(
                    cadena_conexion,
                    echo=False,
                    pool_size=5,
                    max_overflow=10,
                    pool_pre_ping=True,
                    pool_recycle=3600
                )
                session_factory = sessionmaker(bind=engine, expire_on_commit=False)
                _ENGINE_CACHE[connection_key] = {
                    'engine': engine,
                    'session_factory': session_factory
                }
                self.engine = engine
                self.session_factory = session_factory
            
            if not self.engine or not self.session_factory:
                raise ValueError("No se pudo inicializar el motor de base de datos")
            
            if not self.session or not self.session.is_active:
                self.session = self.session_factory()
            return True
        except Exception as ex:
            logging.error(f"[DB] Ocurrió una excepción al abrir la conexión: {str(ex)}")
            raise ValueError(f"Error al abrir la conexión a la base de datos: {str(ex)}")
    
    def cerrar_bd(self):
        """Método para cerrar la conexión a la base de datos."""
        try:
            if self.session:
                self.session.close()
                self.session = None
            
            # No cerramos el engine global para permitir reutilización
        except Exception as e:
            logging.warning(f"[DB] Error cerrando conexión: {str(e)}")
                
    def get_session(self):
        """
        Context manager para obtener una sesión de base de datos.
        
        Returns:
            Session: Sesión de SQLAlchemy
            
        Example:
            with cc.get_session() as session:
                result = session.query(Model).all()
        """
        if not self.engine or not self.session_factory:
            self.abrir_bd()
        
        return self.session_factory()
    
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
            if not self.engine or not self.session_factory:
                self.abrir_bd()
            
            sql = text(consulta_sql)
            params = {}
            consulta_modificada = consulta_sql
            
            if parametros:
                if isinstance(parametros, (tuple, list)):
                    for i, valor in enumerate(parametros):
                        params[f"p{i}"] = valor
                    for i in range(consulta_modificada.count('?')):
                        consulta_modificada = consulta_modificada.replace('?', f":p{i}", 1)
                    idx = 0
                    tmp = consulta_modificada
                    while '%s' in tmp:
                        tmp = tmp.replace('%s', f":p{idx}", 1)
                        idx += 1
                    consulta_modificada = tmp
                    sql = text(consulta_modificada)
                else:
                    params = parametros
            
            with self.session_factory() as session:
                result = session.execute(sql, params)
                session.commit()
                return result.rowcount
        except Exception as ex:
            logging.error(f"[DB] Error al ejecutar comando SQL: {str(ex)}")
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
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Crear nueva sesión para evitar problemas de estado
                if not self.engine or not self.session_factory:
                    self.abrir_bd()
                
                # Usar una nueva sesión para cada operación
                with self.session_factory() as session:
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

                    result = session.execute(sql, params)
                    row = result.fetchone()
                    session.commit()
                    return row[0] if row and len(row) > 0 else None
                
            except Exception as ex:
                # Si es un error de concurrencia, reintentar
                if "concurrent operations are not permitted" in str(ex) and attempt < max_retries - 1:
                    import time
                    time.sleep(0.1 * (attempt + 1))  # Esperar un poco más en cada intento
                    continue
                
                logging.error(f"[DB] Error al ejecutar consulta escalar (intento {attempt + 1}): {str(ex)}")
                if attempt == max_retries - 1:
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
            logging.error(f"[DB] Error al ejecutar consulta SQL: {str(ex)}")
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