---
name: linkedin-posts
description: Keep the local LinkedIn curation (linkedin/) in sync with the project as features ship and versions release, and publish the next queued post. Use when adding/changing user-facing features, publishing a release, changing README features or the docs site, or when asked to "atualizar posts do linkedin", "criar post", "post da versão", "release post", "postar o próximo", "publica o próximo" or "divulgação".
compatibility: opencode
---

# LinkedIn Posts

`linkedin/` guarda a curadoria (posts, cards, fila). É **local (gitignored)** —
nunca commitar. Existem **duas árvores independentes**: `pt-br/` (fonte) e
`en/`. O mesmo post existe nos dois lados com o **mesmo NN e slug**.

## Estrutura

```
linkedin/
├── README.md        ← regras + índice (atualizar ao adicionar post)
├── metrics.json     ← versão, testes, cobertura, gate, features
├── export.py        ← .md → .txt/.json + manifest (--lang)
├── publish.py       ← publisher via API + fila por idioma
├── check_drift.py   ← anti-drift (versão/testes/espelho/índice)
├── assets/
│   └── gen_cards.py ← cards 1200×627 (HTML → PNG via Playwright)
├── pt-br/ en/       ← published.json, launch/, features/, releases/, assets/
└── exports/         ← saída local: .txt/.json/manifest.json
```

## Publicação em fila

A fila são os posts de **feature** de cada idioma, em ordem numérica. O estado
fica em `<lang>/published.json` (local) e registra o que saiu, quando e o URN.

Quando o usuário pedir **"poste o próximo"**, **"posta o próximo"**,
**"publique o próximo"** ou equivalente, publique direto (sem parar para
confirmação) e registre:

```sh
python linkedin/publish.py --lang en --list             # fila e próximo
python linkedin/publish.py --lang en --next             # dry-run
python linkedin/publish.py --lang en --next --publish   # publica
python linkedin/publish.py --lang pt-br --list          # fila pt-BR
```

Depois informe o **ID do post**, a **data** e o **URN/link** impressos.

- Se o comando falhar com `pending`/`failed`, **não insista**: confira no
  LinkedIn e use `--mark <id>` (se saiu) ou `--unmark <id>` (se não saiu).
- Post publicado manualmente: `--mark <id> [--at <data>] [--urn <urn>]`.
- Post que **não** vai ser publicado (release antigo, feature descartada):
  `--skip <id>` registra o estado `pulado`; a fila de features avança por cima
  dos pulados e o `--list` mostra a data do skip.
- Lançamento e releases ficam **fora da fila**: `--only launch/01-launch`,
  `--only releases/01-release-v0.13.0`.

Credenciais em `linkedin/.env.local` (gitignored): `LINKEDIN_ACCESS_TOKEN`,
`LINKEDIN_VERSION` (opcional) e `LINKEDIN_AUTHOR_URN` (opcional; deriva via
`/v2/userinfo`).

## Cards

Todo post traz um card 16:9 no topo, referenciado por `../assets/<id>.png`
(nas duas árvores, o mesmo caminho relativo). Gere com:

```sh
python linkedin/assets/gen_cards.py
python linkedin/assets/gen_cards.py --lang pt-br
python linkedin/assets/gen_cards.py --only 04-assinatura-de-relatorios
```

O card é HTML renderizado no Chromium que já é dependência da lib. Ao criar um
post, adicione o card ao `CARDS` do `gen_cards.py` (variantes pt-br e en).

## Modelo do post (obrigatório)

1. **Gancho** — 1 linha, começa com emoji.
2. **Imagem** — `![título](../assets/<id>.png)` logo após o gancho.
3. **Contexto** — 1 parágrafo do problema.
4. **Bullets** — 3–4 itens com `**negrito**` e marcador emoji.
5. **Fecho** — 1–2 frases de benefício.
6. **CTA + links** — `👇` e os três links (site, GitHub, PyPI).
7. **Hashtags** — última linha.

