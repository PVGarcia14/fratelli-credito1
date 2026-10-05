"""
AUTH - Fratelli B2B Crédito

Controle de usuários e autenticação.

Características:
- Usuário armazenado normalizado;
- Senha nunca armazenada em texto puro;
- Hash PBKDF2 com salt individual;
- Primeiro acesso cria administrador;
- Registro de quem criou cada usuário;
- Registro de último login;
- Alteração/redefinição de senha;
- Ativação/desativação de usuário;
- Compatibilidade com banco SQLite existente.
"""

from __future__ import annotations

import sqlite3
import hashlib
import hmac
import secrets
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Tuple


# ============================================================
# CONFIGURAÇÃO
# ============================================================

ITERATIONS = 310_000
SALT_BYTES = 32


# ============================================================
# UTILITÁRIOS
# ============================================================

def normalize_username(username: str) -> str:
    """
    Padroniza o usuário para evitar problemas com:
    - maiúsculas/minúsculas;
    - espaços no início/fim;
    - espaços duplicados.
    """
    if username is None:
        return ""

    return " ".join(str(username).strip().lower().split())


def normalize_role(role: str) -> str:
    role = str(role or "user").strip().lower()

    if role not in ("admin", "user"):
        return "user"

    return role


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def get_connection(db_path) -> sqlite3.Connection:
    """
    Abre conexão com o banco SQLite.

    Cria a pasta automaticamente quando necessário.
    """
    path = Path(db_path)

    if path.parent and str(path.parent) not in ("", "."):
        path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(path), timeout=30)

    conn.row_factory = sqlite3.Row

    # Melhor comportamento para SQLite.
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")

    return conn


# ============================================================
# SENHAS
# ============================================================

def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    """
    Gera hash seguro da senha usando PBKDF2-HMAC-SHA256.

    O formato armazenado é:

        pbkdf2$iterações$salt$hash
    """

    if password is None:
        password = ""

    password = str(password)

    if salt is None:
        salt = secrets.token_bytes(SALT_BYTES)

    derived = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        ITERATIONS,
    )

    return (
        f"pbkdf2${ITERATIONS}$"
        f"{salt.hex()}$"
        f"{derived.hex()}"
    )


def verify_password(password: str, stored_hash: str) -> bool:
    """
    Verifica uma senha contra o hash armazenado.
    """

    if not password or not stored_hash:
        return False

    try:
        parts = stored_hash.split("$")

        if len(parts) != 4:
            return False

        algorithm, iterations, salt_hex, hash_hex = parts

        if algorithm != "pbkdf2":
            return False

        iterations = int(iterations)

        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)

        calculated = hashlib.pbkdf2_hmac(
            "sha256",
            str(password).encode("utf-8"),
            salt,
            iterations,
        )

        return hmac.compare_digest(calculated, expected)

    except Exception:
        return False


# ============================================================
# BANCO / ESTRUTURA
# ============================================================

