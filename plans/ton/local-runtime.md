# TON — runtime local em Docker

Registro operacional de como subir a stack na máquina de desenvolvimento, as duas
topologias disponíveis, o custo medido de cada uma, e três armadilhas que já
quebraram o ambiente. Não é documento de planejamento: é runbook.

Máquina de referência das medições: Windows 11, 15,7 GB de RAM física, 20 threads,
Docker Desktop 29.5.2 sobre WSL2 com `memory=6GB` no `~/.wslconfig` (teto efetivo
de 5.927 MiB para containers).

---

## 1. As duas topologias

O `docker-compose.onyx-lite.yml` **não** é um compose independente. É um overlay
que move seis serviços para *profiles* e troca três backends de infraestrutura
por Postgres. Nada é adicionado por ele.

### Lite — o padrão para desenvolvimento

```bash
cd deployment/docker_compose
docker compose -f docker-compose.yml \
               -f docker-compose.onyx-lite.yml \
               -f docker-compose.dev.yml up -d
```

Sobem 5 containers: `api_server`, `web_server`, `nginx`, `relational_db`,
`code-interpreter`.

Ficam de fora, atrás de profile: `background` (Celery), `cache` (Redis),
`opensearch`, `minio`, `inference_model_server`, `indexing_model_server`.

O overlay também fixa no `api_server`:

```
DISABLE_VECTOR_DB=true
FILE_STORE_BACKEND=postgres
CACHE_BACKEND=postgres
AUTH_BACKEND=postgres
```

Some: conectores, busca RAG sobre documentos indexados, embeddings locais e o
trabalho de background em processo separado — o próprio `api_server` assume o que
sobra. Fica: conversa com LLM, ferramentas, upload de arquivo de usuário,
Projetos, conhecimento de agente e code interpreter.

### Completa

```bash
cd deployment/docker_compose
docker compose -f docker-compose.yml \
               -f docker-compose.dev.yml \
               -f docker-compose.local-tuning.yml up -d
```

Sobem 10 containers. `minio` fica fora porque está atrás do profile
`s3-filestore` **também no compose base** — não é o overlay lite que o esconde. E
não faz falta: o `.env` fixa `FILE_STORE_BACKEND=postgres`, então o object store
não é usado. Se você subir com `--profile s3-filestore` sem mudar essa variável,
o MinIO fica ocioso; se mudar para `s3`, os arquivos já gravados no Postgres
deixam de ser encontrados.

### Alternar entre as duas

As duas topologias compartilham o mesmo banco, então alternar é um comando. Duas
consequências:

1. **Sessões caem.** Lite guarda auth no Postgres, completa no Redis. Cada troca
   invalida a sessão e exige novo login.
2. Use `--remove-orphans` ao voltar para lite, para derrubar os containers que só
   a completa cria.

---

## 2. Armadilha: as imagens precisam ser construídas deste repo

**Sintoma.** `api_server` em loop de reinício com:

```
ERROR [alembic.util.messaging] Can't locate revision identified by 'faee7eaa921e'
FAILED: Can't locate revision identified by 'faee7eaa921e'
```

**Causa.** Os Planos backend do TON adicionam migrations próprias — `faee7eaa921e`
é `ton_identity_rules_and_analysis_core` (TON-BE-003B). A imagem
`onyxdotapp/onyx-backend:latest` publicada por upstream **não as tem**: 440
migrations contra 448 deste repo. Qualquer `docker compose pull` ou
`docker pull onyxdotapp/onyx-backend` sobrescreve a imagem local construída do
repo e deixa o banco à frente da imagem.

O mesmo vale para `onyxdotapp/onyx-web-server:latest` quando há trabalho de
frontend não publicado.

**Correção.**

```bash
cd deployment/docker_compose
docker compose -f docker-compose.yml -f docker-compose.dev.yml build api_server
```

Isso produz `onyxdotapp/onyx-backend:latest` a partir de `backend/`, alvo
`runtime`. `api_server` e `background` compartilham essa imagem.

Para o frontend, o contexto é `web/` e o `.dockerignore` já exclui
`node_modules`, `.next`, `/tests/`, `src/**/*.test.ts(x)` e `tools`:

