# 7. Practical Guide to Customizing Your Site

This tutorial provides step-by-step instructions for common customizations you might want to make.

## Setup: Development Workflow

Before making changes, start the dev server:

```bash
cd web
npm run dev
```

Visit `http://localhost:4321` - changes you make will appear instantly!

## Customization Recipes

### 1. Change Site Title and Logo

**File**: `src/layouts/Layout.astro`

**Current:**
```astro
<a href="/" class="flex items-center gap-2 text-xl font-bold text-gray-900">
  <span>📰</span>
  <span>Digest Viewer</span>
</a>
```

**Change to:**
```astro
<a href="/" class="flex items-center gap-2 text-xl font-bold text-gray-900">
  <span>🤖</span>
  <span>My AI Digest</span>
</a>
```

**Also change page title** around line 19:
```astro
<title>{title}</title>
```

### 2. Change Color Scheme to Dark Mode

**File**: `src/layouts/Layout.astro`

**Body background** (line 21):
```astro
<!-- From: -->
<body class="bg-gray-50 min-h-screen">

<!-- To: -->
<body class="bg-gray-900 min-h-screen">
```

**Navigation** (line 22):
```astro
<!-- From: -->
<nav class="bg-white border-b border-gray-200 sticky top-0 z-50">

<!-- To: -->
<nav class="bg-gray-800 border-b border-gray-700 sticky top-0 z-50">
```

**Navigation links**:
```astro
<!-- From: -->
<a href="/" class="flex items-center gap-2 text-xl font-bold text-gray-900 hover:text-blue-600">

<!-- To: -->
<a href="/" class="flex items-center gap-2 text-xl font-bold text-white hover:text-blue-400">
```

**File**: `src/pages/index.astro`

**Page title** (line 46):
```astro
<!-- From: -->
<h1 class="text-3xl font-bold text-gray-900 mb-2">Content Digests</h1>
<p class="text-gray-600">AI-curated content from Reddit and Hacker News</p>

<!-- To: -->
<h1 class="text-3xl font-bold text-white mb-2">Content Digests</h1>
<p class="text-gray-300">AI-curated content from Reddit and Hacker News</p>
```

**Digest cards** (line 61):
```astro
<!-- From: -->
<a class="block bg-white rounded-lg border border-gray-200 p-6 hover:shadow-md hover:border-blue-300">

<!-- To: -->
<a class="block bg-gray-800 rounded-lg border border-gray-700 p-6 hover:shadow-md hover:border-blue-600">
```

**Continue this pattern** for all text elements (change `text-gray-900` to `text-white`, `bg-white` to `bg-gray-800`, etc.)

### 3. Add Project Filter/Selector

**File**: `src/pages/index.astro`

Add after the page header (around line 48):

```astro
<div class="mb-8">
  <h1 class="text-3xl font-bold text-gray-900 mb-2">Content Digests</h1>
  <p class="text-gray-600">AI-curated content from Reddit and Hacker News</p>

  <!-- NEW: Project filter -->
  <div class="mt-4 flex flex-wrap gap-2">
    {Array.from(new Set(digests.map(d => d.project))).map(project => (
      <button
        class="px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800 hover:bg-blue-200"
        onclick={`filterByProject('${project}')`}
      >
        {project}
      </button>
    ))}
  </div>
</div>
```

Add JavaScript at the end of the file:

```astro
<script>
  function filterByProject(project: string) {
    const cards = document.querySelectorAll('[data-project]');
    cards.forEach(card => {
      if (project === 'all' || card.getAttribute('data-project') === project) {
        card.classList.remove('hidden');
      } else {
        card.classList.add('hidden');
      }
    });
  }
</script>
```

Update digest cards to include `data-project`:

```astro
{digests.map((digest) => (
  <a
    href={`/digest/${digest.filename}`}
    data-project={digest.project}
    class="block bg-white rounded-lg border border-gray-200 p-6 hover:shadow-md hover:border-blue-300 transition-all"
  >
```

### 4. Change Tag Badge Styles

**File**: `src/components/TagBadge.astro`

**Make tags larger and bolder:**

