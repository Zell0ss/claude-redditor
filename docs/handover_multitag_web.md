# 🎯 Roadmap ClaudeRedditor - Para Claude Code

## Contexto general

**Objetivo:** Evolucionar ClaudeRedditor para soportar multi-tags, generar JSON para una web estática, y permitir bookmarking de historias interesantes desde el CLI.

**Stack actual:** Python + MariaDB + CLI con Click

**Stack nuevo (web):** Astro + Tailwind + Cloudflare Pages

**Flujo deseado:**
1. Cron diario ejecuta scan + digest
2. Se genera markdown (para NotebookLM) + JSON (para web)
3. Web se rebuilds y deploya automáticamente
4. Usuario oye podcast, hace bookmarks desde CLI

---

## Sprint 0: Schema de base de datos

### Tarea 1: Añadir tabla de bookmarks

Crear tabla `bookmarks` con estos campos:
- `story_id` (VARCHAR 50, unique): ID tipo "2025-01-17-003"
- `digest_date` (DATE): Fecha del digest
- `bookmarked_at` (TIMESTAMP): Cuándo se marcó
- `notes` (TEXT nullable): Notas opcionales
- `status` (ENUM: 'to_read', 'to_implement', 'done'): Estado

Campos denormalizados para evitar JOINs:
- `story_title` (TEXT)
- `story_url` (TEXT)  
- `story_tags` (JSON): Array de topic_tags
- `story_category` (VARCHAR 50)

Índices: digest_date, status, bookmarked_at

### Tarea 2: Actualizar tablas de posts

Añadir a `reddit_posts` y `hn_items`:
- `topic_tags` (JSON nullable): Array de tags tipo ["prompts", "tools", "buildable"]
- `format_tag` (VARCHAR 50 nullable): Un solo tag tipo "tutorial", "showcase"
- `sent_in_digest_at` (TIMESTAMP nullable)
- `digest_date` (DATE nullable)

---

## Sprint 1: Multi-tags en clasificador

### Objetivo
El clasificador debe devolver `topic_tags` (array) y `format_tag` (string único) además de category/confidence/red_flags actuales.

### Tarea 1: Actualizar modelo Classification

Añadir campos:
- `topic_tags: List[str] = []`
- `format_tag: Optional[str] = None`

### Tarea 2: Actualizar prompt del clasificador

Añadir al prompt instrucciones para asignar:

**Topic Tags** (multi-select):
- `prompts`: Prompt engineering, system prompts, techniques
- `tools`: MCP servers, integrations, workflows, extensions
- `models`: Model capabilities, comparisons, benchmarks
- `research`: Papers, experiments, academic content
- `coding`: Code examples, repositories, implementations
- `buildable`: **Python-centric o prompts puros, sin dependencias externas ni hardware específico. Implementable inmediatamente por el usuario.**
- `hardware`: **Requiere hardware específico (cámaras, impresoras 3D, microcontroladores, IoT, sensores, dispositivos especializados)**
- `troubleshooting`: Bug fixes, solutions, workarounds
- `news`: Announcements, releases, updates
- `meta-tooling`: Tools about tools (productivity, automation)

**Format Tag** (single-select):
- `tutorial`: Step-by-step guide
- `showcase`: Show HN, project demos
- `discussion`: Open-ended conversation
- `question`: Help request, Q&A
- `resource`: Lists, collections, curated resources
- `code-snippet`: Contains extractable code or prompts (any language)

**Combinaciones útiles para priorizar:**
- `[buildable] + [code-snippet]` → "Puedo implementarlo esta tarde"
- `[code-snippet]` solo → "Tiene código pero puede necesitar ayuda con el lenguaje"
- `[hardware]` → "Depende de tener el hardware específico"
- `[buildable] + [hardware]` → Raro: "Script Python para hardware que ya tengo"

El JSON de respuesta debe incluir estos campos.

### Tarea 3: Guardar tags en DB

Cuando se clasifica un post, guardar topic_tags y format_tag en la DB (serializar topic_tags como JSON).

### Testing

El comando `scan` debe mostrar los tags al final:
```
Clasificados 10 posts:
✓ [technical] [prompts,tools] [tutorial] "Sistema de metacognición..."
✓ [research] [models] [showcase] "Benchmark de Claude 3.5..."
```

---

## Sprint 2: Exportar digest a JSON

### Objetivo
Nuevo formato de output del comando `digest`: además de markdown, poder generar JSON estructurado para consumir desde la web.

### Tarea: Nuevo flag `--format`

`digest --format=json` debe generar archivo JSON con esta estructura:

```json
{
  "digest_id": "2025-01-17",
  "generated_at": "2025-01-17T07:00:00Z",
  "stories": [
    {
      "id": "2025-01-17-001",
      "title": "...",
      "source": "r/ClaudeAI" o "HackerNews",
      "author": "u/...",
      "url": "...",
      "category": "technical",
      "topic_tags": ["prompts", "tools"],
      "format_tag": "tutorial",
      "summary": "...",  // El resumen generado por Claude
      "red_flags": []
    }
  ]
}
```

**Detalles:**
- El `id` es `{fecha}-{número secuencial:03d}`
- El `summary` se genera igual que ahora para el markdown
- Guardar en `outputs/web/{fecha}.json`
- Crear symlink `outputs/web/latest.json` que apunte al más reciente

**Nota:** El markdown actual sigue funcionando igual, esto es un formato adicional.

---

## Sprint 3: CLI de bookmarks

### Objetivo
Comandos CLI para gestionar bookmarks: añadir, listar, marcar como done.

