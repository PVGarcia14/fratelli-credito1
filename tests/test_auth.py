from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from auth import create_user, verify_user, list_user_records, register_login, reset_password


def test_password_creation_and_verification():
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / 'credit.db'
        ok, _ = create_user(db, 'PVGFratelli', 'PVgt753159#@', 'PRIMEIRO_ACESSO', 'admin')
        assert ok
        assert verify_user(db, 'pvgfratelli', 'PVgt753159#@')
        assert not verify_user(db, 'pvgfratelli', 'errada')


def test_password_recovery_and_creator_record():
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / 'credit.db'
        create_user(db, 'admin', '12345678', 'PRIMEIRO_ACESSO', 'admin')
        create_user(db, 'operador', 'abcdefgh', 'admin', 'user')
        assert verify_user(db, 'operador', 'abcdefgh')
        ok, _ = reset_password(db, 'operador', 'NovaSenha#123', 'admin')
        assert ok
        assert verify_user(db, 'operador', 'NovaSenha#123')
        rows = list_user_records(db)
        op = next(x for x in rows if x['username'] == 'operador')
        assert op['created_by'] == 'admin'
        assert op['role'] == 'user'
        register_login(db, 'operador')
        rows = list_user_records(db)
        op = next(x for x in rows if x['username'] == 'operador')
        assert op['last_login']
