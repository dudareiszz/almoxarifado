# Sistema de Almoxarifado · IFPI Campus Pedro II

Atividade prática do laboratório do 3º ano. Sistema web para controlar o estoque do almoxarifado:
catálogo, entradas, pedidos de materiais e atendimento pela gerência, com controle de saldo e histórico.

**Tecnologias:** Python, Django, Django ORM e SQLite.

## Integrantes

| Nome | Matrícula |
|------|-----------|
| (preencher) | |
| (preencher) | |
| (preencher) | |
| (preencher) | |

## Como instalar e executar

Pré-requisito: Python 3.10 ou superior.

**Linux / macOS**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py carregar_dados
python manage.py runserver
```

**Windows (PowerShell)**

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py carregar_dados
python manage.py runserver
```

Abra http://127.0.0.1:8000/ no navegador.

## Contas fictícias da demonstração

Elas são criadas pelo comando `python manage.py carregar_dados` (pode ser rodado mais de uma vez sem duplicar nada).

| Perfil | Usuário | Senha | Setor |
|--------|---------|-------|-------|
| Gerência | `gerente` | `Gerente@123` | não se aplica |
| Solicitante | `ana` | `Solic@123` | Coordenação de Informática |
| Solicitante | `bruno` | `Solic@123` | Secretaria Acadêmica |
| Admin do Django (apoio) | `admin` | `Admin@123` | não se aplica |

O Django Admin (`/admin/`) apoia os cadastros. Pedidos e movimentações aparecem lá somente para
consulta, para ninguém desajustar o saldo por fora do sistema.

## Perfis e rotas

| Rota | Quem acessa |
|------|-------------|
| `/login/` | todos |
| `/` (catálogo e busca) | qualquer conta logada |
| `/pedidos/novo/`, `/pedidos/meus/` | solicitantes (cada um vê só os próprios pedidos) |
| `/gerencia/materiais/novo/`, `/gerencia/materiais/<id>/editar/` | gerência |
| `/gerencia/entradas/nova/` | gerência |
| `/gerencia/solicitantes/`, `/gerencia/solicitantes/novo/` | gerência |
| `/gerencia/pedidos/` (pendentes, atender e recusar) | gerência |
| `/gerencia/historico/` | gerência |

Sem login, qualquer rota redireciona para `/login/`. Conta de solicitante em rota de gerência recebe
**403 (acesso negado)**, inclusive em POST direto. A checagem é feita no servidor (`permissions.py`).

## Como o saldo é controlado

- Criar pedido **não** altera o saldo.
- Atender um pedido (`services.atender_pedido`) roda em transação: confere se o pedido ainda está
  pendente, confere o saldo, dá baixa, registra a saída e marca o atendimento. Só pode acontecer uma vez.
- Se a quantidade for maior que o saldo, aparece a mensagem de saldo insuficiente junto ao pedido,
  o saldo não muda e o pedido continua pendente.
- Toda entrada e saída vira uma linha em **Movimentação** (data, responsável, saldo após), visível em
  `/gerencia/historico/`.
- A recusa exige motivo e registra quem decidiu e quando.

## Como reproduzir os testes

Testes automatizados (cobrem a demonstração inteira, as permissões e as validações):

```bash
python manage.py test
```

Roteiro manual da demonstração obrigatória:

1. Entre como `gerente`. Em **Novo material**, cadastre `PAP-001`, "Resma de papel A4", categoria
   "Papelaria", unidade "resma". Em **Registrar entrada**, registre 1 unidade.
2. Entre como `ana` e peça 1 unidade. Saia, entre como `bruno` e peça 1 unidade. O catálogo continua
   mostrando saldo 1, e cada um vê só o próprio pedido em **Meus pedidos**.
3. Entre como `gerente`, abra **Pedidos pendentes** e clique em **Atender** no primeiro pedido.
   O saldo vai a 0 ("Sem estoque"). Em **Histórico** aparecem o solicitante, o setor e o gerente.
4. Clique em **Atender** no segundo pedido: a mensagem de saldo insuficiente aparece, o saldo continua 0
   e o pedido continua pendente.
5. Registre mais 1 unidade de entrada, confira "Disponível" e atenda o pedido restante.
6. Entre como `ana` e abra `/gerencia/entradas/nova/` e `/gerencia/pedidos/`: o sistema responde 403.

## Identidade visual

Verde institucional `#2F9E41` (topo, botões, selos de disponível e atendido) e vermelho `#CD191E`
(faixa do topo, recusa, "Sem estoque"). Os estados sempre aparecem **em texto**, nunca só por cor.
Em telas estreitas (até 700 px) as tabelas viram listas de cartões.

## Teste de usabilidade com outra equipe

(Preencher depois do teste.)

- Equipe que testou:
- Dificuldade observada:
- Ajuste realizado:

## Estrutura

```
config/                       configurações do projeto
almoxarifado/models.py        Setor, Perfil, Categoria, Material, Pedido, Movimentacao
almoxarifado/services.py      regras de saldo (entrada, atendimento, recusa)
almoxarifado/permissions.py   perfis e decoradores de permissão
almoxarifado/views.py         telas
almoxarifado/migrations/      migrações
almoxarifado/management/      comando carregar_dados
almoxarifado/tests.py         testes automatizados
```