```bash
docker build -t onyxdotapp/onyx-web-server:latest \
  --build-arg NEXT_PUBLIC_DO_NOT_USE_TOGGLE_OFF_DANSWER_POWERED=false \
  --build-arg "NODE_OPTIONS=--max-old-space-size=4096" \
  -f web/Dockerfile web/
```

**Verificar antes de acusar o banco:**

```bash
# a imagem tem a migration que o banco espera?
docker run --rm --entrypoint sh onyxdotapp/onyx-backend:latest \
  -c "ls /app/alembic/versions | grep -c . ; ls /app/alembic/versions | grep faee7eaa921e"

# em que revisão o banco está?
docker exec onyx-relational_db-1 psql -U postgres -d postgres -t \
  -c 'select version_num from alembic_version;'
```

**Prevenção.** Antes de sobrescrever uma imagem local, marque a anterior:
`docker tag onyxdotapp/onyx-backend:latest onyxdotapp/onyx-backend:backup`.
Retag é instantâneo e dispensa rede no rollback.

Só puxe do registry o que este repo não constrói: `opensearch`, `redis`, `minio`,
`postgres`, `code-interpreter`, `onyx-model-server`.

---

## 3. Armadilha: CRLF nos `*.sh` em checkout Windows

**Sintoma.** Container morre imediatamente com exit 127, e o log mostra:

```
/bin/sh: 3: /app/scripts/supervisord_entrypoint.sh: not found
```

O arquivo **existe** na imagem e é executável. Foi o que derrubou `background`.

**Causa.** O `.gitattributes` da raiz não tem regra para `*.sh`. Com
`core.autocrlf=true` (padrão comum no Windows) o checkout converte LF para CRLF.
O shebang vira `#!/bin/sh\r`, e o kernel procura um interpretador literalmente
chamado `/bin/sh\r`. O blob no repositório está correto — o defeito é do checkout,
e só aparece em imagem construída localmente no Windows.

Confirmar:

```bash
docker run --rm --entrypoint sh <imagem> \
  -c "head -c 12 /app/scripts/supervisord_entrypoint.sh | od -c | head -2"
# quebrado: #   !   /   b   i   n   /   s   h  \r  \n
# correto:  #   !   /   b   i   n   /   s   h  \n
```

**Contorno pontual.** Normalizar para LF antes do build e devolver a árvore
depois. São 10 arquivos em `backend/`:

