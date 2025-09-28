# servicios/token_service.py
# Equivalente a TokenService.cs en una API de C#

import datetime
import json
import os
import uuid
import jwt  # Se requiere instalar: pip install PyJWT

class TokenService:
    """
    Clase que gestiona la creación y validación de tokens JWT.
    Equivalente a la clase TokenService en C#.
    """
    
    def __init__(self, configuracion=None):
        """
        Constructor de la clase.
        Carga la configuración JWT.
        
        Args:
            configuracion: Configuración de la aplicación. Si es None, se carga desde el archivo.
        """
        # Verificar si se proporcionó la configuración
        if configuracion is None:
            # Si no se proporcionó, cargar desde archivos conocidos o entorno
            base_dir = os.path.dirname(os.path.dirname(__file__))
            rutas_posibles = [
                os.path.join(base_dir, 'config', 'config.json'),
                os.path.join(base_dir, 'configuracion', 'config.json'),  # compatibilidad
            ]
            last_err = None
            for ruta in rutas_posibles:
                try:
                    with open(ruta) as archivo_config:
                        self.configuracion = json.load(archivo_config)
                        break
                except Exception as e:
                    last_err = e
                    continue
            else:
                # Fallback: variables de entorno mínimas para JWT
                self.configuracion = {
                    'Jwt': {
                        'Key': os.getenv('JWT_KEY', ''),
                        'Issuer': os.getenv('JWT_ISSUER', 'clasificode'),
                        'Audience': os.getenv('JWT_AUDIENCE', 'clasificode'),
                    }
                }
                if not self.configuracion['Jwt']['Key']:
                    raise ValueError(f"No se pudo cargar la configuración JWT desde archivos {rutas_posibles} ni desde variables de entorno (JWT_KEY)")
        else:
            # Si se proporcionó, usarla directamente
            self.configuracion = configuracion

        # Robustecer: si Jwt.Key está vacío en el archivo, intentar tomarlo del entorno
        try:
            key_in_file = (self.configuracion.get('Jwt') or {}).get('Key')
        except Exception:
            key_in_file = None
        env_key = os.getenv('JWT_KEY')
        if (not key_in_file) and env_key:
            if 'Jwt' not in self.configuracion:
                self.configuracion['Jwt'] = {}
            self.configuracion['Jwt']['Key'] = env_key
        # Normalizar Issuer/Audience desde entorno si están definidos
        env_iss = os.getenv('JWT_ISSUER')
        env_aud = os.getenv('JWT_AUDIENCE')
        if env_iss:
            self.configuracion['Jwt']['Issuer'] = env_iss
        if env_aud:
            self.configuracion['Jwt']['Audience'] = env_aud
    
    def generar_token(self, usuario):
        """
        Genera un token JWT para un usuario.
        Equivalente a GenerarToken(string usuario) en C#.
        
        Args:
            usuario (str|dict): Email/identificador o dict con claves: id, email, role.
            
        Returns:
            str: Token JWT generado.
        """
        # Obtener la clave JWT desde la configuración
        clave_jwt = self.configuracion.get("Jwt", {}).get("Key")
        if not clave_jwt:
            raise ValueError("La clave JWT no está configurada correctamente")
        
        # Obtener el emisor y la audiencia
        emisor = self.configuracion.get("Jwt", {}).get("Issuer")
        audiencia = self.configuracion.get("Jwt", {}).get("Audience")
        
        # Normalizar datos de usuario
        user_id = None
        email = None
        role = None
        if isinstance(usuario, dict):
            user_id = usuario.get('id') or usuario.get('user_id')
            email = usuario.get('email') or usuario.get('sub')
            role = usuario.get('role')
        else:
            email = str(usuario)

        # Crear claims (equivalente a claims en C#)
        # Permitir configurar expiración vía entorno (minutos)
        try:
            exp_minutes = int(os.getenv('JWT_EXPIRES_MINUTES', '120'))
        except Exception:
            exp_minutes = 120
        claims = {
            "sub": email,  # Subject (usuario/email)
            "jti": str(uuid.uuid4()),  # JWT ID (identificador único del token)
            "iss": emisor,  # Issuer (emisor)
            "aud": audiencia,  # Audience (audiencia)
            "iat": datetime.datetime.utcnow(),  # Issued At (momento de emisión)
            "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=exp_minutes)  # Expiration configurable
        }
        if user_id is not None:
            claims["user_id"] = user_id
        if role:
            claims["role"] = role
        
        # Generar el token
        token = jwt.encode(
            claims,
            clave_jwt,
            algorithm="HS256"
        )
        
        return token
    
    def validar_token(self, token):
        """
        Valida un token JWT.
        Esta función no está en el TokenService.cs original pero es útil.
        
        Args:
            token (str): Token JWT a validar.
            
        Returns:
            dict: Payload del token si es válido.
            None: Si el token es inválido.
        """
        try:
            # Obtener la clave JWT desde la configuración
            clave_jwt = self.configuracion.get("Jwt", {}).get("Key")
            if not clave_jwt:
                raise ValueError("La clave JWT no está configurada correctamente")
            
            # Obtener el emisor y la audiencia
            emisor = self.configuracion.get("Jwt", {}).get("Issuer")
            audiencia = self.configuracion.get("Jwt", {}).get("Audience")
            
            # Verificar el token
            payload = jwt.decode(
                token,
                clave_jwt,
                algorithms=["HS256"],
                options={"verify_signature": True, "verify_exp": True},
                issuer=emisor,
                audience=audiencia
            )
            # Normalizar alias común
            if 'email' not in payload and 'sub' in payload:
                payload['email'] = payload['sub']
            
            return payload
        except jwt.ExpiredSignatureError:
            print("Token expirado")
            return None
        except jwt.InvalidTokenError as e:
            print(f"Token inválido: {str(e)}")
            return None

    # Alias de compatibilidad
    def validate_token(self, token):
        return self.validar_token(token)