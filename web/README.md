# Claude Gazette

AI-curated content digests from Reddit and Hacker News with personality and visual flair.

## Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

## What it does

- Displays AI-curated digest stories in a futuristic dark blue interface
- Shows Claude's personality through 12 expressions matched to content sentiment
- Features autonomous boids flocking animation background
- Provides bookmark management with status tracking
- Responsive design with Windows-style UI elements

## Documentation

- 📖 [Architecture](ARCHITECTURE.md) - Design decisions and technical details
- 🚀 [Quick Start](QUICKSTART.md) - Complete setup tutorial
- 🤖 [Briefing](BRIEFING.md) - Context for Claude AI

## Requirements

- Node.js 18+
- npm or pnpm
- Astro v5.16.11+
- JSON digest files in `../outputs/web/`

## Theme

**Claude Gazette** features a custom dark blue futuristic theme:
- Navy backgrounds (#0a1929, #0d1b2a) with cyan accents (#00d4ff)
- Autonomous swarm animation using boids flocking algorithm
- 12 Claude expressions (confidence-based) reflecting story sentiment
- Windows-style SVG buttons for navigation
- Inter font for clean, modern typography
