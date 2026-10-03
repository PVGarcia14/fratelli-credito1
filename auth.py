from __future__ import annotations
import hashlib, hmac, os, secrets, sqlite3
from pathlib import Path

ITERATIONS = 220_000


def normalize_username(username: str) -> str:
    return ' '.join((username or '').strip().lower().split())


def _hash(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, ITERATIONS).hex()


def init_users(db_path: Path):
    with sqlite3.connect(db_path) as c:
        c.execute('''CREATE TABLE IF NOT EXISTS users(
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            created_at TEXT NOT NULL
        )''')


def has_users(db_path: Path) -> bool:
    init_users(db_path)
    with sqlite3.connect(db_path) as c:
        return c.execute('SELECT COUNT(*) FROM users').fetchone()[0] > 0


def list_users(db_path: Path) -> list[str]:
    init_users(db_path)
    with sqlite3.connect(db_path) as c:
        return [r[0] for r in c.execute('SELECT username FROM users ORDER BY username').fetchall()]


def create_user(db_path: Path, username: str, password: str) -> tuple[bool, str]:
    username = normalize_username(username)
    if len(username) < 3:
        return False, 'Usuário deve ter pelo menos 3 caracteres.'
    if len(password) < 8:
        return False, 'A senha deve ter pelo menos 8 caracteres.'
    salt = secrets.token_bytes(16)
    ph = _hash(password, salt)
    try:
        with sqlite3.connect(db_path) as c:
            c.execute('INSERT INTO users(username,password_hash,salt,created_at) VALUES(?,?,?,datetime("now"))',
                      (username, ph, salt.hex()))
        return True, 'Usuário criado.'
    except sqlite3.IntegrityError:
        return False, 'Esse usuário já existe.'


def verify_user(db_path: Path, username: str, password: str) -> bool:
    username = normalize_username(username)
    init_users(db_path)
    with sqlite3.connect(db_path) as c:
        row = c.execute('SELECT password_hash,salt FROM users WHERE username=?', (username,)).fetchone()
    if not row:
        return False
    try:
        expected = bytes.fromhex(row[0])
        actual = bytes.fromhex(_hash(password, bytes.fromhex(row[1])))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(expected, actual)


def reset_password(db_path: Path, username: str, new_password: str) -> tuple[bool, str]:
    username = normalize_username(username)
    if len(new_password) < 8:
        return False, 'A nova senha deve ter pelo menos 8 caracteres.'
    salt = secrets.token_bytes(16)
    ph = _hash(new_password, salt)
    init_users(db_path)
    with sqlite3.connect(db_path) as c:
        cur = c.execute('UPDATE users SET password_hash=?, salt=? WHERE username=?',
                        (ph, salt.hex(), username))
        if cur.rowcount == 0:
            return False, 'Usuário não encontrado.'
    return True, 'Senha redefinida com sucesso.'
