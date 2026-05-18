# One Piece Collection

Tracker pessoal da minha coleção de volumes do mangá One Piece. O site exibe todas as capas organizadas por arco, destacando visualmente quais volumes já possuo.

**Site:** [onepiece.felipeduribeiro.com.br](https://onepiece.felipeduribeiro.com.br)

---

## Como funciona

O projeto é 100% serverless — não existe servidor em execução. Um pipeline Python gera um site estático e faz upload para o S3. O CloudFront entrega o conteúdo ao usuário final.

```
collection.yaml  (editado pelo usuário)
      │
      ▼  push para main
GitHub Actions
      │
      ▼  python website/volume_update.py
Pipeline
  ├── Scrapa API do Fandom Wiki → arcos + último volume
  ├── Verifica imagens já existentes no S3 (evita re-download)
  ├── Baixa capas ausentes em paralelo (8 workers)
  ├── Renderiza index.html via Jinja2
  └── Copia assets estáticos (CSS, ícone, etc.)
      │
      ▼  aws s3 cp / aws s3 sync
S3 Bucket
      │
      ▼  CloudFront
onepiece.felipeduribeiro.com.br
```

---

## Atualizando a coleção

Edite `website/data/collection.yaml` e faça push para `main`:

```yaml
volumes:
  - 1-65      # ranges são suportados
  - 100-112
databooks:
  - yellow
  - blue
  - red
  # - blue_deep   (exemplo de entrada comentada)
```

O GitHub Actions detecta a mudança neste arquivo e dispara o pipeline automaticamente.

---

## Estrutura do repositório

```
onepiece-app/
├── website/
│   ├── volume_update.py      # Pipeline principal: scraping, download, renderização
│   ├── owned.py              # Lê e expande os ranges do collection.yaml
│   ├── data/
│   │   └── collection.yaml   # Fonte de verdade da coleção
│   ├── templates/
│   │   └── index.html        # Template Jinja2 (renderizado em build time)
│   └── static/               # Assets permanentes: CSS, ícone, imagem de fallback
├── .github/
│   └── workflows/
│       └── update.yml        # Workflow do GitHub Actions
├── requirements.txt          # Dependências Python (scraping + Jinja2 + boto3)
├── Dockerfile                # Imagem para testes locais (DRY_RUN=true, porta 8080)
└── README.md
```

---

## Testes locais

### Com Docker (recomendado)

```bash
docker build -t onepiece-pipeline .
docker run -p 8080:8080 onepiece-pipeline
# Abrir http://localhost:8080
```

O container roda em `DRY_RUN=true`: ignora o S3, baixa todas as imagens e serve o resultado na porta 8080.

### Sem Docker

```bash
cd website
pip install -r ../requirements.txt

# Apenas gera o output local (sem AWS):
DRY_RUN=true python volume_update.py

# Servir para visualização:
python -m http.server 8080 --directory ../output
```

> **Windows:** defina `PYTHONIOENCODING=utf-8` antes de rodar o script para evitar erros de encoding com os emojis do log.

O output é gerado em `output/` na raiz do repositório (ignorado pelo git).

---

## Infraestrutura AWS

Configurada manualmente. Checklist de referência:

- **S3 bucket** — static website hosting habilitado (ou acesso exclusivo via CloudFront OAC)
- **CloudFront distribution** — apontando para o bucket, `index.html` como default root object, HTTPS via ACM certificate (região `us-east-1` obrigatória para CloudFront)
- **IAM user/role** — permissões: `s3:PutObject`, `s3:ListBucket`, `cloudfront:CreateInvalidation`
- **Route 53** — CNAME `onepiece.felipeduribeiro.com.br` → domínio do CloudFront

### GitHub Secrets necessários

| Secret | Descrição |
|---|---|
| `AWS_ACCESS_KEY_ID` | Chave IAM |
| `AWS_SECRET_ACCESS_KEY` | Secret da chave IAM |
| `BUCKET_NAME` | Nome do bucket S3 |
| `CLOUDFRONT_DISTRIBUTION_ID` | ID da distribuição (opcional — ativa invalidação de cache) |

> A região está hardcoded como `us-east-1` no workflow. Altere `aws-region` em `.github/workflows/update.yml` se o bucket estiver em outra região.

---

## Detalhes técnicos relevantes

**Deduplicação de imagens:** antes de baixar, o pipeline lista os objetos já presentes em `s3://BUCKET/static/Volume_*.webp` via boto3 e pula os que já existem. Isso evita re-download de ~100 imagens a cada execução.

**Estratégia de upload:**
- `index.html` — sempre sobrescrito com `aws s3 cp` (regenerado a cada run)
- `static/` — sincronizado com `aws s3 sync` **sem** `--delete` (imagens só acumulam, nunca são removidas do S3)

**Deduplicação de volumes entre arcos:** o wiki do Fandom atribui alguns volumes a múltiplos arcos (ex: volume 1 aparece em Romance Dawn e Orange Town). O pipeline resolve isso construindo um mapeamento autoritativo `volume→arco` onde arcos menores têm prioridade (`setdefault`), e usando esse mapeamento invertido para montar as listas de volumes por arco no template. Cada volume aparece em exatamente um arco.

**Ordem dos arcos:** a API do Fandom retorna arcos por timestamp de criação da wiki, não por ordem da história. O pipeline ordena pelo menor volume de cada arco no mapeamento final.

**Override manual:** o volume 111 é forçado para o arco Elbaph porque o wiki do Fandom tem dados incorretos para ele.

**Invalidação de CloudFront:** o step está comentado no workflow. Para ativar, adicione o secret `CLOUDFRONT_DISTRIBUTION_ID` e descomente o step em `.github/workflows/update.yml`.