Números reais **sempre**: `pytest --collect-only -q` (testes), `pytest --cov`
(cobertura), `git describe --tags` (versão), `CHANGELOG.md` (entregas). Nunca
estimar.

## Gatilhos — o que fazer quando o projeto muda

| Mudança no projeto | Ação |
|---|---|
| Usuário pede para publicar o próximo | `publish.py --next --publish`; relatar ID/data/URN |
| Feature nova/alterada (bullet do README) | criar/atualizar post nas duas árvores |
| Versão publicada (tag + GitHub Release) | criar post de release nas duas árvores, com números reais |
| Feature removida/renomeada ou comportamento alterado | corrigir os posts que a citam |
| Números mudam (testes/cobertura/versão) | atualizar `metrics.json` e o último post de release; rodar `check_drift.py` |
| README/docs site mudam | revisar posts afetados (claims de implementação) |

## Workflow — post de feature

1. Identifique a feature no `README.md` e no `docs/guide.md`.
2. Próximo `NN` em `features/` (`pt-br` e `en` com o mesmo NN/slug).
3. Escreva pt-BR (fonte) e traduza para `en/`.
4. Adicione o card ao `gen_cards.py` e rode o script.
5. Atualize a tabela "Features → posts" do `linkedin/README.md`.

## Workflow — post de release

1. Versão da última tag (`git describe --tags`) → `releases/NN-release-vX.Y.Z`
   nas duas árvores.
2. Entregas: `CHANGELOG.md` (seção da versão) + `docs/ROADMAP.md` (Done).
3. Números reais: testes, cobertura e faixa de Python do `pyproject.toml`.
4. Destaque 3–5 itens de peso + correções relevantes.
5. Card com os números no subtítulo; atualize as notas por release.

## Regras

- **pt-BR é a fonte; en espelho** (mesmo NN e slug).
- **Não reescrever posts antigos publicados** (são histórico); só o atual/próximo.
- **Sem números/locais inventados**: derive do repo.
- Toda afirmação de implementação deve refletir o estado atual (ex.: a lib não
  tem servidor; saídas são PDF/XLSX/CSV/HTML; assinatura é selo, não PAdES).
- Links fixos ao final: **site** (`https://thepaneb.github.io/isis-report-lib/`),
  **GitHub** (`https://github.com/thepaneb/isis-report-lib`) e **PyPI**
  (`https://pypi.org/project/isis-report-lib/`); hashtags na última linha.

## Verificação (obrigatória)

- [ ] pt-br e en com o mesmo NN/slug para cada post novo
- [ ] card em `<lang>/assets/` e referenciado no topo
- [ ] os três links (site, GitHub, PyPI) + hashtags
- [ ] emojis no gancho, no CTA, nos links e nos bullets
- [ ] números conferem com o repo (testes/cobertura/tag)
- [ ] `python linkedin/check_drift.py`
- [ ] `python linkedin/export.py` sem avisos
- [ ] `git status` limpo (a pasta é gitignored)

## Armadilhas

- `linkedin/` e os `published.json` são **locais**: não versionar/commitar.
- **Little Text:** o `commentary` da Posts API trata `(`, `)`, `[`, `]`, `@`,
  `*`, `_`, `~`, `|`, `{}`, `<>` e `\` como markup; sem escape o post trunca no
  primeiro `(` e ainda retorna **201**. O `publish.py` escapa automaticamente;
  cópia manual no editor web não é afetada.
- `--next` **para** se houver `pending`/`failed`; confira no LinkedIn antes de
  `--mark`/`--unmark` para não duplicar.
- O lançamento (`launch/01-launch`, EN) já saiu em 2026-11-10 e está registrado
  no estado: não republicar.
- `docs/linkedin/` **não** existe aqui de propósito: `docs/` é o site Zensical
  com build `--strict`.
- Não editar `site/` (artefato de build) nem enfiar post em `docs/`.