### Comandos a crear

**1. `bookmark show <fecha>`**
- Lee el JSON de `outputs/web/{fecha}.json`
- Muestra todas las stories de ese digest con su ID, category, tags, título, URL
- Formato sugerido:
  ```
  📰 Digest: 2025-01-17
  
  2025-01-17-001: [technical] [prompts, tools] [tutorial]
    Sistema de metacognición con Claude
    https://reddit.com/...
  
  2025-01-17-002: [buildable] [coding] [code-snippet]
    MCP server para Notion
    https://github.com/...
  ```

**2. `bookmark add <story_id> [--note TEXT] [--status STATUS]`**
- Lee el JSON correspondiente al story_id (extraer fecha del ID)
- Busca la story en el JSON
- Guarda en tabla `bookmarks` (denormalizando: title, url, tags, category)
- Status default: `to_read`

**3. `bookmark list [--status STATUS] [--limit N]`**
- Lista bookmarks de la DB
- Filtrar por status (to_read, to_implement, done, all)
- Ordenar por bookmarked_at DESC
- Mostrar: status, título, tags, URL, nota, fecha guardado

**4. `bookmark done <story_id>`**
- Actualiza status del bookmark a 'done'

### Modelo ORM

Crear `models/bookmark.py` con clase Bookmark mapeando a la tabla.

---

## Sprint 4: Web estática con Astro

### Objetivo
Sitio web que muestra los digests y permite navegar por las historias, con tags visualizados.

### Setup del proyecto

Crear nuevo directorio `clauderedditor-web/` (fuera del repo Python):
```bash
npm create astro@latest clauderedditor-web
# Empty template, TypeScript strict
cd clauderedditor-web
npx astro add tailwind
npx astro add cloudflare
```

### Estructura de páginas

**1. `src/pages/index.astro`**
- Lee todos los JSON de `public/data/*.json`
- Muestra lista de los últimos 10 digests
- Link a cada uno

**2. `src/pages/digest/[date].astro`**
- Lee `public/data/{date}.json`
- Muestra todas las stories del digest
- Cada story muestra: título, source, tags (category + topic_tags + format_tag), summary, link

**3. Componentes**
- `StoryCard.astro`: Card individual de story
- `TagBadge.astro`: Badge de tag (diferentes colores según tipo)

### Data

Crear symlink `clauderedditor-web/public/data` → `../clauderedditor/outputs/web/`

Así Astro lee los JSON directamente.

### Estilos

Usar Tailwind. Algo limpio, minimalista, responsive. No hace falta nada fancy.

### Testing local

```bash
npm run dev  # → localhost:4321
npm run build  # → dist/
```

---

## Sprint 5: Automatización

### Objetivo
Script bash que ejecuta todo el flujo diario y deploya la web.

### Script a crear

`scripts/daily-digest.sh`:

1. Ejecutar scan de Reddit y HackerNews
2. Generar digest markdown
3. Generar digest JSON
4. CD a clauderedditor-web
5. Build (`npm run build`)
6. Deploy a Cloudflare Pages (`npx wrangler pages deploy dist/`)

Crear directorio `logs/` y guardar log del día.

### Crontab

Configurar para ejecutar diario a las 7 AM:
```
0 7 * * * /ruta/al/script/daily-digest.sh
```

### Cloudflare Setup

**Configuración una sola vez:**
```bash
npm install -g wrangler
wrangler login
wrangler pages project create clauderedditor-web
```

Luego el script puede hacer deploy directamente.

---

## 📝 Notas importantes

### Sobre topic_tags específicos

El usuario quiere especial atención a:
- `buildable`: **Python o prompts puros**, sin dependencias externas ni hardware. El usuario puede implementarlo inmediatamente sin ayuda.
- `hardware`: Posts que requieren hardware específico (cámaras, impresoras 3D, microcontroladores, IoT). El usuario depende de tener acceso al hardware.
- `meta-tooling`: Herramientas para mejorar el workflow (como ClaudeRedditor mismo)
- `code-snippet` (format_tag): Posts de los que se pueden extraer prompts o código directamente, **cualquier lenguaje**. Si no es Python/prompts, el usuario puede necesitar ayuda de Claude Code.

**Prioridad de implementación:**
1. `[buildable] + [code-snippet]` → Máxima: implementable solo, ahora mismo
2. `[code-snippet]` → Alta: implementable con ayuda de Claude Code
3. `[hardware]` → Depende: solo si tiene el hardware

### Sobre el flujo de uso

El usuario:
1. Oye el podcast generado con NotebookLM
2. Abre la web (local o pública) para ver la lista de historias
3. Usa `bookmark show <fecha>` para ver IDs
4. Marca las interesantes con `bookmark add`
5. Más tarde revisa con `bookmark list --status=to_read`

### Consideraciones técnicas

- **No usar poetry**: El usuario usa `.venv` y `python -m` directamente
- **MariaDB local**: No cloud databases por ahora
- **Web estática**: Sin interactividad client-side en este sprint (solo HTML/CSS)
- **Deploy público**: La web puede ser pública (no tiene datos sensibles)

---

## ✅ Criterios de éxito por sprint

**Sprint 1:** `scan` muestra tags correctamente
**Sprint 2:** `digest --format=json` genera JSON válido con estructura correcta
**Sprint 3:** Puedo hacer bookmarks desde CLI y verlos listados
**Sprint 4:** Web funciona en local mostrando digests con tags
**Sprint 5:** Cron ejecuta todo automáticamente y web se actualiza

---
