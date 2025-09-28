#!/usr/bin/env python3
"""
Script para crear o actualizar un usuario administrador en la tabla users.
Uso:
  python scripts/seed_admin.py --email admin@clasificode.local --password MiClaveSegura123! --name "Administrador"
"""
import argparse
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from servicios.control_conexion import ControlConexion
from servicios.security import hash_password, validate_email, validate_password_strength


def ensure_admin(email: str, password: str, name: str = "Administrador") -> int:
    cc = ControlConexion()
    # Validaciones básicas
    email_norm = email.strip().lower()
    if not validate_email(email_norm):
        raise ValueError(f"Email inválido: {email}")
    pwd_check = validate_password_strength(password)
    if not pwd_check['valid']:
        raise ValueError("Contraseña débil: " + "; ".join(pwd_check['errors']))

    phash = hash_password(password)

    # Asegurar que la tabla users existe; si falla, dejar que la excepción lo diga
    # Upsert por email (único). Establece role=admin e is_active=true.
    sql = (
        """
        INSERT INTO users (email, password_hash, name, role, is_active, created_at, updated_at)
        VALUES (%s, %s, %s, 'admin', true, NOW(), NOW())
        ON CONFLICT (email)
        DO UPDATE SET
            password_hash = EXCLUDED.password_hash,
            name = EXCLUDED.name,
            role = 'admin',
            is_active = true,
            updated_at = NOW()
        RETURNING id;
        """
    )
    user_id = cc.ejecutar_escalares(sql, (email_norm, phash, name.strip()))
    return int(user_id) if user_id is not None else -1


def main():
    parser = argparse.ArgumentParser(description="Seed admin user")
    parser.add_argument("--email", required=True, help="Email del admin")
    parser.add_argument("--password", required=True, help="Contraseña del admin")
    parser.add_argument("--name", default="Administrador", help="Nombre a mostrar")
    args = parser.parse_args()

    try:
        user_id = ensure_admin(args.email, args.password, args.name)
        print(f"Admin listo. user_id={user_id}, email={args.email}")
        print("Ahora puedes probar login en POST /auth/login con ese email y contraseña.")
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
