# ClaudeRedditor - Briefing para Claude Web

Este documento está diseñado para que Claude Web (sin acceso al código) pueda entender el proyecto y discutir sobre él de forma informada.

---

## Qué es este proyecto

ClaudeRedditor es una herramienta CLI que analiza posts de Reddit y HackerNews para separar el contenido útil ("signal") del ruido ("noise"). Usa Claude como clasificador, una base de datos MariaDB como caché, y genera newsletters diarios en español.

El caso de uso principal: monitorizar comunidades online sobre un tema específico (ej: IA, vino) y generar un digest diario con los posts más relevantes, filtrando el clickbait y las afirmaciones sin fuentes.

---

## Cómo funciona (flujo de datos)

```
1. SCRAPING
   Reddit (RSS o API) ──┐
                        ├──► Posts crudos
   HackerNews (Firebase)┘

2. CACHE
   Posts crudos ──► MariaDB (evita re-procesar)

3. CLASIFICACIÓN
   Posts nuevos ──► Claude API ──► Categoría + Red Flags + Confianza

4. TRUNCADO INTELIGENTE
   - Posts SIGNAL/META: se guardan hasta 5000 caracteres
   - Posts NOISE/UNRELATED: se truncan a 500 caracteres (ahorro de storage)

5. DIGEST (opcional)
   Posts SIGNAL no enviados ──► Claude genera artículo en español ──► Markdown
```

---

## Sistema de clasificación

### Las 10 categorías

| Grupo | Categoría | Qué significa |
|-------|-----------|---------------|
| **SIGNAL** | `technical` | Prompts, workflows, código funcional |
| | `troubleshooting` | Problemas reales con soluciones |
| | `research_verified` | Papers/experimentos con fuentes verificables |
| **NOISE** | `mystical` | Afirmaciones de consciencia sin evidencia |
| | `unverified_claim` | Aserciones técnicas sin fuentes |
| | `engagement_bait` | Clickbait puro |
| **META** | `community` | Discusión sobre el subreddit |
| | `meme` | Humor/entretenimiento |
| **OTHER** | `outlier` | No encaja claramente |
| **UNRELATED** | `unrelated` | Fuera del tema configurado |

### Red flags que se detectan

El clasificador busca patrones específicos que indican contenido problemático:

1. **no_source**: "researchers say", "studies show" (sin citar la fuente)
2. **link_in_bio**: "check my profile", "link in bio" (autopromoción)
3. **mystical_language**: "consciousness emerged", "sentient", "awakening"
4. **cannot_explain**: "researchers puzzled", "mysterious", "defies explanation"
5. **sensationalist**: "you won't believe", "shocking", "mind-blowing"
6. **precise_numbers**: Números muy precisos sin fuente (ej: "95.7% más efectivo")

### Signal Ratio

La métrica principal es el "signal ratio":

```
Signal Ratio = posts SIGNAL / (posts totales - posts UNRELATED)
```

Se excluyen los UNRELATED porque no son ruido del tema, simplemente están fuera de scope.

| Ratio | Calificación |
|-------|--------------|
| ≥70% | Excelente |
| 50-69% | Bueno |
| 30-49% | Regular |
| <30% | Bajo |

---

## Multi-proyecto

El sistema soporta múltiples proyectos aislados como **entidades autocontenidas**. Cada proyecto es un directorio en `projects/` con:

```
projects/
├── claudeia/
│   ├── config.yaml        # topic, subreddits, hn_keywords
│   └── prompts/
│       ├── classify.md    # Prompt de clasificación (categorías específicas)
│       └── digest.md      # Prompt de digest (formato newsletter)
└── wineworld/
    ├── config.yaml
    └── prompts/
        ├── classify.md    # Categorías específicas para vino
        └── digest.md      # "La Gaceta del Vino"
```

### config.yaml de un proyecto

```yaml
name: claudeia
description: "AI and LLM content, focused on Claude"
topic: "AI and Large Language Models, particularly Claude and Claude Code"

sources:
  reddit:
    subreddits:
      - ClaudeAI
      - Claude
      - ClaudeCode
  hackernews:
    keywords:
      - claude
      - anthropic
      - ai
      - llm
```

### Añadir un nuevo proyecto

**Zero code changes** - solo crear directorio:

