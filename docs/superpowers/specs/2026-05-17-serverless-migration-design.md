# Design Spec: Migração para Arquitetura Serverless

**Data:** 2026-05-17
**Status:** Aprovado para implementação

---

## Contexto

O projeto One Piece Collection é um tracker de volumes do mangá. Hoje roda como uma aplicação Flask no Kubernetes (GitLab CI, SQLite embutido no deploy). O objetivo é eliminar toda a infraestrutura de runtime e migrar para um site estático servido via S3 + CloudFront, com o pipeline de geração rodando no GitHub Actions.

---

## Arquitetura

```
GitHub repo
  └── data/collection.yaml  (editado pelo usuário)
        │
        ▼ push para main (ou workflow_dispatch)
  GitHub Actions
        │
        ▼ roda pipeline Python
  volume_update.py
    ├── Scrapa Fandom Wiki → arcos + metadados de volumes
    ├── Lista s3://bucket/static/*.webp (imagens já existentes)
    ├── Baixa da Fandom APENAS imagens ausentes no S3
    ├── Renderiza index.html via Jinja2
    └── Salva resultado em ./output/
        │
        ▼ aws s3 cp output/index.html s3://bucket/index.html
        ▼ aws s3 sync output/static/ s3://bucket/static/
  S3 Bucket (static website)
    ├── index.html
    └── static/
          ├── style.css
          └── Volume_N.webp  (todas as capas)
        │
        ▼ aws cloudfront create-invalidation --paths "/*"
  CloudFront Distribution
        │
        ▼
  onepiece.felipeduribeiro.com.br
```

---

## Componentes

### Removidos

| Componente | Motivo |
|---|---|
| `website/app.py` | Flask não existe mais em runtime |
| `website/Dockerfile` | Sem servidor para containerizar |
| `website/my_database.db` | Sem banco de dados |
| `website/telemetry.py` | Sem runtime server |
| `website/requirements.txt` | Substituído por novo arquivo consolidado |
| `onepieceapp-helm/` | Sem Kubernetes |
| `.gitlab-ci.yml` | Substituído por GitHub Actions |

### Mantidos / Adaptados

| Componente | Mudança |
|---|---|
| `website/volume_update.py` | Adiciona renderização Jinja2 → `index.html`. Adiciona checagem de imagens existentes no S3. Remove gravação SQLite. |
| `website/owned.py` | Sem mudança |
| `website/data/collection.yaml` | Sem mudança — fonte de verdade da coleção |
| `website/templates/index.html` | Sem mudança |
| `website/static/style.css` | Sem mudança |

### Criados

| Componente | Descrição |
|---|---|
| `.github/workflows/update.yml` | Workflow do GitHub Actions |
| `requirements.txt` (raiz) | Dependências consolidadas: scraping + Jinja2, sem Flask |
| `Dockerfile` (raiz, dev only) | Para testes locais — roda pipeline e salva em `./output/` |

---

## Lógica do Pipeline (`volume_update.py`)

### Fluxo principal

1. Lê `data/collection.yaml` via `owned.py`
2. Scrapa a Fandom Wiki para obter arcos e volumes (lógica existente)
3. Lista objetos existentes em `s3://BUCKET/static/` via `boto3`
4. Para cada volume: se `static/Volume_N.webp` **não** existe no S3, baixa da Fandom e salva em `output/static/`
5. Renderiza `templates/index.html` com Jinja2 usando os dados dos volumes/arcos
6. Salva `output/index.html`
7. Copia `website/static/style.css` → `output/static/style.css`

### Modo de execução

| Variável de ambiente | Comportamento |
|---|---|
| `DRY_RUN=true` | Pula listagem e checagem do S3; baixa todas as imagens; salva em `./output/` local |
| `DRY_RUN=false` (padrão) | Checa S3 antes de baixar; faz `s3 cp` do `index.html` e `s3 sync` das imagens novas |

O modo `DRY_RUN=true` é usado nos testes locais com Docker.

---

## GitHub Actions Workflow

**Arquivo:** `.github/workflows/update.yml`

**Trigger:**
- `push` em `main` com alteração em `data/collection.yaml`
- `workflow_dispatch` (disparo manual)

**Steps:**
1. Checkout do repositório
2. Setup Python 3.12
3. `pip install -r requirements.txt`
4. Configurar credenciais AWS via `aws-actions/configure-aws-credentials`
5. Rodar `python website/volume_update.py`
6. `aws s3 cp output/index.html s3://$S3_BUCKET/index.html`
7. `aws s3 sync output/static/ s3://$S3_BUCKET/static/` (sem `--delete` — imagens são aditivas)
8. `aws cloudfront create-invalidation --distribution-id $CLOUDFRONT_DISTRIBUTION_ID --paths "/*"`

**GitHub Secrets necessários:**

| Secret | Descrição |
|---|---|
| `AWS_ACCESS_KEY_ID` | Chave IAM com permissão S3 + CloudFront |
| `AWS_SECRET_ACCESS_KEY` | Secret da chave IAM |
| `AWS_REGION` | Região do bucket (ex: `us-east-1`) |
| `S3_BUCKET_NAME` | Nome do bucket S3 |
| `CLOUDFRONT_DISTRIBUTION_ID` | ID da distribuição CloudFront |

---

## Estrutura do S3

```
s3://bucket-name/
  ├── index.html
  └── static/
        ├── style.css
        ├── Volume_1.webp
        ├── Volume_2.webp
        └── ...
```

O CloudFront deve ter `index.html` como documento raiz padrão.

---

## Testes Locais

**Build da imagem:**
```bash
docker build -t onepiece-pipeline .
```

**Execução local (sem AWS):**
```bash
docker run -e DRY_RUN=true -v $(pwd)/output:/app/output onepiece-pipeline
```

O resultado estará em `./output/`. Abrir `output/index.html` no browser para validar.

**A pasta `output/` é adicionada ao `.gitignore`.**

---

## Infraestrutura AWS (configuração manual)

> Fora do escopo desta implementação — configurar manualmente no console AWS.

Checklist de referência:
- [ ] S3 bucket com static website hosting habilitado (ou acesso via CloudFront OAC)
- [ ] Bucket policy permitindo leitura pública (ou via CloudFront OAC)
- [ ] CloudFront distribution apontando para o bucket, com `index.html` como default root object
- [ ] IAM user/role com permissões `s3:PutObject`, `s3:DeleteObject`, `s3:ListBucket`, `cloudfront:CreateInvalidation`
- [ ] HTTPS via ACM certificate (us-east-1 para CloudFront)
- [ ] CNAME no Route 53 apontando `onepiece.felipeduribeiro.com.br` para o domínio do CloudFront

---

## O que está fora do escopo

- Automação da infraestrutura AWS (Terraform/CDK) — avaliado futuramente
- Múltiplos ambientes (staging/prod)
- Cache inteligente de invalidação (invalida apenas arquivos alterados) — `/*` é suficiente por ora
