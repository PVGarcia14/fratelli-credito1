from pathlib import Path
from getpass import getpass
from auth import init_users, list_users, reset_password

DB = Path(__file__).parent / 'credit.db'
init_users(DB)
users = list_users(DB)
if not users:
    print('Nenhum usuário cadastrado. Abra o sistema pelo navegador e crie o primeiro administrador.')
    raise SystemExit(0)
print('Usuários cadastrados:')
for i, u in enumerate(users, 1):
    print(f'{i}. {u}')
choice = input('Escolha o número do usuário: ').strip()
try:
    username = users[int(choice)-1]
except (ValueError, IndexError):
    print('Opção inválida.')
    raise SystemExit(1)
p1 = getpass('Nova senha: ')
p2 = getpass('Confirmar nova senha: ')
if p1 != p2:
    print('As senhas não conferem.')
    raise SystemExit(1)
ok, msg = reset_password(DB, username, p1)
print(msg)