1. Crear `projects/{nombre}/config.yaml`
2. Crear `projects/{nombre}/prompts/classify.md` (copiar de existente y adaptar)
3. Crear `projects/{nombre}/prompts/digest.md` (copiar de existente y adaptar)
4. Usar `--project {nombre}` en comandos CLI

El sistema **autodescubre** proyectos al escanear `projects/` buscando directorios con `config.yaml`.

### Aislamiento de datos

- Datos aislados en la base de datos (columna `project` en todas las tablas)
- **Decisión de diseño importante**: Un mismo post puede existir en dos proyectos con clasificaciones diferentes. Por ejemplo, un post sobre "IA aplicada al vino" podría ser:
  - `technical` en el proyecto "wineworld"
  - `unrelated` en el proyecto "claudeia"

Esto es intencional: la clasificación depende del contexto del proyecto.

---

## Truncado de selftext

Esta es una optimización de storage que puede causar confusión:

1. **En clasificación**: Se usa el selftext completo (o hasta 5000 chars)
2. **Al guardar en DB**:
   - SIGNAL/META → hasta 5000 chars
   - NOISE/UNRELATED → truncado a 500 chars
3. **En digest**: Si detectamos que el selftext fue truncado (longitud exacta = 5000), intentamos recuperar el contenido completo via URL

```python
# Detección de truncado en digest
if len(post.selftext) == 5000 and post.url:
    full_content = fetch_full_content(post.url)
```

---

## El digest (newsletter)

El digest genera un newsletter en español llamado "La Gaceta IA" con los posts SIGNAL que aún no se han enviado.

### Formato de salida

```markdown
# La Gaceta IA
*Fecha: 2024-01-15*

## Artículo 1: [Título del post]

**Fuente**: r/ClaudeAI | u/author | technical
**URL**: https://reddit.com/...

[Artículo generado por Claude en español, 2-3 párrafos]

---

## Artículo 2: ...
```

### Proceso de generación

1. Query: posts SIGNAL donde `sent_in_digest_at IS NULL`
2. Por cada post:
   - Si selftext truncado → fetch contenido completo
   - Claude genera artículo en español
   - Claude extrae puntos clave
3. Guardar markdown en `outputs/digests/`
4. Marcar posts como enviados (actualizar `sent_in_digest_at`)

---

## Comandos CLI disponibles

| Comando | Qué hace |
|---------|----------|
| `scan <subreddit>` | Escanea un subreddit de Reddit |
| `scan-hn` | Escanea HackerNews por keywords |
| `compare` | Compara signal ratio entre subreddits |
| `digest` | Genera el newsletter diario (markdown/json/both) |
| `config` | Muestra configuración actual |
| `init-db` | Inicializa/migra la base de datos |
| `history` | Muestra clasificaciones históricas |
| `cache-stats` | Estadísticas del caché |
| `bookmark show <date>` | Ver stories de un digest JSON |
| `bookmark add <id>` | Añadir bookmark con notas |
| `bookmark list` | Listar bookmarks (filtrar por status) |
| `bookmark done <id>` | Marcar bookmark como completado |
| `bookmark status <id> <status>` | Cambiar estado del bookmark |

---

## Stack técnico

- **Python 3.11+** con **Typer** para CLI (estructura modular en `cli/`)
- **Claude API** (Anthropic) para clasificación y generación
- **MariaDB** para caché (opcional pero recomendado)
- **SQLAlchemy** como ORM
- **pydantic-settings** para configuración (solo secrets en `.env`)
- **PyYAML** para configuración de proyectos
- **Reddit**: RSS por defecto, PRAW si hay credenciales
- **HackerNews**: Firebase API (sin auth, 500 req/min)

---

## Decisiones de diseño no obvias

1. **RSS por defecto para Reddit**: No requiere API key, suficiente para monitoreo básico

2. **Batch de 20 posts por llamada a Claude**: Balance entre tokens y latencia

3. **Truncado DESPUÉS de clasificar**: La clasificación ve todo el contenido, pero NOISE no merece storage

4. **Digest solo SIGNAL**: Los posts META (community, meme) no van al newsletter

5. **Español en digest**: El target es una newsletter en español, aunque las fuentes sean en inglés

6. **N8N para automatización**: Se integra con N8N para ejecución diaria via cron

7. **Proyectos como entidades autocontenidas**: Cada proyecto tiene su propio `config.yaml` y `prompts/`. Zero code changes para añadir un nuevo proyecto - solo crear directorio.

