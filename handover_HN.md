# 🔶 HANDOVER: HackerNews Integration + Multi-Source Architecture

## Contexto

Añadir HackerNews como fuente de datos alternativa/complementaria a Reddit. HN tiene **API pública sin autenticación** y es muy relevante para posts sobre Claude y AI.

---

## ¿Por qué HackerNews?

✅ **API pública gratuita** (sin auth, sin rate limits estrictos)  
✅ **Muy relevante** para posts sobre AI/Claude  
✅ **Alta calidad** de discusiones técnicas  
✅ **JSON responses** fáciles de parsear  
✅ **Compatible** con arquitectura existente  

---

## HackerNews API Overview

### Endpoints

```
Base: https://hacker-news.firebaseio.com/v0/

GET /topstories.json          → [id1, id2, ...] (hasta 500 IDs)
GET /newstories.json          → [id1, id2, ...] (nuevos posts)
GET /beststories.json         → [id1, id2, ...] (best posts)
GET /item/{id}.json           → Detalles del item
```

### Estructura de Item

```json
{
  "id": 8863,
  "by": "dhouston",
  "descendants": 71,           // Número de comments
  "score": 111,
  "time": 1175714200,          // Unix timestamp
  "title": "My YC app: Dropbox - Throw away your USB drive",
  "type": "story",
  "url": "http://www.getdropbox.com/u/2/screencast.html"
}
```

**Para "Ask HN" posts** (sin URL externa):
```json
{
  "id": 121003,
  "by": "tel",
  "text": "HTML content of the post",  // Selftext equivalent
  "title": "Ask HN: The Arc Effect",
  "type": "story"
}
```

### Rate Limits

- No limits oficiales documentados
- Recomendación: 1-2 requests/segundo (educado)
- Cachear agresivamente (HN posts no cambian)

---

## Arquitectura Multi-Source

### Diagrama

```
┌────────────────────────────────────┐
│      Unified Scraper Interface     │
│                                    │
│  ┌──────────────┐  ┌─────────────┐│
│  │ RedditScraper│  │ HNScraper   ││
│  │  (RSS/PRAW)  │  │ (Public API)││
│  └──────┬───────┘  └──────┬──────┘│
│         │                 │       │
│         └────────┬────────┘       │
│                  ↓                │
│         Normalized Post Format    │
│         {id, title, source, ...}  │
└─────────────────┬──────────────────┘
                  ↓
         ┌────────────────┐
         │ Classifier     │
         │ (Claude API)   │
         └────────┬───────┘
                  ↓
         ┌────────────────┐
         │ MariaDB Cache  │
         └────────────────┘
```

---

## Schema Updates

### 🏗️ **DECISIÓN ARQUITECTÓNICA: Prefixed IDs (más simple)**

En vez de composite keys `(id, source)`, usamos **IDs prefijados**:
- Reddit: `reddit_abc123`
- HackerNews: `hn_8863`

**Ventajas**:
- ✅ No rompe foreign keys existentes
- ✅ Más simple de implementar
- ✅ No requiere cambiar PK en tablas
- ✅ Compatible con código actual

### Modificar Tabla `reddit_posts` → `posts`

```sql
-- 1. Renombrar tabla para ser agnóstica de fuente
RENAME TABLE reddit_posts TO posts;

-- 2. Añadir columna source
ALTER TABLE posts
ADD COLUMN source ENUM('reddit', 'hackernews') NOT NULL DEFAULT 'reddit'
AFTER id;

-- 3. Actualizar IDs existentes con prefijo 'reddit_'
-- NOTA: Esto debe hacerse ANTES si hay datos existentes
-- UPDATE posts SET id = CONCAT('reddit_', id) WHERE source = 'reddit';

-- 4. Añadir índice source
ALTER TABLE posts
ADD INDEX idx_source (source),
ADD INDEX idx_source_created (source, created_utc);

-- 5. Actualizar classifications (añadir source column)
ALTER TABLE classifications
ADD COLUMN source ENUM('reddit', 'hackernews') NOT NULL DEFAULT 'reddit'
AFTER post_id;

-- 6. Si hay datos existentes, actualizar IDs
-- UPDATE classifications SET post_id = CONCAT('reddit_', post_id), source = 'reddit' WHERE source = 'reddit';

-- 7. Actualizar scan_history para multi-source
ALTER TABLE scan_history
MODIFY COLUMN subreddit VARCHAR(100) NULL COMMENT 'Subreddit name or HN (for hackernews source)';

COMMIT;
```

**Migration script**: `db/migrations/002_multi_source.sql`

**IMPORTANTE**: Si hay datos existentes en producción, crear backup antes:
```sql
CREATE TABLE posts_backup AS SELECT * FROM posts;
CREATE TABLE classifications_backup AS SELECT * FROM classifications;
```

---

## 🏗️ **DECISIONES ARQUITECTÓNICAS FINALES**

