# Hubi Time

Sistema desktop (Windows) de controle de jornada de trabalho, horas trabalhadas, banco de horas e acompanhamento financeiro pessoal, construido com **Python + PySide6 + Supabase**.

> Os valores financeiros exibidos sao sempre **estimativas de controle pessoal** - nao substituem a folha de pagamento oficial da empresa.

---

## Indice

1. [Arquitetura](#arquitetura)
2. [Requisitos](#requisitos)
3. [Configuracao do Supabase](#configuracao-do-supabase)
4. [Autenticacao, OTP e SMTP](#autenticacao-otp-e-smtp)
5. [Variaveis de ambiente](#variaveis-de-ambiente)
6. [Instalacao e execucao](#instalacao-e-execucao)
7. [Testes](#testes)
8. [Build do executavel (.exe)](#build-do-executavel-exe)
9. [Seguranca](#seguranca)
10. [Checklist de funcionalidades](#checklist-de-funcionalidades)
11. [Limitacoes conhecidas](#limitacoes-conhecidas)

---

## Arquitetura

Camadas com responsabilidades separadas (Repository + Service pattern):

```
UI (PySide6)  ->  Services (regras de negocio)  ->  Repositories (acesso a dados)  ->  Supabase
```

- **UI nunca acessa o banco diretamente.** Toda tela recebe um `AppContainer` (injecao de dependencia) com os services ja instanciados.
- **Repositories** (`repositories/`) sao os unicos modulos que chamam `supabase-py`. Traduzem qualquer erro de rede/API em `RepositoryError` com mensagem amigavel.
- **Services** (`services/`) contem as regras de negocio: calculo de jornada (`CalculationService`, puro e testavel), autenticacao (`AuthService`), CRUD de jornada com salvamento parcial (`WorkService`), vigencias de salario/carga horaria, auditoria e relatorios.
- **Models** (`models/`) sao dataclasses que espelham as tabelas do Supabase.
- **Widgets** (`widgets/`) sao componentes de UI reutilizaveis: sidebar, cards, campo de horario com botao "Agora", grafico (PyQtGraph), dialogos padronizados, editor de dia (`DayEditorWidget`, usado tanto em "Hoje" quanto em "Registrar Horas").
- **Workers** (`workers/async_worker.py`): toda chamada de rede roda em `QThread` via `AsyncTaskRunner`, para nunca travar a interface.
- **Security** (`security/session_storage.py`): o recurso "Manter-me conectado" grava somente o `refresh_token` do Supabase no Windows Credential Manager (via `keyring`) - nunca a senha.

### Decisoes tecnicas relevantes

| Decisao | Motivo |
|---|---|
| Auditoria gravada por **trigger SQL `SECURITY DEFINER`** | Garante que o historico (`work_record_history`) nao possa ser forjado pelo cliente via API - o usuario comum so tem `SELECT`. |
| Soft delete (`status = archived`) | Registros de jornada nunca sao apagados fisicamente no fluxo normal. |
| Concorrencia otimista (`version`) | Evita que duas sessoes sobrescrevam uma a outra silenciosamente. |
| `Decimal` + `NUMERIC` para dinheiro | Evita erros de arredondamento de ponto flutuante em valores financeiros. |
| Calculos internos em minutos (`int`) | Evita erros de precisao/arredondamento em `timedelta`/string. |
| Vigencias (`salary_history`, `work_schedule_history`) append-only | Meses passados continuam usando a configuracao valida na epoca. |

### Estrutura de pastas

```
Hubi-Time/
|-- main.py                  # entry point
|-- app_container.py         # composition root (injecao de dependencia)
|-- app_state.py             # sessao do usuario logado (estado compartilhado)
|-- config/                  # settings.py (.env) e constants.py (enums)
|-- database/
|   |-- supabase_client.py   # cliente Supabase singleton
|-- supabase/
|   |-- config.toml          # configuracao do projeto para a Supabase CLI
|   |-- migrations/          # scripts SQL, aplicados via `supabase db push`
|-- models/                  # dataclasses (WorkRecord, SalaryEntry, ...)
|-- repositories/            # unico ponto de acesso ao Supabase
|-- services/                # regras de negocio (auth, work, calculation, salary, report, audit, notification)
|-- security/                # armazenamento seguro de sessao (keyring)
|-- workers/                 # execucao assincrona (QThread)
|-- widgets/                 # componentes de UI reutilizaveis
|-- ui/                      # telas (uma pasta por feature)
|   |-- login/ register/ verify_email/ forgot_password/
|   |-- main_window/ today/ work_entry/ calendar/ history/
|   |-- hours_control/ bank_hours/ finance/ reports/ settings/ profile/
|-- utils/                   # funcoes puras (datas, dinheiro, validacoes, formatacao)
|-- tests/                   # testes unitarios (pytest)
|-- assets/                  # icones/imagens
```

### Modelo do banco (resumo)

```
auth.users (Supabase Auth)
  |-- profiles            (1:1)  nome, timestamps
  |-- user_settings       (1:1)  tema, notificacoes, keep_signed_in
  |-- work_schedule_history (N)  vigencias de carga horaria (append-only)
  |-- salary_history        (N)  vigencias salariais (append-only)
  |-- overtime_rules        (N)  percentuais de hora extra configuraveis
  |-- work_records          (N)  UNIQUE(user_id, work_date); soft delete
  |     `-- work_record_history (N) auditoria append-only, 1 linha por campo alterado
  |-- holidays               (N)
  |-- notifications          (N)
  `-- audit_log              (N)  auditoria generica (perfil, config, salario, jornada)
```

Todas as tabelas tem **Row Level Security** habilitado com policies `auth.uid() = user_id`. Veja `supabase/migrations/20260101000013_row_level_security.sql`.

> RLS e GRANT sao camadas independentes no Postgres: uma policy so e avaliada depois que o papel `authenticated` ja tem o privilegio basico (`SELECT`/`INSERT`/`UPDATE`/`DELETE`) na tabela. A migration `20260101000014_grants.sql` concede exatamente esses privilegios - sem ela, toda consulta falha com `permission denied for table X`, mesmo com as policies corretas.

---

## Requisitos

- Windows 10/11
- Python 3.11 ou superior
- Uma conta e projeto no [Supabase](https://supabase.com)

---

## Configuracao do Supabase

1. Crie um projeto no Supabase.
2. Aplique as migrations em `supabase/migrations/` (13 arquivos, executados em ordem cronologica pelo nome). Duas formas de fazer isso:

   **Opcao A - Supabase CLI (recomendado):**
   ```powershell
   # instala a CLI sob demanda via npx (ou "npm install -g supabase" para uso frequente)
   npx supabase login
   npx supabase link --project-ref SEU_PROJECT_REF
   npx supabase db push
   ```
   O `PROJECT_REF` e o identificador do projeto, visivel na URL do painel Supabase (`app.supabase.com/project/SEU_PROJECT_REF`) ou em **Project Settings > General**. O `db push` aplica exatamente os arquivos de `supabase/migrations/` ao banco remoto, na ordem do timestamp no nome de cada arquivo, e registra o que ja foi aplicado - rodar de novo no futuro so aplica migrations novas.

   **Opcao B - SQL Editor manual:** abra **SQL Editor** no painel do Supabase e execute, um de cada vez e **nesta ordem**, o conteudo de cada arquivo de `supabase/migrations/` (ordene pelo prefixo numerico/timestamp do nome do arquivo).

3. Em **Authentication > Providers**, mantenha o provider **Email** habilitado.
4. Em **Authentication > Settings**, habilite **Confirm email** (obrigatorio para o fluxo de verificacao por codigo OTP).
5. Copie a **Project URL** e a chave **anon/public** em **Project Settings > API** - voce vai usa-las no `.env` (veja abaixo).

**Nunca use a `service_role key` no aplicativo desktop.** Ela nao e necessaria em nenhum momento - toda a seguranca e feita via RLS + a chave anon.

> `supabase/` tambem contem `config.toml` (gerado por `supabase init`) e pastas de uso interno da CLI (`.branches`, `.temp`) que ja estao no `.gitignore` proprio dessa pasta - nao precisam de atencao manual.

---

## Autenticacao, OTP e SMTP

- O cadastro, login, verificacao por codigo (OTP), recuperacao de senha e troca de senha usam **exclusivamente o Supabase Auth** (`supabase.auth.*`). Nao existe nenhuma logica caseira de senha no codigo.
- O codigo de verificacao de 6 digitos enviado por e-mail (cadastro e recuperacao de senha) e o mecanismo nativo do Supabase (`verify_otp` com `type="signup"` e `type="recovery"`).
- **Configuracao de e-mail/SMTP:** por padrao o Supabase usa um servidor de e-mail compartilhado com limites baixos, adequado apenas para testes. Para producao, configure um provedor SMTP proprio em **Project Settings > Auth > SMTP Settings** (ex.: SendGrid, Amazon SES, Postmark). **Essas credenciais SMTP devem ser configuradas exclusivamente no painel do Supabase - nunca no codigo do aplicativo.**

### Template do e-mail de verificacao (obrigatorio)

Por padrao, o Supabase envia um e-mail com um **link** de confirmacao (`{{ .ConfirmationURL }}`), que aponta para a "Site URL" do projeto - normalmente `http://localhost:3000`, ou seja, nenhum site real. Como o Hubi Time usa o fluxo de **codigo digitado no app** (nao o link), e preciso trocar o template para exibir `{{ .Token }}` em vez do botao de confirmacao. Sem essa troca, o usuario recebe um link quebrado em vez do codigo de 6 digitos.

Os templates prontos ja estao versionados em `supabase/email_templates/`. Para aplicar:

1. No painel do Supabase, va em **Authentication > Email Templates**.
2. Abra **Confirm signup**, apague o conteudo e cole o HTML de [`supabase/email_templates/confirm_signup.html`](supabase/email_templates/confirm_signup.html). Salve.
3. Abra **Reset Password**, apague o conteudo e cole o HTML de [`supabase/email_templates/reset_password.html`](supabase/email_templates/reset_password.html). Salve.
4. Em **Authentication > URL Configuration**, o campo "Site URL" pode ficar com qualquer valor placeholder (ex.: `http://localhost`) - ele nunca e acessado pelo app, ja que o fluxo e 100% por codigo.

Isso e configuracao feita direto no painel do Supabase - nao ha nenhuma chamada de API/credencial que permita automatizar essa etapa pelo terminal.

---

## Variaveis de ambiente

Copie `.env.example` para `.env` e preencha:

```
SUPABASE_URL=https://SEU-PROJETO.supabase.co
SUPABASE_ANON_KEY=SUA_CHAVE_ANON_AQUI
APP_KEYRING_SERVICE=HubiTime
APP_LOG_LEVEL=INFO
```

O arquivo `.env` **nunca** deve ser commitado (ja esta no `.gitignore`).

---

## Instalacao e execucao

```powershell
# 1. Criar e ativar ambiente virtual
py -m venv .venv
.venv\Scripts\activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variaveis de ambiente
copy .env.example .env
# edite o .env com os valores do seu projeto Supabase

# 4. Executar
python main.py
```

No primeiro uso: crie uma conta pela tela de cadastro, confirme o codigo enviado por e-mail e faca login. Antes de usar "Controle de Horas"/"Financeiro" de forma completa, configure sua carga horaria e salario em **Configuracoes**.

---

## Testes

```powershell
pip install -r requirements.txt
pytest
```

Os testes cobrem exclusivamente logica pura (nao dependem de rede/Supabase/Qt):

- `test_calculation_service.py`: horas trabalhadas, intervalos, banco de horas, saldo, horas extras, registros incompletos.
- `test_salary_and_schedule_service.py`: selecao de vigencia salarial/carga horaria por data, calculo de valor/hora com `Decimal`.
- `test_validators.py`: validacao de e-mail/senha e deteccao de inconsistencias de horario.

---

## Build do executavel (.exe)

```powershell
pip install pyinstaller
pyinstaller --noconfirm --windowed --name "HubiTime" ^
    --add-data ".env.example;." ^
    main.py
```

O executavel sera gerado em `dist/HubiTime/`. Copie um arquivo `.env` real (nao versionado) para a mesma pasta do `.exe` antes de distribuir/executar, com as credenciais do seu projeto Supabase.

> Dica: para um instalador unico (`--onefile`), adicione a flag `--onefile`, mas prefira `--windowed` (sem `--onefile`) em producao, pois a inicializacao fica mais rapida.

---

## Distribuicao gratuita (GitHub Releases)

O workflow `.github/workflows/release.yml` builda o `.exe` automaticamente e publica no GitHub Releases sempre que uma tag de versao e enviada - distribuicao publica, gratuita e sem servidor proprio.

**Configuracao (uma vez so):**

1. O repositorio precisa estar **publico** no GitHub (minutos de Actions ilimitados e gratuitos para repositorios publicos).
2. Em **Settings > Secrets and variables > Actions**, crie dois repository secrets:
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`

   Sim, a chave `anon`/`publishable` pode ser embutida no `.exe` distribuido publicamente - ela foi desenhada para isso pela Supabase. A protecao dos dados vem do RLS (cada usuario so acessa o que e seu), nao do sigilo dessa chave. **Nunca** faca isso com a `service_role key`.

**Para lancar uma nova versao:**

```powershell
git tag v1.0.0
git push origin v1.0.0
```

Em poucos minutos, o Release `v1.0.0` aparece na aba **Releases** do repositorio com um `HubiTime-v1.0.0-windows.zip` pronto para download - esse e o link que voce compartilha com qualquer pessoa, em qualquer lugar. Cada usuario baixa, extrai e executa `HubiTime.exe`; como todos usam a mesma `SUPABASE_URL`/`SUPABASE_ANON_KEY`, todos se conectam ao mesmo projeto (cada um com sua propria conta, isolada por RLS).

**Sobre o aviso do Windows SmartScreen:** como o `.exe` nao e assinado digitalmente (certificados de assinatura de codigo custam ~US$100-400/ano, o que nao se justifica para um projeto gratuito de baixo uso), o Windows vai exibir "O Windows protegeu seu PC" no primeiro uso. Isso e esperado, nao e um erro - oriente quem for baixar a clicar em **Mais informacoes > Executar assim mesmo**. Se o projeto crescer, [SignPath.io](https://signpath.io) oferece assinatura gratuita para projetos open source elegiveis.

---

## Seguranca

Checklist aplicado neste projeto:

- [x] Autenticacao 100% via Supabase Auth (sem senha em texto claro, sem hash caseiro).
- [x] Apenas a chave `anon` no aplicativo; `service_role` nunca referenciada no codigo.
- [x] Row Level Security habilitado em **todas** as tabelas de dados do usuario.
- [x] Um usuario nunca consegue ler/escrever dados de outro (policies `auth.uid() = user_id`).
- [x] Historico de auditoria (`work_record_history`) gravado por trigger `SECURITY DEFINER`; usuario comum so tem `SELECT` - nao pode inserir historico falso nem editar/apagar (trigger `prevent_history_mutation` bloqueia mesmo tentativas administrativas).
- [x] Soft delete: nenhum `DELETE` fisico de `work_records` no fluxo normal (sem policy de DELETE na tabela).
- [x] Sessao persistente ("Manter-me conectado") grava somente `refresh_token` via `keyring` (Windows Credential Manager) - nunca a senha.
- [x] `.env` fora do controle de versao; `.env.example` com placeholders, sem segredos reais.
- [x] Erros tecnicos (stack traces, respostas de API) nunca exibidos ao usuario - apenas mensagens amigaveis; detalhe tecnico vai so para o log.

---

## Checklist de funcionalidades

- [x] Cadastro com verificacao de e-mail por codigo OTP (Supabase Auth)
- [x] Login, logout e sessao persistente
- [x] Recuperacao de senha (e-mail -> codigo -> nova senha)
- [x] Data atual automatica + selecao de qualquer data
- [x] Registro parcial dos 4 horarios (nenhum obrigatorio, sem duplicar o dia)
- [x] Botao "Agora" em cada horario
- [x] Deteccao de inconsistencias de horario (aviso, nao bloqueio)
- [x] CRUD completo com soft delete (arquivar/restaurar)
- [x] Auditoria completa e visivel (aba "Historico de alteracoes")
- [x] Calendario mensal colorido por status
- [x] Historico filtravel (hoje/semana/mes/ano/personalizado) + arquivados
- [x] CalculationService isolado da UI, com testes
- [x] Configuracao de jornada (semanal/mensal) com vigencia
- [x] Controle de Horas (indicadores + graficos previsto x realizado)
- [x] Banco de Horas (saldo diario/semanal/mensal/anual/acumulado + evolucao)
- [x] Horas extras com percentuais configuraveis
- [x] Salario com historico por vigencia
- [x] Dashboard financeiro com estimativas (deixado explicito que sao estimativas)
- [x] Graficos financeiros (evolucao salarial, horas normais x extras)
- [x] Exportacao Excel/CSV/PDF
- [x] Notificacoes/alertas configuraveis
- [x] Tema claro/escuro persistido por usuario
- [x] Interface moderna (cards, sombras, cantos arredondados, estados de hover/loading)

## Limitacoes conhecidas

- Ao alternar o tema (claro/escuro) durante a sessao, os graficos (PyQtGraph) ja renderizados mantem as cores do tema em que foram criados ate a tela ser reaberta - isso e uma limitacao de como o PyQtGraph le a configuracao de cores (no momento da criacao do widget), nao um bug funcional.
- Os icones da barra lateral usam glifos Unicode (sem dependencia de pacote de icones externo); substitua por SVGs proprios em `assets/icons/` se desejar uma identidade visual customizada.
- O SMTP de envio de e-mails (OTP, recuperacao de senha) deve ser configurado por voce diretamente no painel do Supabase - nenhuma credencial de e-mail existe neste repositorio.
