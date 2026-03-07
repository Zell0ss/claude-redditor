# ClaudeRedditor

Monitor Reddit/HN for AI posts, classify with Claude, generate Spanish newsletters.

## Quick Start

```bash
# Install
source .venv/bin/activate
pip install -e .

# Configure (add ANTHROPIC_API_KEY)
cp .env.example .env

# Scan & generate digest
./reddit-analyzer scan claudeia --limit 50
./reddit-analyzer digest --project claudeia
```

## What It Does

- **Multi-source scraping**: Reddit (RSS/PRAW) + HackerNews (Firebase API)
- **AI classification**: Claude Haiku categorizes posts as SIGNAL/NOISE/META with multi-tier tags
- **Deep analysis**: 9-tier classification system for SIGNAL posts (tech stack, patterns, strategy)
- **Daily digest**: Auto-generates Spanish newsletter from top SIGNAL posts
- **Multi-project**: Isolated configs for different topics (AI podcast, wine blog)
- **Cost optimization**: MariaDB cache reduces API costs by 70-80%

## Documentation

- [Architecture](ARCHITECTURE.md) - How it works, key decisions
- [Quick Start](QUICKSTART.md) - Full tutorial (5 min)
- [Briefing](BRIEFING.md) - Project overview for Claude AI
- [How to Deploy](docs/HOW-TO-DEPLOY.md) - Cron/N8N automation
- [How to Add Project](docs/HOW-TO-ADD-PROJECT.md) - Create new topic

## CLI Reference

### `podcast` — Genera un podcast desde un digest

Toma un digest markdown existente, lo sube a Google NotebookLM como fuente,
genera un Audio Overview conversacional en español con dos hosts IA, y descarga
el MP3 resultante.

**Prerequisito:** Tener un digest generado (`digest --project <proyecto>`).
La autenticación de NotebookLM debe estar configurada en `~/.notebooklm/storage_state.json`.

```
SYNOPSIS
    reddit-analyzer podcast --project NAME [OPTIONS]

OPTIONS
    --project, -p  NAME        (requerido) Nombre del proyecto. Debe existir en
                               src/claude_redditor/projects/. Ej: claudeia

    --date  YYYY-MM-DD         Fecha del digest a usar. Si hay varios ficheros
                               para esa fecha, usa el más reciente (_02 sobre _01).
                               Default: hoy.
                               Mutuamente excluyente con --file.

    --file  PATH               Path directo al fichero digest .md. Útil cuando
                               hay varios digests por día y quieres elegir uno
                               específico sin depender del orden.
                               Mutuamente excluyente con --date.

    --output-dir  PATH         Directorio donde se guarda el MP3.
                               Default: outputs/podcasts/
                               El nombre del fichero sigue el patrón:
                                 podcast_{project}_{date}.m4a          (con --date)
                                 podcast_{project}_{date}_{N}.m4a      (con --file)

    --focus  TEXT              Instrucción adicional de enfoque que se añade al
                               prompt de generación. Ej: "modelos de lenguaje"

    --cleanup / --no-cleanup   Si borrar el notebook de NotebookLM tras descargar
                               el audio. Default: --cleanup (borrar).
                               Usar --no-cleanup para inspeccionar el notebook
                               manualmente después.

    --dry-run                  Muestra el plan de ejecución (digest que se usaría,
                               path de salida, título del notebook) sin ejecutar
                               nada ni contactar con NotebookLM.
```

**Ejemplos:**

```bash
# Digest de hoy (el más reciente)
./reddit-analyzer podcast --project claudeia

# Fecha específica
./reddit-analyzer podcast --project claudeia --date 2026-03-03

# Fichero concreto cuando hay dos digests el mismo día
./reddit-analyzer podcast --project claudeia \
  --file outputs/digests/digest_claudeia_2026-03-04_02.md

# Guardar en directorio custom + enfoque temático
./reddit-analyzer podcast --project claudeia \
  --file /ruta/al/digest.md \
  --output-dir /data/voice_rec/ \
  --focus "modelos de lenguaje open source"

# Previsualizar sin ejecutar
./reddit-analyzer podcast --project claudeia --date 2026-03-03 --dry-run

# Mantener notebook en NotebookLM (para revisión manual)
./reddit-analyzer podcast --project claudeia --no-cleanup
```

**Salida:** El comando imprime el path del MP3 al finalizar, lo que permite
capturarlo desde scripts o pipelines (n8n, cron):

```bash
MP3=$(./reddit-analyzer podcast --project claudeia --output-dir /data/voice_rec/ | tail -1)
echo "Podcast generado en: $MP3"
```
#### para acordarse: 

```bash
./reddit-analyzer podcast --project claudeia --file outputs/digests/digest_claudeia_2026-03-05_01.md --timeout 1200 --output-dir /data/voice_rec/ 
```

**Errores comunes:**

| Mensaje | Causa | Solución |
|---------|-------|---------|
| `Autenticación de NotebookLM expirada` | El `storage_state.json` ha caducado | Ejecutar `notebooklm login` localmente y copiar el fichero a `~/.notebooklm/` |
| `No se encontró digest para project/fecha` | No existe ningún `.md` para ese proyecto y fecha | Ejecutar `digest --project <proyecto>` primero |
| `--date y --file son mutuamente excluyentes` | Se pasaron los dos flags a la vez | Usar solo uno |
| `Fichero no encontrado` | El path pasado a `--file` no existe | Verificar el path con `ls outputs/digests/` |

---

## Requirements

- Python 3.11+
- Anthropic API key (required)
- MariaDB (optional, recommended for caching)
- Reddit API credentials (optional, faster scraping)
