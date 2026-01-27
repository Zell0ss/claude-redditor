# 2. Project Structure Deep Dive

## Your Web Directory Layout

Let's explore every important file in your `web/` directory:

```
web/
├── src/                          ← Your source code
│   ├── components/               ← Reusable UI components
│   │   ├── StoryCard.astro       ← Displays a single story
│   │   ├── TagBadge.astro        ← Colored tag badges
│   │   └── BookmarkCard.astro    ← Bookmark display
│   │
│   ├── layouts/                  ← Page wrappers (templates)
│   │   └── Layout.astro          ← Main layout (nav, footer, etc.)
│   │
│   ├── pages/                    ← Routes (files = URLs!)
│   │   ├── index.astro           ← Homepage (/)
│   │   ├── bookmarks.astro       ← /bookmarks
│   │   ├── digest/
│   │   │   └── [id].astro        ← /digest/anything
│   │   └── story/
│   │       └── [id].astro        ← /story/anything
│   │
│   ├── styles/
│   │   └── global.css            ← Site-wide styles
│   │
│   └── types/
│       └── digest.ts             ← TypeScript types (data shapes)
│
├── package.json                  ← Dependencies & scripts
├── astro.config.mjs              ← Astro configuration
└── tsconfig.json                 ← TypeScript configuration
```

## Understanding Each Part

### 📄 `src/pages/` - The Router

**Python analogy**: Like Flask routes or Django urls.py

Files in `pages/` automatically become URLs:

| File | URL | Purpose |
|------|-----|---------|
| `index.astro` | `/` | List all digests |
| `bookmarks.astro` | `/bookmarks` | Show bookmarks |
| `digest/[id].astro` | `/digest/claudeia_2026-01-27-01` | Single digest view |
| `story/[id].astro` | `/story/2026-01-27-01-003` | Single story detail |

**The `[id]` syntax** means "dynamic route" - like `@app.route('/digest/<id>')` in Flask.

### 🧩 `src/components/` - Reusable Pieces

**Python analogy**: Like functions you import and reuse

Components are reusable UI chunks. Instead of copying HTML, you create a component:

```astro
<!-- Before: Repeating code everywhere -->
<div class="tag">Python</div>
<div class="tag">AI</div>

<!-- After: Reusable component -->
<TagBadge tag="Python" />
<TagBadge tag="AI" />
```

### 🎨 `src/layouts/` - Page Templates

**Python analogy**: Like `base.html` in Jinja2/Django templates

Your `Layout.astro` wraps every page with:
- Navigation bar
- Footer
- Common `<head>` tags (title, meta, etc.)

Every page uses it like:
```astro
---
import Layout from '../layouts/Layout.astro';
---

<Layout title="My Page">
  <p>This content goes inside the layout</p>
</Layout>
```

### 🎨 `src/styles/` - Styling

Your project uses **Tailwind CSS** (covered in tutorial 6).

`global.css` defines custom color variables for your tags.

### 📦 `src/types/` - Data Shapes

**Python analogy**: Like Pydantic models or dataclasses

TypeScript types describe your data structure:

```typescript
// Python equivalent:
class Story:
    id: str
    title: str
    source: str
    # ...

// TypeScript:
interface Story {
  id: string;
  title: string;
  source: string;
  // ...
}
```

## Configuration Files

### `package.json` - Dependencies

**Python equivalent**: `requirements.txt` or `pyproject.toml`

```json
{
  "scripts": {
    "dev": "astro dev",      // npm run dev
    "build": "astro build"   // npm run build
  },
  "dependencies": {
    "astro": "^5.16.11",     // like "flask==2.0.0"
    "tailwindcss": "^4.1.18"
  }
}
```

### `astro.config.mjs` - Astro Settings

**Python equivalent**: `settings.py` in Django

```javascript
export default defineConfig({
  vite: {
    plugins: [tailwindcss()]  // Enable Tailwind CSS
  }
});
```

## Data Flow

Here's how your Python output becomes a website:

```
1. Python creates JSON
   ../outputs/web/claudeia_2026-01-27-01.json
          ↓
2. Astro page reads it (at build time)
   src/pages/digest/[id].astro
   - Uses Node.js fs.readFileSync()
   - Parses JSON
          ↓
3. Astro renders components
   <StoryCard story={...} />
          ↓
4. Outputs static HTML
   dist/digest/claudeia_2026-01-27-01/index.html
          ↓
5. User visits URL
   Browser loads instant HTML (no JavaScript needed!)
```

## Key Takeaways

1. **Pages = Routes**: Files in `src/pages/` become URLs automatically
2. **Components = Functions**: Reusable UI pieces in `src/components/`
3. **Layouts = Base Templates**: Common wrapper in `src/layouts/`
4. **Static Build**: Astro pre-renders everything at build time

## Next Steps

In tutorial 3, we'll dive into `.astro` file syntax and understand how to write Astro components.

---

**Try this:**
```bash
cd web
npm run dev
# Visit http://localhost:4321
# Edit src/pages/index.astro (change the title)
# See the page update instantly!
```