### 1. **Post Model**: Extender RedditPost → `Post` genérico
- Crear `Post` dataclass agnóstico en `scrapers/base.py`
- Mantener `RedditPost` en `core/models.py` para backward compatibility
- `RedditScraper` convertirá `RedditPost` → `Post`

### 2. **Estructura de Directorios**: Reorganizar scrapers
```
src/claude_redditor/
  scrapers/              ← NUEVO directorio
    __init__.py          ← ScraperManager + factory functions
    base.py              ← Post dataclass + BaseScraper interface
    reddit.py            ← Mover RedditScraper actual aquí
    hackernews.py        ← Nuevo HNScraper
  scraper.py             ← DEPRECAR: mantener create_scraper() por compatibilidad
```

### 3. **CLI Commands**: `scan-hn` dedicado
```bash
# Mantener comandos existentes sin cambios
./reddit-analyzer scan ClaudeAI          # Single subreddit (actual)
./reddit-analyzer scan all               # All subreddits (actual)
./reddit-analyzer compare                # Compare subreddits (actual)

# Nuevos comandos para HackerNews
./reddit-analyzer scan-hn -k claude -k anthropic    # HN con keywords
./reddit-analyzer compare-sources                    # Reddit vs HN (futuro)
```

### 4. **Database IDs**: Prefixed IDs (no composite keys)
- Reddit IDs: `reddit_abc123`
- HN IDs: `hn_8863`
- Columna `source` para queries eficientes

---

## Implementation

### 1. Base Scraper Interface (scrapers/base.py)

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class Post:
    """
    Normalized post format agnóstico de fuente.
    Compatible con Reddit y HackerNews.
    """
    id: str
    source: str              # 'reddit' o 'hackernews'
    title: str
    url: Optional[str]
    author: Optional[str]
    score: int
    num_comments: int
    created_utc: int         # Unix timestamp
    selftext: Optional[str]  # Body del post (si existe)
    source_url: str          # URL canónica del post
    
    # Source-specific metadata (opcional)
    subreddit: Optional[str] = None      # Solo Reddit
    hn_type: Optional[str] = None        # Solo HN: 'story', 'ask', etc.

class BaseScraper(ABC):
    """Interface común para todos los scrapers"""
    
    @abstractmethod
    def fetch_posts(
        self, 
        limit: int = 100,
        sort: str = "hot",
        **kwargs
    ) -> List[Post]:
        """
        Fetch posts de la fuente.
        Returns: Lista de Posts normalizados
        """
        pass
    
    @abstractmethod
    def get_source_name(self) -> str:
        """Returns: 'reddit' o 'hackernews'"""
        pass
```

---

### 2. HackerNews Scraper (scraper/hackernews.py)

```python
import requests
import time
from typing import List, Optional
from .base import BaseScraper, Post
import logging

logger = logging.getLogger(__name__)