def init_users(db_path) -> None:
    """
    Cria a estrutura de usuários caso ainda não exista.

    Também adiciona colunas que possam estar faltando em
    versões anteriores do sistema.
    """

    conn = get_connection(db_path)

    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL,
                last_login TEXT,
                password_changed_at TEXT
            )
            """
        )

        # Migração defensiva para bancos antigos.
        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(users)").fetchall()
        }

        migrations = {
            "role": "ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'",
            "active": "ALTER TABLE users ADD COLUMN active INTEGER NOT NULL DEFAULT 1",
            "created_at": "ALTER TABLE users ADD COLUMN created_at TEXT",
            "created_by": "ALTER TABLE users ADD COLUMN created_by TEXT",
            "last_login": "ALTER TABLE users ADD COLUMN last_login TEXT",
            "password_changed_at": "ALTER TABLE users ADD COLUMN password_changed_at TEXT",
        }

        for column, sql in migrations.items():
            if column not in columns:
                try:
                    conn.execute(sql)
                except sqlite3.OperationalError:
                    pass

        # Corrige registros antigos que eventualmente tenham campos vazios.
        conn.execute(
            """
            UPDATE users
            SET role = 'user'
            WHERE role IS NULL OR TRIM(role) = ''
            """
        )

        conn.execute(
            """
            UPDATE users
            SET active = 1
            WHERE active IS NULL
            """
        )

        conn.execute(
            """
            UPDATE users
            SET created_at = ?
            WHERE created_at IS NULL OR TRIM(created_at) = ''
            """,
            (now_iso(),),
        )

        conn.execute(
            """
            UPDATE users
            SET created_by = 'LEGACY'
            WHERE created_by IS NULL OR TRIM(created_by) = ''
            """
        )

        conn.commit()

    finally:
        conn.close()


# ============================================================
# CONSULTAS
# ============================================================

def has_users(db_path) -> bool:
    init_users(db_path)

    conn = get_connection(db_path)

    try:
        row = conn.execute(
            "SELECT COUNT(*) AS total FROM users"
        ).fetchone()

        return int(row["total"]) > 0

    finally:
        conn.close()


def list_users(db_path) -> List[str]:
    init_users(db_path)

    conn = get_connection(db_path)

    try:
        rows = conn.execute(
            """
            SELECT username
            FROM users
            WHERE active = 1
            ORDER BY username
            """
        ).fetchall()

        return [row["username"] for row in rows]

    finally:
        conn.close()


def list_user_records(db_path) -> List[Dict]:
    init_users(db_path)

    conn = get_connection(db_path)

    try:
        rows = conn.execute(
            """
            SELECT
                id,
                username,
                role,
                active,
                created_at,
                created_by,
                last_login,
                password_changed_at
            FROM users
            ORDER BY username
            """
        ).fetchall()

        return [dict(row) for row in rows]

    finally:
        conn.close()


def get_user(db_path, username: str) -> Optional[Dict]:
    init_users(db_path)

    normalized = normalize_username(username)

    if not normalized:
        return None

    conn = get_connection(db_path)

    try:
        row = conn.execute(
            """
            SELECT
                id,
                username,
                password_hash,
                role,
                active,
                created_at,
                created_by,
                last_login,
                password_changed_at
            FROM users
            WHERE username = ?
            LIMIT 1
            """,
            (normalized,),
        ).fetchone()

        if row is None:
            return None

        return dict(row)

    finally:
        conn.close()


# ============================================================
# CRIAÇÃO DE USUÁRIO
# ============================================================

def create_user(
    db_path,
    username: str,
    password: str,
    created_by: str,
    role: str = "user",
) -> Tuple[bool, str]:

    init_users(db_path)

    username = normalize_username(username)
    created_by = normalize_username(created_by) or "SISTEMA"
    role = normalize_role(role)

    if not username:
        return False, "Informe um usuário."

    if len(username) < 3:
        return False, "O usuário deve ter pelo menos 3 caracteres."

    if not password:
        return False, "Informe uma senha."

    if len(password) < 6:
        return False, "A senha deve ter pelo menos 6 caracteres."

    password_hash = hash_password(password)

    now = now_iso()

    conn = get_connection(db_path)

    try:
        existing = conn.execute(
            """
            SELECT id
            FROM users
            WHERE username = ?
            LIMIT 1
            """,
            (username,),
        ).fetchone()

        if existing is not None:
            return False, f"O usuário '{username}' já existe."

        conn.execute(
            """
            INSERT INTO users (
                username,
                password_hash,
                role,
                active,
                created_at,
                created_by,
                last_login,
                password_changed_at
            )
            VALUES (?, ?, ?, 1, ?, ?, NULL, ?)
            """,
            (
                username,
                password_hash,
                role,
                now,
                created_by,
                now,
            ),
        )

        conn.commit()

        return True, f"Usuário '{username}' criado com sucesso."

    except sqlite3.IntegrityError:
        conn.rollback()
        return False, "Não foi possível criar o usuário. Ele pode já existir."

    except Exception as exc:
        conn.rollback()
        return False, f"Erro ao criar usuário: {exc}"

    finally:
        conn.close()


# ============================================================
# LOGIN
# ============================================================

def verify_user(
    db_path,
    username: str,
    password: str,
) -> bool:

    """
    Valida usuário e senha.

    IMPORTANTE:
    - O usuário é normalizado antes da busca.
    - A senha NÃO é alterada.
    - A senha é comparada somente contra o hash.
    """

    normalized = normalize_username(username)

    if not normalized:
        return False

    if password is None:
        return False

    user = get_user(db_path, normalized)

    if user is None:
        return False

    if int(user.get("active", 0)) != 1:
        return False

    stored_hash = user.get("password_hash")

    if not stored_hash:
        return False

    return verify_password(password, stored_hash)


# ============================================================
# LOGIN REGISTRADO
# ============================================================

def register_login(db_path, username: str) -> bool:

    normalized = normalize_username(username)

    if not normalized:
        return False

    conn = get_connection(db_path)

    try:
        cursor = conn.execute(
            """
            UPDATE users
            SET last_login = ?
            WHERE username = ?
              AND active = 1
            """,
            (now_iso(), normalized),
        )

        conn.commit()

        return cursor.rowcount > 0

    finally:
        conn.close()


# ============================================================
# ADMINISTRADOR
# ============================================================

def is_admin(db_path, username: str) -> bool:

    user = get_user(db_path, username)

    if user is None:
        return False

    return (
        int(user.get("active", 0)) == 1
        and normalize_role(user.get("role")) == "admin"
    )


# ============================================================
# ALTERAÇÃO DE SENHA
# ============================================================

def reset_password(
    db_path,
    username: str,
    new_password: str,
    changed_by: str,
) -> Tuple[bool, str]:

    username = normalize_username(username)
    changed_by = normalize_username(changed_by) or "SISTEMA"

    if not username:
        return False, "Usuário inválido."

    if not new_password:
        return False, "Informe a nova senha."

    if len(new_password) < 6:
        return False, "A nova senha deve ter pelo menos 6 caracteres."

    if not is_admin(db_path, changed_by):
        return False, "Somente um administrador pode redefinir senhas."

    password_hash = hash_password(new_password)

    conn = get_connection(db_path)

    try:
        cursor = conn.execute(
            """
            UPDATE users
            SET
                password_hash = ?,
                password_changed_at = ?
            WHERE username = ?
              AND active = 1
            """,
            (
                password_hash,
                now_iso(),
                username,
            ),
        )

        conn.commit()

        if cursor.rowcount == 0:
            return False, "Usuário não encontrado ou inativo."

        return True, f"Senha do usuário '{username}' redefinida com sucesso."

    finally:
        conn.close()


# ============================================================
# DESATIVAÇÃO
# ============================================================

def deactivate_user(
    db_path,
    username: str,
) -> Tuple[bool, str]:

    username = normalize_username(username)

    if not username:
        return False, "Usuário inválido."

    conn = get_connection(db_path)

    try:
        cursor = conn.execute(
            """
            UPDATE users
            SET active = 0
            WHERE username = ?
            """,
            (username,),
        )

        conn.commit()

        if cursor.rowcount == 0:
            return False, "Usuário não encontrado."

        return True, f"Usuário '{username}' desativado."

    finally:
        conn.close()
