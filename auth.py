from __future__ import annotations
import hashlib, hmac, secrets, sqlite3
from pathlib import Path
from datetime import datetime, timezone

ITERATIONS = 220_000


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def normalize_username(username: str) -> str:
    # Username is normalized; password is NEVER stripped or lower-cased.
    return ' '.join((username or '').strip().lower().split())


def _hash(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac('sha256', (password or '').encode('utf-8'), salt, ITERATIONS).hex()


def init_users(db_path: Path):
    with sqlite3.connect(db_path) as c:
        c.execute('''CREATE TABLE IF NOT EXISTS users(
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            created_at TEXT NOT NULL,
            created_by TEXT NOT NULL DEFAULT 'PRIMEIRO_ACESSO',
            role TEXT NOT NULL DEFAULT 'admin',
            active INTEGER NOT NULL DEFAULT 1,
            last_login TEXT,
            password_changed_at TEXT
        )''')
        # Migration for databases created by 6.4.4 and earlier.
        cols = {r[1] for r in c.execute('PRAGMA table_info(users)').fetchall()}
        migrations = {
            'created_by': "ALTER TABLE users ADD COLUMN created_by TEXT NOT NULL DEFAULT 'PRIMEIRO_ACESSO'",
            'role': "ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'admin'",
            'active': "ALTER TABLE users ADD COLUMN active INTEGER NOT NULL DEFAULT 1",
            'last_login': "ALTER TABLE users ADD COLUMN last_login TEXT",
            'password_changed_at': "ALTER TABLE users ADD COLUMN password_changed_at TEXT",
        }
        for name, sql in migrations.items():
            if name not in cols:
                c.execute(sql)
        # Ensure legacy rows have meaningful timestamps.
        c.execute("UPDATE users SET password_changed_at=COALESCE(password_changed_at,created_at)")


def has_users(db_path: Path) -> bool:
    init_users(db_path)
    with sqlite3.connect(db_path) as c:
        return c.execute('SELECT COUNT(*) FROM users WHERE active=1').fetchone()[0] > 0


def list_users(db_path: Path) -> list[str]:
    init_users(db_path)
    with sqlite3.connect(db_path) as c:
        return [r[0] for r in c.execute('SELECT username FROM users WHERE active=1 ORDER BY username').fetchall()]


def list_user_records(db_path: Path) -> list[dict]:
    init_users(db_path)
    with sqlite3.connect(db_path) as c:
        rows = c.execute('''SELECT username, role, active, created_at, created_by, last_login, password_changed_at
                            FROM users ORDER BY created_at DESC''').fetchall()
    return [dict(username=r[0], role=r[1], active=bool(r[2]), created_at=r[3], created_by=r[4],
                 last_login=r[5] or '', password_changed_at=r[6] or '') for r in rows]


def is_admin(db_path: Path, username: str) -> bool:
    init_users(db_path)
    u = normalize_username(username)
    with sqlite3.connect(db_path) as c:
        row = c.execute('SELECT role,active FROM users WHERE username=?', (u,)).fetchone()
    return bool(row and row[1] and row[0] == 'admin')


def create_user(db_path: Path, username: str, password: str, created_by: str = 'PRIMEIRO_ACESSO', role: str = 'user') -> tuple[bool, str]:
    username = normalize_username(username)
    created_by = 'PRIMEIRO_ACESSO' if (created_by or '').strip().upper() == 'PRIMEIRO_ACESSO' else (normalize_username(created_by) or 'PRIMEIRO_ACESSO')
    init_users(db_path)
    if len(username) < 3:
        return False, 'Usuário deve ter pelo menos 3 caracteres.'
    if len(password or '') < 8:
        return False, 'A senha deve ter pelo menos 8 caracteres.'
    if role not in ('admin', 'user'):
        role = 'user'
    salt = secrets.token_bytes(16)
    ph = _hash(password, salt)
    ts = now_utc()
    try:
        with sqlite3.connect(db_path) as c:
            c.execute('''INSERT INTO users(username,password_hash,salt,created_at,created_by,role,active,last_login,password_changed_at)
                         VALUES(?,?,?,?,?,?,1,NULL,?)''', (username, ph, salt.hex(), ts, created_by, role, ts))
        return True, 'Usuário criado com sucesso.'
    except sqlite3.IntegrityError:
        return False, 'Esse usuário já existe.'


def verify_user(db_path: Path, username: str, password: str) -> bool:
    username = normalize_username(username)
    init_users(db_path)
    with sqlite3.connect(db_path) as c:
        row = c.execute('SELECT password_hash,salt,active FROM users WHERE username=?', (username,)).fetchone()
    if not row or not row[2]:
        return False
    try:
        expected = bytes.fromhex(row[0])
        actual = bytes.fromhex(_hash(password, bytes.fromhex(row[1])))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(expected, actual)


def register_login(db_path: Path, username: str):
    u = normalize_username(username)
    init_users(db_path)
    with sqlite3.connect(db_path) as c:
        c.execute('UPDATE users SET last_login=? WHERE username=? AND active=1', (now_utc(), u))


def reset_password(db_path: Path, username: str, new_password: str, actor: str = 'ADMIN_RECOVERY') -> tuple[bool, str]:
    username = normalize_username(username)
    if len(new_password or '') < 8:
        return False, 'A nova senha deve ter pelo menos 8 caracteres.'
    salt = secrets.token_bytes(16)
    ph = _hash(new_password, salt)
    init_users(db_path)
    with sqlite3.connect(db_path) as c:
        cur = c.execute('UPDATE users SET password_hash=?, salt=?, password_changed_at=? WHERE username=? AND active=1',
                        (ph, salt.hex(), now_utc(), username))
        if cur.rowcount == 0:
            return False, 'Usuário não encontrado ou inativo.'
    return True, f'Senha redefinida por {normalize_username(actor) or "administrador"}.'


def deactivate_user(db_path: Path, username: str) -> tuple[bool, str]:
    u = normalize_username(username)
    init_users(db_path)
    with sqlite3.connect(db_path) as c:
        active_admins = c.execute("SELECT COUNT(*) FROM users WHERE role='admin' AND active=1").fetchone()[0]
        row = c.execute("SELECT role,active FROM users WHERE username=?", (u,)).fetchone()
        if not row:
            return False, 'Usuário não encontrado.'
        if not row[1]:
            return False, 'Usuário já está inativo.'
        if row[0] == 'admin' and active_admins <= 1:
            return False, 'Não é possível desativar o último administrador ativo.'
        c.execute('UPDATE users SET active=0 WHERE username=?', (u,))
    return True, 'Usuário desativado.'
