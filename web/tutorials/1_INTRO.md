# 1. Introduction to Astro

## What is Astro?

Astro is a **web framework** for building fast, content-focused websites. Think of it as a tool that helps you create websites without needing to write complex JavaScript.

### Key Concepts for a Python Developer

If you're coming from Python, here are some helpful comparisons:

| Python World | Astro World | Purpose |
|--------------|-------------|---------|
| Flask/Django templates | `.astro` files | Create HTML pages |
| Jinja2 `{{ variable }}` | `{variable}` | Insert dynamic values |
| Python functions | Components | Reusable UI pieces |
| `pip install` | `npm install` | Install dependencies |
| `python app.py` | `npm run dev` | Run the development server |

## Why Astro for This Project?

Your Claude Redditor project generates **JSON files** with digest data. Astro is perfect because:

1. **Static Site Generation (SSG)**: Astro reads your JSON files at build time and creates fast HTML pages
2. **No JavaScript by default**: Your users get plain HTML - super fast
3. **Easy templating**: Write HTML with dynamic parts (similar to Python templates)
4. **Built-in routing**: Files in `src/pages/` automatically become URLs

## How Your Current Web Works

```
JSON Files (Python outputs)  →  Astro reads them  →  Static HTML  →  User's browser
../outputs/web/*.json            at build time         /dist/           sees fast page
```

### The Flow

1. **You run** (Python): `./reddit-analyzer digest --format both`
   - Creates: `outputs/web/claudeia_2026-01-27-01.json`

2. **You build** (Astro): `cd web && npm run build`
   - Astro reads all JSON files
   - Creates HTML pages in `web/dist/`

3. **User visits**: `http://yoursite.com/digest/claudeia_2026-01-27-01`
   - Gets pre-built HTML (instant load!)

## Your Current Web Structure

```
web/
├── src/
│   ├── pages/              ← URLs (index.astro → /, digest/[id].astro → /digest/*)
│   ├── components/         ← Reusable UI pieces (like Python functions)
│   ├── layouts/            ← Page templates (like base.html in Django)
│   └── styles/             ← CSS for styling
├── package.json            ← Dependencies (like requirements.txt)
└── astro.config.mjs        ← Configuration (like settings.py)
```

## File Extensions You'll See

- `.astro` - Astro components (HTML + JavaScript + CSS in one file)
- `.ts` - TypeScript (typed JavaScript, like Python with type hints)
- `.mjs` - JavaScript module
- `.css` - Styling

## Next Steps

In the next tutorial, we'll explore your project structure in detail and understand what each file does.

---

**Commands to remember:**
```bash
cd web
npm run dev      # Start development server (like Flask debug mode)
npm run build    # Build for production (creates dist/ folder)
npm run preview  # Preview the production build locally
```