class HackerNewsScraper(BaseScraper):
    """
    Scraper para HackerNews usando Firebase API.
    
    Features:
    - Keyword filtering (busca en title y text)
    - Multiple story types (top, new, best)
    - Rate limiting educado (1 req/sec)
    """
    
    BASE_URL = "https://hacker-news.firebaseio.com/v0"
    
    def __init__(self, keywords: Optional[List[str]] = None):
        """
        Args:
            keywords: Lista de keywords para filtrar (case-insensitive)
                     Ej: ['claude', 'anthropic', 'ai', 'artificial intelligence']
        """
        self.keywords = [k.lower() for k in keywords] if keywords else []
        self.session = requests.Session()
        self.last_request_time = 0
    
    def get_source_name(self) -> str:
        return "hackernews"
    
    def _rate_limit(self):
        """Rate limiting: 1 request/segundo"""
        elapsed = time.time() - self.last_request_time
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)
        self.last_request_time = time.time()
    
    def _get(self, endpoint: str) -> Optional[dict]:
        """GET request con rate limiting"""
        self._rate_limit()
        
        try:
            url = f"{self.BASE_URL}/{endpoint}"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"HN API error: {e}")
            return None
    
    def fetch_posts(
        self,
        limit: int = 100,
        sort: str = "top",  # 'top', 'new', 'best'
        **kwargs
    ) -> List[Post]:
        """
        Fetch posts de HackerNews.
        
        Args:
            limit: Número máximo de posts
            sort: 'top', 'new', 'best'
        
        Returns:
            Lista de Posts (filtrados por keywords si están definidos)
        """
        # 1. Get story IDs
        endpoint_map = {
            'top': 'topstories.json',
            'new': 'newstories.json',
            'best': 'beststories.json'
        }
        endpoint = endpoint_map.get(sort, 'topstories.json')
        
        logger.info(f"Fetching {sort} stories from HackerNews...")
        story_ids = self._get(endpoint)
        
        if not story_ids:
            logger.warning("No story IDs returned from HN")
            return []
        
        # 2. Fetch individual stories
        # Fetch más de lo necesario porque algunos pueden ser filtrados
        fetch_limit = min(limit * 3, 500)  # HN devuelve hasta 500 IDs
        posts = []
        
        for story_id in story_ids[:fetch_limit]:
            story_data = self._get(f"item/{story_id}.json")
            
            if not story_data or story_data.get('type') != 'story':
                continue
            
            # Parse story
            post = self._parse_story(story_data)
            
            if not post:
                continue
            
            # 3. Filter by keywords (si están definidos)
            if self.keywords and not self._matches_keywords(post):
                continue
            
            posts.append(post)
            
            # 4. Stop si ya tenemos suficientes
            if len(posts) >= limit:
                break
        
        logger.info(f"Fetched {len(posts)} HN posts (filtered from {fetch_limit})")
        return posts
    
    def _parse_story(self, story_data: dict) -> Optional[Post]:
        """Convierte HN story a Post normalizado"""
        try:
            # Extraer campos
            story_id = str(story_data['id'])
            title = story_data.get('title', '')
            url = story_data.get('url')  # None si es Ask HN
            author = story_data.get('by')
            score = story_data.get('score', 0)
            num_comments = story_data.get('descendants', 0)
            created_utc = story_data.get('time', 0)
            selftext = story_data.get('text', '')  # Solo para Ask HN
            
            # URL canónica de HN
            source_url = f"https://news.ycombinator.com/item?id={story_id}"
            
            # Si no hay URL externa, es Ask HN → usar source_url
            if not url:
                url = source_url
            
            return Post(
                id=story_id,
                source='hackernews',
                title=title,
                url=url,
                author=author,
                score=score,
                num_comments=num_comments,
                created_utc=created_utc,
                selftext=selftext[:5000] if selftext else None,
                source_url=source_url,
                hn_type=story_data.get('type')
            )
            
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing HN story: {e}")
            return None
    
    def _matches_keywords(self, post: Post) -> bool:
        """
        Chequea si post contiene alguna keyword.
        Busca en: title + selftext
        """
        if not self.keywords:
            return True
        
        # Combinar texto a buscar
        search_text = post.title.lower()
        if post.selftext:
            search_text += " " + post.selftext.lower()
        
        # Buscar keywords
        for keyword in self.keywords:
            if keyword in search_text:
                return True
        
        return False
    
    def search_by_keywords(
        self,
        keywords: List[str],
        limit: int = 50,
        sort: str = "top"
    ) -> List[Post]:
        """
        Convenience method para buscar por keywords.
        
        Args:
            keywords: ['claude', 'anthropic', 'ai']
            limit: Max posts
            sort: 'top', 'new', 'best'
        """
        self.keywords = [k.lower() for k in keywords]
        return self.fetch_posts(limit=limit, sort=sort)
```

---

### 3. Unified Scraper Manager (scraper/__init__.py)

```python
from typing import List, Optional
from .base import Post
from .hackernews import HackerNewsScraper
from .reddit import RedditScraper  # Tu scraper actual de Reddit

class ScraperManager:
    """
    Manager para coordinar múltiples scrapers.
    """
    
    def __init__(self, config):
        self.config = config
        self.scrapers = {}
        
        # Initialize available scrapers
        self.scrapers['hackernews'] = HackerNewsScraper()
        
        # Reddit solo si tenemos credenciales
        if config.reddit_client_id:
            self.scrapers['reddit'] = RedditScraper()
    
    def fetch_from_source(
        self,
        source: str,
        limit: int = 100,
        **kwargs
    ) -> List[Post]:
        """
        Fetch posts de una fuente específica.
        
        Args:
            source: 'reddit' o 'hackernews'
            limit: Max posts
            **kwargs: Parámetros específicos de cada scraper
        """
        scraper = self.scrapers.get(source)
        if not scraper:
            raise ValueError(f"Unknown source: {source}")
        
        return scraper.fetch_posts(limit=limit, **kwargs)
    
    def fetch_all(self, limit_per_source: int = 50) -> List[Post]:
        """Fetch posts de todas las fuentes disponibles"""
        all_posts = []
        
        for source_name, scraper in self.scrapers.items():
            posts = scraper.fetch_posts(limit=limit_per_source)
            all_posts.extend(posts)
        
        return all_posts
    
    def search_hackernews(
        self,
        keywords: List[str],
        limit: int = 50,
        sort: str = "top"
    ) -> List[Post]:
        """
        Busca en HackerNews por keywords.
        
        Args:
            keywords: ['claude', 'anthropic', 'ai', 'llm']
        """
        hn_scraper = self.scrapers.get('hackernews')
        if not hn_scraper:
            return []
        
        return hn_scraper.search_by_keywords(keywords, limit, sort)
```

---

### 4. Repository Updates (db/repository.py)

```python
# Actualizar métodos para soportar campo 'source'

def get_cached_classifications(
    self, 
    post_ids: List[str],
    source: str = 'reddit'  # NEW parameter
) -> List[Dict]:
    """Get cached classifications by source"""
    if not post_ids:
        return []
    
    with self.db.get_session() as session:
        results = session.execute(
            select(Classification, Post)
            .join(Post, and_(
                Classification.post_id == Post.id,
                Classification.source == Post.source
            ))
            .where(
                Classification.post_id.in_(post_ids),
                Classification.source == source
            )
        ).all()
        
        # ... rest same

