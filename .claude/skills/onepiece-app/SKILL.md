---
name: onepiece-app
description: >
  Fluxo completo de validação local antes de qualquer git push no projeto One Piece Collection.
  Use esta skill SEMPRE que arquivos em website/ forem alterados (Python, CSS, template HTML, YAML)
  e ANTES de qualquer commit ou push. Triggers: "preview", "mostra antes do push", "valida local",
  "gera o output", "sobe o 8080", "testa localmente", "pode fazer o push?", ou qualquer pedido de
  ver o resultado antes de deployar.
---

# Preview — Validação local antes do push

Este projeto é 100% serverless: o pipeline Python roda no GitHub Actions, gera um site estático e
faz upload para S3. Não há servidor de aplicação. Todo o resultado visível ao usuário vem do que
o pipeline gerar — por isso validar localmente antes do push é essencial.

## O que esta skill faz

1. Limpa o `output/` para garantir geração do zero
2. Roda o pipeline com `DRY_RUN=true` (sem tocar no S3)
3. Garante que o servidor HTTP está no ar na porta 8080
4. Pede ao usuário que valide em http://localhost:8080
5. Aguarda aprovação explícita antes de fazer commit e push

## Passos

### 1. Limpar output/

Remove todos os arquivos gerados anteriormente para garantir que o pipeline parte do zero:

```powershell
Remove-Item -Recurse -Force "output" -ErrorAction SilentlyContinue
```

Confirme que o diretório foi removido antes de continuar.

### 2. Rodar o pipeline localmente

No Windows (PowerShell):
```powershell
cd website
$env:DRY_RUN="true"
$env:PYTHONIOENCODING="utf-8"
python volume_update.py
cd ..
```

O pipeline vai:
- Descobrir o último volume via API do Fandom
- Coletar todos os arcos e mapear volumes (sem duplicatas)
- Baixar todas as capas em paralelo (8 workers) para `output/static/`
- Para volumes novos sem versão 1000px no CDN: fallback automático para `/revision/latest`
- Gerar `output/index.html` via Jinja2

Aguarde a conclusão — pode levar 1-3 minutos pelo download das imagens. Mostre as últimas linhas
do output para o usuário confirmar que terminou sem erros.

**Sinais de sucesso esperados:**
- `✅ index.html gerado → ...`
- `✅ Finalizado!`
- Volumes recentes podem mostrar `⚠️ Volume X: 1000px indisponível, tentando resolução original...` — isso é normal, não é erro

### 3. Garantir o servidor HTTP na porta 8080

Verifique se a porta já está ocupada:
```powershell
netstat -an | Select-String ":8080"
```

- **Se a porta já estiver em uso (LISTENING):** o servidor já está rodando — informe o usuário e
  peça para dar F5 no browser
- **Se não estiver em uso:** suba o servidor em background:
  ```powershell
  python -m http.server 8080 --directory output
  ```
  Use `run_in_background: true` para não bloquear a conversa

### 4. Pedir validação ao usuário

Informe:
> "Pipeline gerado. Abra ou atualize **http://localhost:8080** para conferir. Quando estiver
> satisfeito, me diga que pode fazer o push."

**Aguarde resposta explícita do usuário antes de prosseguir.** Não faça commit nem push sem
aprovação. Exemplos de aprovação: "pode fazer o push", "ok", "aprovado", "commita", "está bom".

### 5. Commit e push

Após aprovação explícita:

1. Identifique os arquivos modificados em `website/` com `git status`
2. Adicione apenas os arquivos fonte (nunca o `output/`):
   ```bash
   git add website/
   ```
3. Crie um commit descritivo sobre o que foi alterado
4. Faça push:
   ```bash
   git push
   ```

O push em `website/data/collection.yaml` dispara o GitHub Actions automaticamente. Outros
arquivos em `website/` também disparam o workflow se o path filter do workflow incluir o caminho.

## Contexto técnico importante

**DRY_RUN=true:** pula completamente a listagem e upload do S3. Baixa todas as imagens
diretamente do Fandom para `output/static/`. O `output/` está no `.gitignore` — nunca é commitado.

**Detecção de placeholders:** em runs reais (sem DRY_RUN), o pipeline compara o tamanho de cada
`Volume_*.webp` no S3 com o `NoPicAvailable.webp` local. Arquivos do mesmo tamanho são
re-baixados automaticamente — isso auto-corrige volumes que saíram depois do primeiro deploy.

**Volume 111:** sempre forçado para `Elbaph_Arc` por override hardcoded no pipeline.

**Volume 115 (e futuros recém-lançados):** podem aparecer como NoPicAvailable se o Fandom ainda
não publicou a imagem. Isso é esperado e correto — não é um bug.

**GitHub Actions:** o workflow em `.github/workflows/update.yml` roda o pipeline completo contra
o S3 real. O resultado vai para `onepiece.felipeduribeiro.com.br` via CloudFront.