```powershell
Get-ChildItem -Recurse -Path backend -Include "*.sh" -File | ForEach-Object {
  $t = [IO.File]::ReadAllText($_.FullName) -replace "`r`n", "`n"
  [IO.File]::WriteAllText($_.FullName, $t)
}
# build aqui
git checkout -- backend
```

**Correção de verdade**, a decidir por quem mantém o repo — nenhuma foi aplicada:

- `*.sh text eol=lf` no `.gitattributes` da raiz. Resolve para todo mundo e é o
  caminho correto, mas altera o repositório.
- `git config core.autocrlf input` neste clone. Resolve local, não protege
  ninguém mais.

---

## 4. Armadilha: `OPENSEARCH_ADMIN_PASSWORD` fora do `.env`

**Sintoma.** Qualquer `docker compose` no diretório falha antes de agir:

```
error while interpolating services.api_server.environment.[]:
required variable OPENSEARCH_ADMIN_PASSWORD is missing a value
```

**Causa.** O compose marca seis variáveis como obrigatórias com `${VAR:?...}`:
`MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD`, `OPENSEARCH_ADMIN_PASSWORD`,
`POSTGRES_PASSWORD`, `S3_AWS_ACCESS_KEY_ID`, `S3_AWS_SECRET_ACCESS_KEY`. Cinco
estão no `.env`; a do OpenSearch tinha sido injetada pelo shell na subida
original, então some a cada sessão nova. A interpolação valida a stack inteira,
inclusive serviços que o comando não vai tocar.

**Correção aplicada.** A chave foi persistida em
`deployment/docker_compose/.env`, que é gitignored por `deployment/.gitignore:1`
(`.env*`) e já guarda as outras cinco. Recuperável de um container em execução
sem exibir o valor:

```powershell
$e = docker inspect onyx-api_server-1 --format '{{json .Config.Env}}' | ConvertFrom-Json
$e | Where-Object { $_ -like 'OPENSEARCH_ADMIN_PASSWORD=*' }
```

---

## 5. Consumo medido

Em repouso, logo após subir, sem indexação em curso. Teto de 5.927 MiB.

| Container | Lite | Completa |
|---|---:|---:|
| `background` (Celery) | — | **1.606 MiB** |
| `opensearch` | — | **1.156 MiB** |
| `api_server` | 188 MiB | 725 MiB |
| `web_server` | 109 MiB | 185 MiB |
| `relational_db` | 131 MiB | 147 MiB |
| `inference_model_server` | — | 116 MiB |
| `indexing_model_server` | — | 107 MiB |
| `code-interpreter` | 45 MiB | 59 MiB |
| `cache` (Redis) | — | 6 MiB |
| `nginx` | 6 MiB | 5 MiB |
| **Total** | **~479 MiB (8%)** | **4.112 MiB (69%)** |

Três observações que contradizem a intuição:

1. **Os model servers são leves em repouso** — ~110 MiB cada, não os 1–2 GB que a
   imagem de 13,1 GB sugere. Carregam modelo sob demanda. Sob indexação real o
   número sobe; o `SIZING.md` do chart Helm avisa que um embedder no teto de CPU
   pode inanir os heartbeats do docprocessing e disparar o watchdog de stall.
2. **O Celery é o maior custo isolado**, não o OpenSearch. Um container só roda,
   via supervisord, oito workers (`primary`, `light`, `heavy`, `docfetching`,
   `docprocessing`, `user_file_processing`, `scheduled_tasks`, `monitoring`) mais
   o `beat` como agendador, o watchdog do beat, e os bots de Slack e Discord.
3. **O heap do OpenSearch foi reduzido.** O base fixa `-Xms2g -Xmx2g`, calibrado
   para deployment real, e `Xms=Xmx` reserva os 2 GB no start. Para índice de
   teste, `docker-compose.local-tuning.yml` baixa para 1 GB. Cabe manter: a
   pressão do OpenSearch é off-heap (k-NN nativo + page cache do Lucene), então
   heap menor não muda o comportamento de busca em índice pequeno.

### Sobre o teto do WSL2

O teto é o `memory=` do `~/.wslconfig`, **não** o que sobra de RAM no host.
Fechar aplicação no Windows não aumenta o que os containers podem usar. Subir o
teto exige `wsl --shutdown`, que derruba todos os containers de todos os
projetos — e containers com `restart: no` não voltam sozinhos.

Com 4.112 MiB de uso e 5.927 MiB de teto, a stack completa cabe em `memory=6GB`
sem ajuste adicional.

### Custo em disco

As três imagens que faltavam consumiram ~15 GB: `onyx-model-server` **13,1 GB**
descompactada (4,78 GB de download), `opensearch` 2,77 GB, `minio` 247 MB.

---

## 6. Arquivos locais fora do git

Registrados em `.git/info/exclude`, não em `.gitignore`, para não alterar arquivo
versionado:

| Arquivo | Papel |
|---|---|
| `deployment/docker_compose/docker-compose.local-tuning.yml` | heap do OpenSearch em 1 GB |
| `deployment/docker_compose/.env.bak-pre-full` | backup do `.env` antes de persistir a chave do OpenSearch |

---

## 7. Diagnóstico rápido

```bash
# estado e causa de morte
docker ps -a --filter "name=onyx-" --format "{{.Names}}\t{{.Status}}"
docker inspect <container> --format '{{.State.ExitCode}} oom={{.State.OOMKilled}} restarts={{.RestartCount}}'

# memoria contra o teto
docker stats --no-stream

# o Celery esta vivo?
docker top onyx-background-1        # espera supervisord + workers
```

Leitura dos códigos de saída observados:

| Código | Significado no contexto |
|---|---|
| 127 | comando não encontrado — quase sempre o CRLF do §3 |
| 137 | SIGKILL. Verifique `OOMKilled`; se falso e vários containers caíram juntos, foi shutdown da VM ou do daemon |
| 143 | SIGTERM, parada ordenada |
| 0 | saída limpa, tipicamente `docker stop` ou shutdown do daemon |

Queda simultânea de **todos** os containers, com mistura de 0/137/143 e
`OOMKilled=false`, não é OOM de container: é a VM do WSL2 ou o Docker Desktop
reiniciando. Aconteceu uma vez durante este trabalho, com o host em 2,4 GB
livres. Causa não determinada.