def save_posts(self, posts: List[Post]) -> None:
    """Save posts (multi-source aware)"""
    with self.db.get_session() as session:
        for post in posts:
            # Check if exists
            exists = session.execute(
                select(DBPost).where(
                    DBPost.id == post.id,
                    DBPost.source == post.source
                )
            ).first()
            
            if not exists:
                db_post = DBPost(
                    id=post.id,
                    source=post.source,
                    title=post.title,
                    author=post.author,
                    score=post.score,
                    num_comments=post.num_comments,
                    created_utc=post.created_utc,
                    url=post.url,
                    selftext=post.selftext,
                    subreddit=post.subreddit  # None para HN
                )
                session.add(db_post)
```

---

### 5. CLI Commands (cli.py)

```python
@app.command()
def scan_hn(
    keywords: List[str] = typer.Option(
        ['claude', 'anthropic'],
        "--keyword", "-k",
        help="Keywords to filter (can specify multiple)"
    ),
    limit: int = 50,
    sort: str = typer.Option("top", help="Sort: top, new, best")
):
    """
    Scan HackerNews for posts about Claude/AI.
    
    Example:
        reddit-analyzer scan-hn -k claude -k anthropic -k ai --limit 30
    """
    from .scraper import ScraperManager
    from .classifier import PostClassifier
    from .analyzer import AnalysisEngine
    from .reporter import Reporter
    
    console.print(f"[cyan]🔶 Scanning HackerNews (keywords: {', '.join(keywords)})[/cyan]\n")
    
    # Initialize
    manager = ScraperManager(settings)
    classifier = PostClassifier()
    analyzer = AnalysisEngine()
    reporter = Reporter()
    
    # 1. Fetch from HN
    console.print("Fetching posts from HackerNews...")
    posts = manager.search_hackernews(keywords, limit, sort)
    
    if not posts:
        console.print("[yellow]No posts found matching keywords[/yellow]")
        return
    
    console.print(f"[green]✓ Found {len(posts)} posts[/green]\n")
    
    # 2. Analyze with cache
    classifications, cache_stats = analyzer.analyze_with_cache(
        posts, 
        classifier,
        source='hackernews'
    )
    
    # 3. Display cache stats
    table = Table(title="💾 Cache Stats", show_header=False)
    table.add_row("Total posts", str(cache_stats['total']))
    table.add_row("Cached", f"{cache_stats['cached']} ({cache_stats['cache_hit_rate']:.1%})")
    table.add_row("New classified", str(cache_stats['new']))
    console.print(table)
    console.print()
    
    # 4. Generate report
    report = analyzer.generate_report(classifications, posts)
    
    # 5. Save history
    analyzer.save_scan_result('hackernews', cache_stats, report.signal_ratio)
    
    # 6. Display
    reporter.render_terminal(report)


@app.command()
def scan_all(
    limit_per_source: int = 30,
    hn_keywords: List[str] = typer.Option(
        ['claude', 'anthropic', 'ai'],
        "--hn-keyword",
        help="Keywords for HackerNews filtering"
    )
):
    """
    Scan both Reddit and HackerNews.
    """
    console.print("[cyan]📊 Scanning Multiple Sources[/cyan]\n")
    
    # ... similar pero fetch de ambas fuentes
```

---

### 6. Config Updates (config.py)

```python
class Settings(BaseSettings):
    # ... existing ...
    
    # HackerNews
    hn_default_keywords: List[str] = [
        'claude', 'anthropic', 'ai', 'artificial intelligence',
        'llm', 'large language model', 'chatgpt alternative'
    ]
    hn_fetch_limit: int = 100  # Fetch más para compensar filtrado
```

---

## Migration Script (002_multi_source.sql)

```sql
USE reddit_analyzer;

-- Backup de datos existentes (opcional)
CREATE TABLE reddit_posts_backup AS SELECT * FROM reddit_posts;
CREATE TABLE classifications_backup AS SELECT * FROM classifications;

-- 1. Renombrar tabla
RENAME TABLE reddit_posts TO posts;

-- 2. Añadir columna source
ALTER TABLE posts 
ADD COLUMN source ENUM('reddit', 'hackernews') NOT NULL DEFAULT 'reddit'
AFTER id;

-- 3. Actualizar primary key (composite)
ALTER TABLE posts
DROP PRIMARY KEY,
ADD PRIMARY KEY (id, source);

-- 4. Añadir índice source
ALTER TABLE posts 
ADD INDEX idx_source (source),
ADD INDEX idx_source_subreddit (source, subreddit);

-- 5. Actualizar classifications
ALTER TABLE classifications
ADD COLUMN source ENUM('reddit', 'hackernews') NOT NULL DEFAULT 'reddit'
AFTER post_id;