Line 46-50:
```astro
<!-- From: -->
<span class:list={[
  'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border',
  colorClasses
]}>

<!-- To: -->
<span class:list={[
  'inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold border-2',
  colorClasses
]}>
```

**Change category colors** (line 16-24):

```astro
const categoryColors: Record<string, string> = {
  technical: 'bg-indigo-100 text-indigo-900 border-indigo-400',
  industry: 'bg-rose-100 text-rose-900 border-rose-400',
  tutorial: 'bg-emerald-100 text-emerald-900 border-emerald-400',
  discussion: 'bg-sky-100 text-sky-900 border-sky-400',
  news: 'bg-orange-100 text-orange-900 border-orange-400',
  // ... etc
};
```

### 5. Add Story Excerpt/Preview

**File**: `src/components/StoryCard.astro`

**First, modify the Story type** to include excerpt in `src/types/digest.ts`:

```typescript
export interface Story {
  // ... existing fields ...
  excerpt?: string;  // Add this
}
```

**Then add excerpt display** after tags (around line 62):

```astro
{story.format_tag && (
  <TagBadge tag={story.format_tag} type="format" />
)}
</div>

<!-- NEW: Excerpt preview -->
{story.excerpt && (
  <p class="text-sm text-gray-600 mt-3 line-clamp-3">
    {story.excerpt}
  </p>
)}
```

**Note**: You'll need to modify your Python digest generator to include excerpts in the JSON.

### 6. Add Sort Options to Digest List

**File**: `src/pages/index.astro`

**Add sort buttons** after the header:

```astro
<div class="mb-4 flex gap-2">
  <button
    onclick="sortDigests('date')"
    class="px-3 py-1 rounded text-sm bg-gray-200 hover:bg-gray-300"
  >
    Sort by Date
  </button>
  <button
    onclick="sortDigests('stories')"
    class="px-3 py-1 rounded text-sm bg-gray-200 hover:bg-gray-300"
  >
    Sort by Story Count
  </button>
</div>
```

**Add script**:

```astro
<script>
  function sortDigests(by: 'date' | 'stories') {
    const container = document.getElementById('digests-container');
    const cards = Array.from(container!.children);

    cards.sort((a, b) => {
      if (by === 'date') {
        const dateA = a.getAttribute('data-date') || '';
        const dateB = b.getAttribute('data-date') || '';
        return dateB.localeCompare(dateA);
      } else {
        const countA = parseInt(a.getAttribute('data-story-count') || '0');
        const countB = parseInt(b.getAttribute('data-story-count') || '0');
        return countB - countA;
      }
    });

    cards.forEach(card => container!.appendChild(card));
  }
</script>
```

**Update container** (line 58):

```astro
<div class="space-y-4" id="digests-container">
  {digests.map((digest) => (
    <a
      data-date={digest.generated_at}
      data-story-count={digest.story_count}
      href={`/digest/${digest.filename}`}
      ...
```

### 7. Change Card Hover Effects

**File**: `src/components/StoryCard.astro`

**More dramatic hover** (line 22):

```astro
<!-- From: -->
<article class="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition-shadow">

<!-- To: -->
<article class="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-xl hover:scale-105 hover:border-blue-400 transition-all duration-200">
```

This adds:
- Larger shadow on hover
- Slight scale-up effect (5%)
- Blue border on hover
- Smooth transition for all properties

### 8. Add Icons to Source Names

**File**: `src/components/StoryCard.astro`

Already implemented! But you can change the icons (line 13-17):

```astro
const getSourceIcon = (source: string): string => {
  if (source.startsWith('r/')) return '🔴';  // Change to '📱' or other
  if (source.includes('HN')) return '🟠';    // Change to '💻' or other
  return '📰';                                // Default icon
};
```

### 9. Add Search Functionality

**File**: `src/pages/index.astro`

**Add search input** after header:

```astro
<div class="mb-6">
  <input
    type="text"
    id="search"
    placeholder="Search digests..."
    oninput="searchDigests()"
    class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
  />
</div>
```

**Add search script**:

