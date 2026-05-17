# ClaudeRedditor

Monitor Reddit y HackerNews para contenido relevante, clasifica con Claude AI, genera newsletters en español y produce podcasts conversacionales con TTS.

## ¿Qué hace?

- **Scraping multi-fuente**: Reddit (RSS/PRAW) + HackerNews (Firebase API)
- **Clasificación IA**: Claude Haiku categoriza posts como SIGNAL/NOISE/META con sistema multi-tag
- **Digest diario**: Newsletter en español desde los mejores posts SIGNAL
- **Web viewer**: Sitio Astro estático para explorar digests y bookmarks
- **Pipeline de podcast**: Genera episodios conversacionales completos (guion + audio TTS)
- **Multi-proyecto**: Configuraciones aisladas por tema (AI/LLM, mundo del vino)
- **Caché**: MariaDB reduce costes de API un 70-80%

## Quick Start

```bash
source .venv/bin/activate
pip install -e .

# Copiar y configurar variables de entorno
cp .env.example .env  # Añadir ANTHROPIC_API_KEY

# Escanear y generar digest
./reddit-analyzer scan claudeia --limit 50
./reddit-analyzer digest --project claudeia
```

## CLI Reference

### Escaneo y clasificación

```bash
./reddit-analyzer scan claudeia --limit 20          # Todas las fuentes
./reddit-analyzer scan claudeia --source reddit      # Solo Reddit
./reddit-analyzer scan claudeia --source hackernews  # Solo HackerNews
./reddit-analyzer compare claudeia --limit 30        # Comparar subreddits
```

### Digest

```bash
./reddit-analyzer digest --project claudeia           # Markdown + JSON (por defecto)
./reddit-analyzer digest --project claudeia --dry-run # Previsualizar sin guardar
./reddit-analyzer digest --project claudeia --limit 7 # Top 7 posts
```

Salida: `outputs/digests/digest_{project}_{date}_{NN}.md` + `outputs/web/{project}_{date}-{NN}.json`

### Podcast pipeline

El pipeline toma un digest existente y produce un episodio completo en tres etapas:

| Etapa | Comando | Salida |
|-------|---------|--------|
| 1. Editor | `podcast edit` | `outputs/podcast/{stem}_episode.json` — estructura del episodio |
| 2. Guionista + Intro/Outro | `podcast script` | `outputs/podcast/{stem}_dialog.json` — diálogo completo |
| 3. Audio TTS | `podcast audio` | `outputs/podcast/{stem}.mp3` — audio via Deepgram |

```bash
# Pipeline completo (ejecutar en orden)
./reddit-analyzer podcast edit --project claudeia
./reddit-analyzer podcast script --project claudeia
./reddit-analyzer podcast audio --project claudeia

# Opciones útiles
./reddit-analyzer podcast edit --project claudeia --dry-run          # Previsualizar
./reddit-analyzer podcast script --project claudeia --blocks 2,3     # Regenerar bloques concretos
./reddit-analyzer podcast audio --project claudeia --date 2026-05-01 --digest-id 02

# Requiere: DEEPGRAM_API_KEY en .env
```

### Bookmarks

```bash
./reddit-analyzer bookmark show latest            # Ver últimas historias bookmarkeables
./reddit-analyzer bookmark add 2026-05-01-003     # Añadir bookmark
./reddit-analyzer bookmark add 2026-05-01-003 --note "Interesante para el blog"
./reddit-analyzer bookmark list --status to_read  # Listar por estado
./reddit-analyzer bookmark done 2026-05-01-003    # Marcar como leído
```

### Base de datos y utilidades

```bash
./reddit-analyzer init-db                                     # Crear tablas
./reddit-analyzer config                                      # Ver proyectos y config
./reddit-analyzer history --project claudeia                  # Historial de digests
./reddit-analyzer cache-stats                                 # Estadísticas de caché
./reddit-analyzer regenerate-json --project claudeia --date all  # Reconstruir JSONs desde DB
```

### Web viewer