-- 6. Drop foreign key antigua
ALTER TABLE classifications
DROP FOREIGN KEY classifications_ibfk_1;

-- 7. Actualizar unique key
ALTER TABLE classifications
DROP INDEX unique_post;

ALTER TABLE classifications
ADD UNIQUE KEY unique_post_source (post_id, source);

-- 8. Nueva foreign key
ALTER TABLE classifications
ADD CONSTRAINT fk_post 
FOREIGN KEY (post_id, source) 
REFERENCES posts(id, source) 
ON DELETE CASCADE;

-- 9. Actualizar scan_history para multi-source
ALTER TABLE scan_history
MODIFY COLUMN subreddit VARCHAR(100) NULL COMMENT 'Subreddit or source identifier';

COMMIT;
```

---

## Usage Examples

### Scan HackerNews por keywords

```bash
# Buscar posts sobre Claude/Anthropic
reddit-analyzer scan-hn -k claude -k anthropic --limit 50

# Buscar posts sobre AI en general
reddit-analyzer scan-hn -k "artificial intelligence" -k "machine learning" -k llm

# Ver nuevos posts (en lugar de top)
reddit-analyzer scan-hn -k claude --sort new
```

### Scan ambas fuentes

```bash
# Escanear Reddit + HN
reddit-analyzer scan-all --limit-per-source 30

# Ver historial combinado
reddit-analyzer history
```

---

## Expected Output

```bash
$ reddit-analyzer scan-hn -k claude -k anthropic --limit 30

🔶 Scanning HackerNews (keywords: claude, anthropic)

Fetching posts from HackerNews...
✓ Found 23 posts

💾 Cache Stats
─────────────────────────────
Total posts       23
Cached            8 (34.8%)
New classified    15
API cost saved    ~$0.008

📈 Analysis Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Category Distribution:
  ✓ Technical       12 (52%)
  ✓ Research        5 (22%)
  ✗ Mystical        2 (9%)
  • Community       4 (17%)

✅ Signal Ratio: 74% (17/23 posts)

🏆 Top Signal Posts:
  1. [234↑] Claude 3.5 Sonnet beats GPT-4 on SWE-bench
     https://news.ycombinator.com/item?id=...
  2. [189↑] Anthropic's Constitutional AI paper analysis
     ...
```

---

## Benefits vs Reddit

| Feature | Reddit | HackerNews |
|---------|--------|------------|
| **Auth** | ❌ Requiere app | ✅ Public API |
| **Rate Limits** | ❌ 403 sin auth | ✅ Generoso |
| **Content Quality** | ⚠️ Variable | ✅ Alta (tech-focused) |
| **Relevancia AI** | ✅ Buena (r/ClaudeAI) | ✅ Excelente |
| **Filtrado** | ⚠️ Solo subreddit | ✅ Keywords custom |
| **Metadata** | ✅ Completa | ⚠️ Limitada |

---

## Implementation Checklist

**Phase 1: HN Scraper (1h)**
- [ ] `scraper/base.py` (Post dataclass + interface)
- [ ] `scraper/hackernews.py` (HN scraper con keyword filter)
- [ ] Test básico: fetch 10 posts con keyword "claude"

**Phase 2: Multi-Source (1h)**
- [ ] Migration script 002
- [ ] Update models.py (añadir source column)
- [ ] Update repository.py (source-aware queries)

**Phase 3: CLI (30min)**
- [ ] `scan-hn` command
- [ ] `scan-all` command
- [ ] Update `history` para mostrar source

**Phase 4: Testing (30min)**
- [ ] Test HN fetch
- [ ] Test cache con HN posts
- [ ] Test clasificación de HN content

**Total: ~3 horas**

---

## Keywords Recomendadas para HN

```python
CLAUDE_KEYWORDS = [
    'claude',
    'anthropic',
    'claude 3',
    'claude sonnet',
    'constitutional ai'
]

AI_GENERAL_KEYWORDS = [
    'artificial intelligence',
    'machine learning',
    'large language model',
    'llm',
    'gpt',
    'chatbot',
    'natural language processing',
    'nlp'
]