```astro
<script>
  function searchDigests() {
    const query = (document.getElementById('search') as HTMLInputElement).value.toLowerCase();
    const cards = document.querySelectorAll('[data-searchable]');

    cards.forEach(card => {
      const text = card.getAttribute('data-searchable') || '';
      if (text.toLowerCase().includes(query)) {
        card.classList.remove('hidden');
      } else {
        card.classList.add('hidden');
      }
    });
  }
</script>
```

**Update digest cards**:

```astro
<a
  data-searchable={`${digest.project} ${formatDate(digest.generated_at)}`}
  href={`/digest/${digest.filename}`}
  ...
```

### 10. Add Footer Links

**File**: `src/layouts/Layout.astro`

**Enhance footer** (line 43):

```astro
<footer class="border-t border-gray-200 mt-12 bg-white">
  <div class="max-w-4xl mx-auto px-4 py-8">
    <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
      <!-- Column 1 -->
      <div>
        <h3 class="font-bold text-gray-900 mb-2">About</h3>
        <p class="text-sm text-gray-500">
          AI-curated content digests from Reddit and Hacker News.
        </p>
      </div>

      <!-- Column 2 -->
      <div>
        <h3 class="font-bold text-gray-900 mb-2">Links</h3>
        <ul class="text-sm text-gray-500 space-y-1">
          <li><a href="/" class="hover:text-blue-600">Home</a></li>
          <li><a href="/bookmarks" class="hover:text-blue-600">Bookmarks</a></li>
        </ul>
      </div>

      <!-- Column 3 -->
      <div>
        <h3 class="font-bold text-gray-900 mb-2">Built With</h3>
        <ul class="text-sm text-gray-500 space-y-1">
          <li>Astro</li>
          <li>Tailwind CSS</li>
          <li>Claude AI</li>
        </ul>
      </div>
    </div>

    <div class="border-t border-gray-200 mt-6 pt-6 text-center text-sm text-gray-500">
      Generated by Claude Redditor
    </div>
  </div>
</footer>
```

## Testing Your Changes

### 1. Development Mode

```bash
cd web
npm run dev
# Visit http://localhost:4321
# Edit files, see changes instantly
```

### 2. Build for Production

```bash
cd web
npm run build
npm run preview
# Visit http://localhost:4321
# Test the production build
```

### 3. Check for Errors

Watch the terminal for TypeScript errors or build warnings.

## Common Issues and Fixes

### Issue: Changes don't appear

**Solution**: Hard refresh your browser (Ctrl+Shift+R or Cmd+Shift+R)

### Issue: TypeScript errors

**Solution**: Check that props match their TypeScript interfaces:

```astro
interface Props {
  story: Story;  // Make sure Story type is imported
}
```

### Issue: Styling looks broken

**Solution**: Check class names are valid Tailwind classes. Use the [Tailwind docs](https://tailwindcss.com/docs).

### Issue: Build fails

**Solution**: Check that all JSON files exist in `../outputs/web/`

## Key Takeaways

1. **Dev Server**: Use `npm run dev` for instant feedback
2. **Build**: Always test with `npm run build` before deploying
3. **Tailwind**: Change appearance by swapping utility classes
4. **Components**: Modify components to change all instances at once
5. **TypeScript**: Type errors help catch mistakes early

## Next Steps

You now have the skills to customize your Astro site! Experiment with:

- Different color schemes
- New layouts
- Additional components
- Interactive features with JavaScript

## Cheatsheet

```bash
# Start development
cd web && npm run dev

# Build for production
cd web && npm run build

# Preview production build
cd web && npm run preview

# Install new packages
cd web && npm install package-name
```

**Files to edit for common changes:**

| What to change | File |
|----------------|------|
| Site title/logo | `src/layouts/Layout.astro` |
| Homepage layout | `src/pages/index.astro` |
| Story card appearance | `src/components/StoryCard.astro` |
| Tag colors | `src/components/TagBadge.astro` |
| Global styles | `src/styles/global.css` |
| Digest page | `src/pages/digest/[id].astro` |

---

**Your turn!** Pick a customization from this guide and implement it. Start small, then build up to larger changes. The development server's instant feedback makes experimentation easy and fun!