```bash
cd web && npm run dev    # http://localhost:4321
cd web && npm run build  # Build estático a web/dist/
```

## Automatización con n8n

El workflow **"ClaudeIA Gazzette"** (`n8n_gazzette.json`) automatiza el pipeline completo cada mañana.

### Diagrama del workflow
Por proyecto `claudeia` y `wineworld` esta seria la secvuencia de llamadas para generar un episodio de podcast.
1. daily-scan.sh / ./reddit-analyzer scan "claudeia" --limit 50 
    > Scrapping de HN y Reddit.
    Los resultados se guardan en la MariaDB
2. ./reddit-analyzer digest --project claudeia --limit 7
    > generar newsletter con Claude de los 7 mejores posts SIGNAL no enviados aún,  marcandolos como enviados en DB.
    outputs/digests/digest_claudeia_2026-05-17_01.md   ← newsletter en markdown
    outputs/web/claudeia_2026-05-17-01.json            ← JSON para el web viewer
    outputs/web/latest.json                            ← symlink al JSON anterior
3. process the filename from the output of previous step and sent it by mail
4. ./scripts/deploy-web.sh
    > Despliega web viewer a Cloudflare Pages
    > version local en web/dist/ 
5. ./reddit-analyzer podcast edit   --project claudeia --date 2026-05-17
    > genera estructura del episodio (modo editor)
    outputs/podcast/claudeia_2026-05-17_episode.json
6. ./reddit-analyzer podcast script --project claudeia --date 2026-05-17
    > genera diálogo completo (modo guionista)
    outputs/podcast/claudeia_2026-05-17_dialog.json 
7. ./reddit-analyzer podcast audio --project claudeia --date 2026-05-17
    > genera audio via Deepgram
    outputs/podcast/claudeia_2026-05-17.mp3


```
[Cron 06:00] ──┬──► [daily-scan.sh] ──► [digest claudeia --limit 7]
[Webhook POST] ┘         │                         │
                         │                    ┌────┴────────────────────┐
                         │                    │                         │
                         │            [Filename extractor]        [deploy-web.sh]
                         │              (extrae path + fecha)
                         │                    │
                         │            ┌───────┴───────────────┐
                         │            │                       │
                         │     [Mail executor]     [podcast edit+script+audio]
                         │     (email adjunto              │
                         │      a zelloss@gmail.com)  [JS formatter]
                         │                                   │
                         │                          [Telegram notification]
                         │
                         └──► [digest wineworld --limit 15]
                                        │
                               [Wine Filename extractor]
                                        │
                               [Wine Mail executor]
                               (email adjunto a zelloss@gmail.com)
```

### Nodos del workflow

| Nodo | Tipo | Función |
|------|------|---------|
| **Trigger mañanero** | Schedule (`0 6 * * *`) | Dispara el workflow a las 06:00 |
| **Webhook** | POST `/gazette` | Permite lanzar manualmente vía HTTP |
| **daily scan** | SSH → seb01 | Ejecuta `daily-scan.sh` (escanea Reddit + HN) |
| **AI Python sentiment digester** | SSH → seb01 | `digest --project claudeia --limit 7` |
| **Filename extractor** | JavaScript | Extrae path del digest, fecha y digestId del stdout |
| **Mail executor** | SSH → seb01 | Envía el markdown del digest por email adjunto |
| **site uploader** | SSH → seb01 | Ejecuta `deploy-web.sh` (build + deploy Astro) |
| **notebooklm_exporter** | SSH → seb01 | Pipeline podcast: `edit` + `script` + `audio` |
| **Code in JavaScript** | JavaScript | Formatea resultado del podcast (limpia ANSI/Rich) |
| **Send a text message** | Telegram | Notifica resultado por Telegram (bot LaBorrachaAlerting) |
| **Wine Python sentiment digester** | SSH → seb01 | `digest --project wineworld --limit 15` |
| **Wine Filename extractor** | JavaScript | Extrae path del digest de vino |
| **Wine Mail executor** | SSH → seb01 | Envía digest de vino por email adjunto |