8. **Prompts específicos por proyecto**: El proyecto de vino tiene categorías diferentes (tasting, winemaking, viticulture) que el de IA (technical, troubleshooting). Cada proyecto define sus propios prompts de clasificación y digest.

9. **`.env` solo para secrets**: La configuración de proyectos (subreddits, topics, keywords) está en `projects/{name}/config.yaml`, no en variables de entorno.

---

## Estado actual (Enero 2026)

- ✅ 8 comandos CLI + 5 subcomandos bookmark (Typer, estructura modular en `cli/`)
- ✅ Multi-proyecto operativo con **auto-discovery**
- ✅ Proyectos como entidades autocontenidas (`projects/{name}/`)
- ✅ Reddit + HackerNews como fuentes
- ✅ Caché MariaDB
- ✅ Digest en español (markdown)
- ✅ Integración N8N documentada
- ✅ **Multi-tags**: topic_tags (array) + format_tag (single) en clasificaciones
- ✅ **JSON export**: `digest --format json` genera `outputs/web/{date}.json` + `latest.json` symlink
- ✅ **Bookmarks CLI**: show, add, list, done, status
- ✅ **ProjectLoader**: Auto-descubre proyectos desde `projects/`

**Roadmap activo** (ver `docs/handover_multitag_web.md`):
- ✅ Sprint 0: Schema (migration 006)
- ✅ Sprint 1: Multi-tags en clasificador
- ✅ Sprint 2: JSON export
- ✅ Sprint 3: CLI de bookmarks
- ✅ Sprint 3.5: Proyectos autocontenidos (config.yaml + prompts/)
- ⏳ Sprint 4: Web estática con Astro
- ⏳ Sprint 5: Automatización con cron

**Posibles mejoras futuras**:
- Más fuentes (Twitter/X, newsletters, blogs)
- Alertas en tiempo real
- Clasificación con embeddings (reducir costes API)

---

## Snippets clave (para referencia)

### Categorías y su clasificación

```python
class CategoryEnum(str, Enum):
    # SIGNAL (contenido útil)
    TECHNICAL = "technical"
    TROUBLESHOOTING = "troubleshooting"
    RESEARCH_VERIFIED = "research_verified"

    # NOISE (contenido problemático)
    MYSTICAL = "mystical"
    UNVERIFIED_CLAIM = "unverified_claim"
    ENGAGEMENT_BAIT = "engagement_bait"

    # META
    COMMUNITY = "community"
    MEME = "meme"

    # OTHER
    OUTLIER = "outlier"

    # UNRELATED
    UNRELATED = "unrelated"
```

### Red flags patterns

```python
RED_FLAG_PATTERNS = {
    "no_source": ["researchers say", "studies show", "experiments found"],
    "link_in_bio": ["link in bio", "check my profile"],
    "mystical_language": ["consciousness emerged", "sentient", "awakening"],
    "cannot_explain": ["can't explain", "researchers puzzled", "mysterious"],
    "sensationalist": ["you won't believe", "shocking", "mind-blowing"],
}
```

### Truncado inteligente

```python
# En analyzer.py - después de clasificar, antes de guardar
if CategoryEnum.is_low_value(category):  # NOISE o UNRELATED
    post['selftext'] = post['selftext'][:500]  # Truncar a 500 chars
# Si no es low_value, se guarda hasta 5000 chars
```

### Detección de contenido truncado en digest

```python
# En digest.py - si el selftext tiene exactamente 5000 chars, probablemente truncado
if item['selftext_truncated'] and post.get('url'):
    full_content = fetch_full_content(post['url'])
```

---

## Preguntas frecuentes para discusión

1. **¿Por qué no usar embeddings para clasificar?**
   - Coste vs precisión: Claude es más caro pero más preciso para detección de red flags

2. **¿Por qué 10 categorías y no menos?**
   - Granularidad: permite métricas más finas y reglas específicas por categoría

3. **¿Por qué español en el digest?**
   - Target audience: newsletter para comunidad hispanohablante de IA

4. **¿Por qué truncar NOISE a 500 chars?**
   - Storage: NOISE no se usa en digest, no vale la pena guardar todo

---

*Este briefing está actualizado a Enero 2026. Para detalles de implementación, consultar el código fuente.*