COMPETITORS = [
    'openai',
    'chatgpt',
    'gemini',
    'mistral'
]
```

---

## Future Enhancements

**Post-MVP**:
- Algolia HN Search API (búsqueda más sofisticada)
- Comments scraping (analizar discusiones)
- Trending detection (posts que suben rápido)
- Cross-source comparison (Reddit vs HN discourse)

---

## ✅ Ready para Claude Code

**Start with**:
1. `scrapers/base.py` (interfaces + Post dataclass)
2. `scrapers/hackernews.py` (HN scraper)
3. Migration `002_multi_source.sql`
4. Update `repository.py` para source awareness
5. CLI commands (`scan-hn`)

🚀 **Let's add HackerNews!**

---

## 📋 IMPLEMENTATION CHECKLIST

Checklist detallada para implementación incremental. Marca con `[x]` cuando completes cada tarea.

### Phase 1: Base Architecture & Refactoring (1-2h)

**Objetivo**: Crear estructura `scrapers/` y mover código existente sin romper nada.

- [ ] **1.1** Crear directorio `src/claude_redditor/scrapers/`
- [ ] **1.2** Crear `scrapers/__init__.py` vacío
- [ ] **1.3** Crear `scrapers/base.py`:
  - [ ] Definir `Post` dataclass con todos los campos (id, source, title, url, author, score, num_comments, created_utc, selftext, source_url, subreddit, hn_type)
  - [ ] Definir `BaseScraper` abstract class con métodos `fetch_posts()` y `get_source_name()`
  - [ ] Agregar helper `def prefix_id(raw_id: str, source: str) -> str` para generar IDs prefijados
- [ ] **1.4** Copiar `scraper.py` → `scrapers/reddit.py`:
  - [ ] Modificar imports para usar `from .base import Post, BaseScraper`
  - [ ] Hacer que `RedditScraper` herede de `BaseScraper`
  - [ ] Agregar método `get_source_name()` que retorne `'reddit'`
  - [ ] Modificar `fetch_posts()` para retornar `List[Post]` en vez de `List[RedditPost]`
  - [ ] En `_parse_*` methods, convertir `RedditPost` → `Post` y agregar prefijo `reddit_` al ID
- [ ] **1.5** Actualizar `scrapers/__init__.py`:
  - [ ] Importar `Post`, `BaseScraper` desde `.base`
  - [ ] Importar `RedditScraper` desde `.reddit`
  - [ ] Crear función `create_reddit_scraper() -> RedditScraper` (factory)
- [ ] **1.6** Mantener `scraper.py` (backward compatibility):
  - [ ] Importar desde `scrapers`: `from .scrapers import create_reddit_scraper`
  - [ ] Modificar `create_scraper()` para usar `create_reddit_scraper()`
  - [ ] Agregar deprecation comment
- [ ] **1.7** Verificar que nada se rompió:
  - [ ] Ejecutar `./reddit-analyzer config` (debe funcionar)
  - [ ] Ejecutar un scan pequeño: `./reddit-analyzer scan ClaudeAI --limit 5`
  - [ ] Verificar que se generan posts con IDs prefijados `reddit_*`

**Checkpoint 1**: Reddit scraper funciona con nueva estructura ✅

---

### Phase 2: HackerNews Scraper (1h)

**Objetivo**: Implementar HNScraper funcional con keyword filtering.

- [ ] **2.1** Crear `scrapers/hackernews.py`:
  - [ ] Copiar código del handover (líneas 196-386)
  - [ ] Ajustar imports: `from .base import BaseScraper, Post`
  - [ ] Implementar `HackerNewsScraper` class
  - [ ] Implementar `_rate_limit()`, `_get()`, `fetch_posts()`, `_parse_story()`, `_matches_keywords()`, `search_by_keywords()`
  - [ ] **IMPORTANTE**: En `_parse_story()`, usar `prefix_id(story_id, 'hackernews')` para generar ID prefijado
- [ ] **2.2** Actualizar `scrapers/__init__.py`:
  - [ ] Importar `HackerNewsScraper` desde `.hackernews`
  - [ ] Crear función `create_hn_scraper(keywords: Optional[List[str]] = None) -> HackerNewsScraper`
  - [ ] Crear `ScraperManager` class (copiar del handover líneas 398-461)
- [ ] **2.3** Test manual del scraper:
  - [ ] Crear script temporal `test_hn_scraper.py`:
    ```python
    from claude_redditor.scrapers import create_hn_scraper

    scraper = create_hn_scraper(keywords=['claude', 'anthropic'])
    posts = scraper.fetch_posts(limit=5, sort='top')

    print(f"Fetched {len(posts)} posts:")
    for post in posts:
        print(f"  [{post.id}] {post.title}")
        print(f"    Score: {post.score}, Comments: {post.num_comments}")
    ```
  - [ ] Ejecutar: `source .venv/bin/activate && python test_hn_scraper.py`
  - [ ] Verificar que se obtienen ~5 posts de HN con IDs prefijados `hn_*`
  - [ ] Verificar que keyword filtering funciona

**Checkpoint 2**: HNScraper fetch posts correctamente ✅

---

### Phase 3: Database Migration (30min)

**Objetivo**: Actualizar schema para soportar multi-source con IDs prefijados.

- [ ] **3.1** Crear migration script `src/claude_redditor/db/migrations/002_multi_source.sql`:
  - [ ] Copiar SQL del handover (líneas 113-144) con IDs prefijados (sin composite keys)
  - [ ] Agregar comentarios explicativos
  - [ ] Incluir comandos de backup al inicio
- [ ] **3.2** Actualizar `db/models.py`:
  - [ ] En `Post` table model: agregar columna `source` tipo `Enum('reddit', 'hackernews')`
  - [ ] Agregar índice `idx_source` y `idx_source_created`
  - [ ] En `Classification` table model: agregar columna `source` tipo `Enum`
  - [ ] Modificar `scan_history` table comment para mencionar multi-source
- [ ] **3.3** Actualizar `db/repository.py`:
  - [ ] En `get_cached_classifications()`: agregar parámetro `source: str = 'reddit'`
  - [ ] Modificar query para filtrar por `source`
  - [ ] En `save_posts()`: asegurar que se guarda campo `source` correctamente
  - [ ] En `save_classifications()`: asegurar que se guarda campo `source`
  - [ ] En `save_scan_history()`: permitir que `subreddit` sea `'HackerNews'` para HN posts
  - [ ] En `get_scan_history()`: actualizar queries para manejar source
- [ ] **3.4** Ejecutar migration (SOLO SI TIENES DB CONFIGURADA):
  - [ ] Backup: `mysqldump reddit_analyzer > backup_before_hn.sql`
  - [ ] Ejecutar: `mysql reddit_analyzer < src/claude_redditor/db/migrations/002_multi_source.sql`
  - [ ] Verificar: `mysql reddit_analyzer -e "DESCRIBE posts;"`
  - [ ] Verificar que columna `source` existe
- [ ] **3.5** Actualizar `analyzer.py`:
  - [ ] En `CachedAnalysisEngine.analyze_with_cache()`: agregar parámetro `source: str = 'reddit'`
  - [ ] Pasar `source` a `repo.get_cached_classifications()`
  - [ ] Pasar `source` a `repo.save_posts()` y `repo.save_classifications()`

**Checkpoint 3**: Database soporta multi-source ✅

---

### Phase 4: CLI Integration (30min)

**Objetivo**: Agregar comando `scan-hn` funcional.

- [ ] **4.1** Actualizar `cli.py` - agregar comando `scan-hn`:
  - [ ] Copiar estructura del handover (líneas 527-589)
  - [ ] Importar: `from .scrapers import ScraperManager, create_hn_scraper`
  - [ ] Implementar función `scan_hn()` con parámetros:
    - `keywords: List[str]` con opción `-k/--keyword`
    - `limit: int` (default 50)
    - `sort: str` (default 'top')
    - `export_json: bool` (default False)
    - `no_cache: bool` (default False)
  - [ ] Flow completo:
    1. Create HNScraper con keywords
    2. Fetch posts
    3. Classify con cache (pasar `source='hackernews'`)
    4. Mostrar cache stats
    5. Generar report
    6. Save scan history (subreddit='HackerNews')
    7. Display con reporter
- [ ] **4.2** Actualizar comando `history`:
  - [ ] Modificar display para mostrar columna `source` si es HN
  - [ ] Formato: `"HackerNews"` en vez de subreddit name cuando sea HN
- [ ] **4.3** Test del nuevo comando:
  - [ ] Ejecutar: `./reddit-analyzer scan-hn -k claude -k anthropic --limit 5`
  - [ ] Verificar que:
    - Fetch posts de HN
    - Classify correctamente
    - Muestra cache stats
    - Genera report legible
    - Guarda en history

**Checkpoint 4**: CLI `scan-hn` funciona end-to-end ✅

---

### Phase 5: Config & Documentation (20min)

**Objetivo**: Agregar configuración y documentar nuevas features.

- [ ] **5.1** Actualizar `config.py`:
  - [ ] Agregar setting `hn_default_keywords: List[str]` con default:
    ```python
    ['claude', 'anthropic', 'ai', 'artificial intelligence', 'llm']
    ```
  - [ ] Agregar setting `hn_fetch_limit: int = 100`
- [ ] **5.2** Actualizar `.env.example`:
  - [ ] Agregar sección para HackerNews:
    ```bash
    # HackerNews (OPTIONAL - keywords for filtering)
    HN_DEFAULT_KEYWORDS=claude,anthropic,ai,llm
    HN_FETCH_LIMIT=100
    ```
- [ ] **5.3** Actualizar `README.md`:
  - [ ] Agregar sección "HackerNews Integration" después de "Reddit Scraping"
  - [ ] Documentar comando `scan-hn` con ejemplos
  - [ ] Actualizar architecture diagram para incluir HN
  - [ ] Agregar a "Features" list: "HackerNews support with keyword filtering"
- [ ] **5.4** Actualizar `Makefile`:
  - [ ] Agregar comando `scan-hn`:
    ```makefile
    scan-hn:
        @echo "Scanning HackerNews..."
        source .venv/bin/activate && ./reddit-analyzer scan-hn -k claude -k anthropic --limit 10
    ```

**Checkpoint 5**: Documentación actualizada ✅

---

### Phase 6: Testing & Validation (30min)

**Objetivo**: Probar todos los casos de uso y edge cases.

- [ ] **6.1** Test HN Scraper aislado:
  - [ ] Test con keywords que no matchean nada → debe retornar lista vacía
  - [ ] Test con limit muy alto → debe respetar límite de API (500)
  - [ ] Test con sort='new' → debe funcionar
  - [ ] Test con sort='best' → debe funcionar
- [ ] **6.2** Test End-to-End:
  - [ ] `./reddit-analyzer scan-hn -k claude --limit 10` → debe completar
  - [ ] `./reddit-analyzer scan-hn -k nonexistentkeyword123 --limit 10` → debe decir "No posts found"
  - [ ] Segunda ejecución del mismo comando → debe mostrar cache hit alto
  - [ ] `./reddit-analyzer history` → debe mostrar scan de HN
- [ ] **6.3** Test Cache multi-source:
  - [ ] Scan Reddit: `./reddit-analyzer scan ClaudeAI --limit 5`
  - [ ] Scan HN: `./reddit-analyzer scan-hn -k claude --limit 5`
  - [ ] Verificar en DB que existen posts con ambos prefijos: `reddit_*` y `hn_*`
  - [ ] Query manual:
    ```sql
    SELECT id, source, title FROM posts WHERE source = 'hackernews' LIMIT 5;
    ```
- [ ] **6.4** Test Classifier con HN posts:
  - [ ] Verificar que Claude clasifica HN posts correctamente
  - [ ] Verificar que red flags se detectan en HN posts
  - [ ] Comparar signal ratio Reddit vs HN (HN debería tener ratio más alto generalmente)
- [ ] **6.5** Test Error Handling:
  - [ ] HN API down (simular con URL incorrecta) → debe manejar gracefully
  - [ ] No keywords provided → debe usar default keywords del config
  - [ ] Limit negativo o 0 → debe validar

**Checkpoint 6**: Todos los tests pasan ✅

---

### Phase 7: Polish & Cleanup (15min)

**Objetivo**: Limpieza final y preparación para production.

- [ ] **7.1** Cleanup:
  - [ ] Eliminar script temporal `test_hn_scraper.py`
  - [ ] Verificar que no hay prints de debug
  - [ ] Verificar que todos los imports son correctos
  - [ ] Verificar que no hay código comentado innecesario
- [ ] **7.2** Logging:
  - [ ] Agregar logs informativos en `HackerNewsScraper`:
    - "Fetching HN posts with keywords: {keywords}"
    - "Found {count} matching posts"
  - [ ] Agregar logs en `scan-hn` command
- [ ] **7.3** Type hints:
  - [ ] Verificar que todas las funciones nuevas tienen type hints
  - [ ] Verificar que `Post` dataclass tiene tipos correctos
- [ ] **7.4** Docstrings:
  - [ ] Verificar que `HackerNewsScraper` tiene docstring completo
  - [ ] Verificar que `scan-hn` command tiene docstring con ejemplos
  - [ ] Verificar que métodos principales tienen docstrings
- [ ] **7.5** Git Commit:
  - [ ] Revisar cambios: `git status`, `git diff`
  - [ ] Commit con mensaje descriptivo:
    ```bash
    git add .
    git commit -m "Add HackerNews integration with keyword filtering

    - Implement HackerNewsScraper with Firebase API
    - Add scrapers/ directory structure with base classes
    - Refactor RedditScraper to use Post generic model
    - Add scan-hn CLI command with keyword filtering
    - Update database schema for multi-source support (prefixed IDs)
    - Add cache support for HackerNews posts
    - Update documentation and README

    Closes #[issue-number] (if applicable)"
    ```

**Checkpoint 7**: Feature completa y lista para merge ✅

---

## 🎯 Progress Tracker

**Tiempo estimado total**: ~3-4 horas

| Phase | Status | Time Est | Notes |
|-------|--------|----------|-------|
| Phase 1: Base Architecture | ⬜ Not Started | 1-2h | Refactoring crítico |
| Phase 2: HN Scraper | ⬜ Not Started | 1h | Core functionality |
| Phase 3: DB Migration | ⬜ Not Started | 30min | Requiere DB configurada |
| Phase 4: CLI Integration | ⬜ Not Started | 30min | User-facing |
| Phase 5: Config & Docs | ⬜ Not Started | 20min | Documentation |
| Phase 6: Testing | ⬜ Not Started | 30min | Validation |
| Phase 7: Polish | ⬜ Not Started | 15min | Final touches |

**Legend**:
- ⬜ Not Started
- 🔄 In Progress
- ✅ Complete
- ⚠️ Blocked (note issue)

---

## 💡 Tips para Implementación

1. **Trabajar incrementalmente**: Completa cada phase antes de avanzar
2. **Test frecuentemente**: Después de cada checkpoint, verifica que nada se rompió
3. **Backup antes de DB migration**: Siempre hacer backup de la DB
4. **Usar feature branch**: `git checkout -b feature/hackernews-integration`
5. **Si encuentras blocker**: Marca con ⚠️ y documenta el issue en el checklist
6. **Commit frecuente**: Commit después de cada phase mayor

---

## 🚨 Si algo falla

**Rollback DB Migration**:
```bash
mysql reddit_analyzer < backup_before_hn.sql
```

**Rollback Code**:
```bash
git reset --hard HEAD~1
```

**Debug HN Scraper**:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
# Ejecutar scraper y ver logs detallados
```