**Notas:**
- Todas las conexiones SSH usan clave privada (`SSH Seb 01`)
- El error del workflow se delega a un workflow separado de alertas
- El Webhook acepta `POST /gazette` para lanzados manuales o desde otros sistemas

## Arquitectura del paquete

`cli/` es la capa de presentación (equivalente a `routers/` en FastAPI): cada fichero agrupa un conjunto de comandos Typer y es lo único que el usuario final toca. Los módulos de dominio (`analyzer.py`, `classifier.py`, `digest.py`, etc.) viven sueltos en la raíz del paquete — Typer no impone una carpeta `services/`, así que es la convención habitual en proyectos medianos.

```
src/claude_redditor/
├── cli/          ← presentación: comandos Typer (scan, digest, podcast…)
├── core/         ← modelos y enums compartidos
├── db/           ← repositorio + ORM (todo el acceso a MariaDB)
├── scrapers/     ← acceso a datos externos (Reddit, HackerNews)
├── projects/     ← configuración por proyecto (config.yaml + prompts)
└── *.py          ← servicios de dominio: classifier, analyzer, digest, reporter…
```
el punto de entrada es cli/__init__.py. :
```
  cli/__init__.py          ← PUNTO DE ENTRADA: ensambla el app Typer y llama a main()
      │
      ├── cli/scan.py      ← comandos: scan, compare
      ├── cli/digest_cmd.py
      ├── cli/bookmark.py
      ├── cli/db.py
      ├── cli/info.py
      └── cli/podcast.py
              │
              ▼  importan de:
      analyzer.py          ← métricas y motor de análisis cacheado (447L)
      classifier.py        ← lógica de clasificación con Claude, batch=20 (344L)
      digest.py            ← generación de newsletter + JSON export (651L)
      reporter.py          ← generación de report para terminal/JSON (258L)
      projects.py          ← auto-descubrimiento de proyectos en /projects/ (191L)
      content_fetcher.py   ← fetch full content si selftext truncado (135L)
      config.py            ← settings pydantic (82L)
      logcentral_setup.py  ← inicialización de logging (49L)
```

## Estructura de proyectos

Cada proyecto es autocontenido en `src/claude_redditor/projects/{name}/`:

```
projects/
├── claudeia/           # AI/LLM content → podcast semanal
│   ├── config.yaml     # Subreddits, HN keywords, config del podcast
│   └── prompts/        # classify.md, digest.md, podcast_editor.md, ...
└── wineworld/          # Mundo del vino → blog
    ├── config.yaml
    └── prompts/
```

Para añadir un nuevo proyecto: ver [docs/HOW-TO-ADD-PROJECT.md](docs/HOW-TO-ADD-PROJECT.md).

## Variables de entorno

```bash
# Requerido
ANTHROPIC_API_KEY=sk-ant-...

# Opcional (MariaDB — muy recomendado)
MYSQL_HOST=localhost
MYSQL_USER=user
MYSQL_PASSWORD=pass
MYSQL_DATABASE=reddit_analyzer

# Opcional (PRAW — scraping Reddit más rápido)
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...

# Requerido para podcast audio
DEEPGRAM_API_KEY=...
```

## Documentación

- [Architecture](ARCHITECTURE.md) — Decisiones técnicas y diseño del sistema
- [Quick Start](QUICKSTART.md) — Tutorial completo (5 min)
- [Briefing](BRIEFING.md) — Visión general del proyecto
- [How to Deploy](docs/HOW-TO-DEPLOY.md) — Automatización con n8n/cron
- [How to Add Project](docs/HOW-TO-ADD-PROJECT.md) — Crear nuevo proyecto

## Requisitos

- Python 3.11+
- Anthropic API key (requerido)
- MariaDB (opcional, recomendado para caché)
- Reddit API credentials (opcional, scraping más rápido)
- Deepgram API key (requerido para podcast audio)
- n8n (opcional, para automatización del pipeline completo)
