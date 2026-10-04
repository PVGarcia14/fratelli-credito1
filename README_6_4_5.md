# B2B Credit Decision Engine 6.4.5

Correção da autenticação e evolução do banco de usuários.

### Primeiro acesso
Use a aba **Primeiro acesso** para criar o primeiro administrador.

### Login
Use **Entrar**. Usuário é normalizado; senha é comparada exatamente como digitada.

### Banco de usuários
O banco local `credit.db` contém a tabela `users` com:
- usuário
- hash da senha + salt
- perfil
- ativo/inativo
- data de criação
- quem criou o usuário
- último login
- data da última alteração de senha

### Administração
Depois de entrar como administrador, o menu **Usuários** permite criar usuários e administrar os acessos.

### Recuperação
A recuperação normal exige um administrador autenticado. Para perda da senha do único administrador, use `reset_admin.py` localmente.
