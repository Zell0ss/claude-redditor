# 6. Styling with Tailwind CSS

## What is Tailwind CSS?

Tailwind is a **utility-first CSS framework**. Instead of writing CSS files, you use pre-made classes directly in HTML.

**Traditional CSS:**
```html
<style>
  .card {
    background-color: white;
    border-radius: 8px;
    padding: 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  }
</style>

<div class="card">Content</div>
```

**Tailwind CSS:**
```html
<div class="bg-white rounded-lg p-4 shadow">Content</div>
```

No CSS file needed! Classes describe exactly what they do.

## Tailwind Basics

### Spacing

Tailwind uses a scale: `0, 1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24, ...`

| Class | CSS | Pixels |
|-------|-----|--------|
| `p-4` | `padding: 1rem` | 16px |
| `px-4` | `padding-left: 1rem; padding-right: 1rem` | 16px horizontal |
| `py-4` | `padding-top: 1rem; padding-bottom: 1rem` | 16px vertical |
| `m-4` | `margin: 1rem` | 16px |
| `mt-4` | `margin-top: 1rem` | 16px |
| `gap-4` | `gap: 1rem` | 16px (for flex/grid) |

**Examples from your code:**
```astro
<div class="px-4 py-8">  <!-- 16px horizontal padding, 32px vertical -->
<div class="mb-3">       <!-- 12px bottom margin -->
<div class="gap-2">      <!-- 8px gap between flex items -->
```

### Colors

Format: `{property}-{color}-{shade}`

| Class | Meaning |
|-------|---------|
| `bg-gray-50` | Background: very light gray |
| `bg-gray-900` | Background: very dark gray |
| `text-blue-600` | Text: medium blue |
| `border-red-200` | Border: light red |

**Shade scale**: 50 (lightest) → 100, 200, 300, 400, 500, 600, 700, 800, 900 (darkest)

**Your TagBadge colors:**
```astro
<!-- Category: technical -->
<span class="bg-blue-100 text-blue-800 border-blue-300">
  <!-- Light blue background, dark blue text, medium blue border -->
</span>
```

### Typography

| Class | CSS |
|-------|-----|
| `text-xs` | `font-size: 0.75rem` (12px) |
| `text-sm` | `font-size: 0.875rem` (14px) |
| `text-base` | `font-size: 1rem` (16px) |
| `text-lg` | `font-size: 1.125rem` (18px) |
| `text-xl` | `font-size: 1.25rem` (20px) |
| `text-2xl` | `font-size: 1.5rem` (24px) |
| `text-3xl` | `font-size: 1.875rem` (30px) |
| `font-bold` | `font-weight: 700` |
| `font-semibold` | `font-weight: 600` |
| `font-medium` | `font-weight: 500` |

**Your page title:**
```astro
<h1 class="text-3xl font-bold text-gray-900 mb-2">
  <!-- 30px, bold, dark gray, 8px bottom margin -->
  Content Digests
</h1>
```

### Layout

#### Flexbox

```astro
<div class="flex items-center justify-between gap-4">
  <!-- display: flex -->
  <!-- align-items: center -->
  <!-- justify-content: space-between -->
  <!-- gap: 1rem -->
</div>
```

Common flex classes:
- `flex` - Enable flexbox
- `flex-col` - Column direction (vertical)
- `flex-wrap` - Allow wrapping
- `items-center` - Align items vertically centered
- `items-start` - Align items to top
- `justify-between` - Space between items
- `justify-center` - Center items
- `gap-4` - Space between items

**Your nav bar:**
```astro
<div class="flex items-center justify-between">
  <!-- Logo on left, nav links on right, vertically centered -->
  <a href="/">Logo</a>
  <nav>Links</nav>
</div>
```

#### Sizing

| Class | Meaning |
|-------|---------|
| `w-full` | Width: 100% |
| `h-screen` | Height: 100vh (full viewport) |
| `min-h-screen` | Min height: 100vh |
| `max-w-4xl` | Max width: 896px |
| `mx-auto` | Margin horizontal: auto (centers) |

**Your main content:**
```astro
<main class="max-w-4xl mx-auto px-4 py-8">
  <!-- Max 896px wide, centered, 16px horizontal padding, 32px vertical -->
</main>
```

### Borders & Rounded Corners

| Class | CSS |
|-------|-----|
| `border` | `border-width: 1px` |
| `border-2` | `border-width: 2px` |
| `border-t` | Top border only |
| `border-gray-200` | Border color: light gray |
| `rounded` | `border-radius: 0.25rem` (4px) |
| `rounded-lg` | `border-radius: 0.5rem` (8px) |
| `rounded-full` | `border-radius: 9999px` (pill shape) |

**Your story card:**
```astro
<article class="bg-white rounded-lg border border-gray-200">
  <!-- White background, 8px corners, 1px light gray border -->
</article>
```

### Shadows

| Class | Effect |
|-------|--------|
| `shadow` | Small shadow |
| `shadow-md` | Medium shadow |
| `shadow-lg` | Large shadow |

**Your hover effect:**
```astro
<div class="hover:shadow-md transition-shadow">
  <!-- Shadow appears on hover, smooth transition -->
</div>
```

### States (Hover, Focus, etc.)

Prefix classes with state names:

```astro
<!-- Normal: blue text. Hover: darker blue -->
<a class="text-blue-600 hover:text-blue-800">Link</a>

<!-- Normal: no shadow. Hover: shadow appears -->
<div class="hover:shadow-md">Card</div>

<!-- Focus state for inputs -->
<input class="border focus:border-blue-500 focus:ring-2" />
```

## Analyzing Your Current Styles

### Story Card

```astro
<article class="
  bg-white           ← White background
  rounded-lg         ← 8px rounded corners
  border             ← 1px border
  border-gray-200    ← Light gray border
  p-4                ← 16px padding all sides
  hover:shadow-md    ← Shadow on hover
  transition-shadow  ← Smooth shadow transition
">
```

### Tag Badge

```astro
<span class="
  inline-flex        ← Inline flex container
  items-center       ← Vertically center content
  px-2               ← 8px horizontal padding
  py-0.5             ← 2px vertical padding
  rounded-full       ← Pill shape
  text-xs            ← 12px font size
  font-medium        ← Semi-bold font
  border             ← 1px border
  bg-blue-100        ← Light blue background
  text-blue-800      ← Dark blue text
  border-blue-300    ← Medium blue border
">
```

### Navigation Bar

```astro
<nav class="
  bg-white           ← White background
  border-b           ← Bottom border only
  border-gray-200    ← Light gray border
  sticky             ← Stick to viewport when scrolling
  top-0              ← Stick to top
  z-50               ← Layer above other content
">
```

## Common Patterns in Your Code

### Spacing Utilities

```astro
<!-- Vertical spacing between elements -->
<div class="space-y-4">
  <div>Item 1</div>  <!-- 16px margin-top (except first) -->
  <div>Item 2</div>
  <div>Item 3</div>
</div>

<!-- Horizontal spacing -->
<div class="space-x-4">
  <span>Tag 1</span>  <!-- 16px margin-left (except first) -->
  <span>Tag 2</span>
</div>
```

### Responsive Classes

```astro
<!-- Hide on small screens, show on medium+ -->
<div class="hidden md:block">Desktop only</div>

<!-- Stack vertically on mobile, horizontal on desktop -->
<div class="flex flex-col md:flex-row">
  <div>Item 1</div>
  <div>Item 2</div>
</div>
```

Breakpoints:
- `sm:` - 640px and up
- `md:` - 768px and up
- `lg:` - 1024px and up
- `xl:` - 1280px and up

### Conditional Classes with `class:list`

Astro's special feature for dynamic classes:

```astro
---
const isActive = true;
const variant = 'primary';
---

<div class:list={[
  'base-class',                    ← Always applied
  isActive && 'active-class',      ← Applied if isActive is true
  variant === 'primary' && 'primary-class',  ← Applied if variant is 'primary'
  {
    'conditional': someCondition,  ← Object syntax
    'another': anotherCondition
  }
]}>
```

**Example from your StoryCard:**

```astro
<span class:list={[
  'font-medium',
  story.confidence >= 0.9 ? 'text-green-600' :
  story.confidence >= 0.7 ? 'text-amber-600' : 'text-red-600'
]}>
  {Math.round(story.confidence * 100)}%
</span>
```

## Custom Colors in global.css

Your `src/styles/global.css`:

```css
@import "tailwindcss";

@theme {
  /* Define custom colors */
  --color-tag-blue: #3b82f6;
  --color-tag-green: #22c55e;
  /* ... more colors */
}
```

These extend Tailwind's default colors.

## Making Style Changes

### Change Color Scheme

**Make all blue tags purple:**

Find in `TagBadge.astro`:
```astro
const categoryColors = {
  technical: 'bg-blue-100 text-blue-800 border-blue-300',  // OLD
  // Change to:
  technical: 'bg-purple-100 text-purple-800 border-purple-300',  // NEW
};
```

### Change Card Appearance

**Add shadow to all story cards by default:**

In `StoryCard.astro`:
```astro
<article class="bg-white rounded-lg border border-gray-200 p-4 shadow-md">
  <!-- Added shadow-md, removed hover:shadow-md -->
</article>
```

**Make cards more compact:**

```astro
<article class="bg-white rounded border border-gray-200 p-2">
  <!-- Changed: rounded-lg → rounded, p-4 → p-2 -->
</article>
```

### Change Typography

**Make all titles larger:**

In `StoryCard.astro`:
```astro
<a href={`/story/${story.id}`} class="text-2xl font-bold">
  <!-- Changed: text-lg font-semibold → text-2xl font-bold -->
  {story.title}
</a>
```

**Change page title color:**

In `index.astro`:
```astro
<h1 class="text-3xl font-bold text-blue-900 mb-2">
  <!-- Changed: text-gray-900 → text-blue-900 -->
  Content Digests
</h1>
```

### Change Layout Width

**Make content wider:**

In `Layout.astro`:
```astro
<main class="max-w-6xl mx-auto px-4 py-8">
  <!-- Changed: max-w-4xl (896px) → max-w-6xl (1152px) -->
</main>
```

### Change Navigation Style

**Dark navigation:**

In `Layout.astro`:
```astro
<nav class="bg-gray-900 border-b border-gray-700">
  <div class="max-w-4xl mx-auto px-4 py-3">
    <a href="/" class="text-white hover:text-blue-400">
      <!-- Changed text colors for dark background -->
      Digest Viewer
    </a>
  </div>
</nav>
```

## Tailwind Cheatsheet for Your Project

### Most Used Classes

```
Spacing:      p-4 px-4 py-8 m-4 mt-2 mb-3 gap-2 space-y-4
Colors:       bg-white text-gray-900 border-gray-200
              bg-blue-100 text-blue-800
Typography:   text-xs text-sm text-lg text-3xl
              font-medium font-semibold font-bold
Layout:       flex items-center justify-between gap-4
              max-w-4xl mx-auto
Borders:      border rounded rounded-lg rounded-full
States:       hover:shadow-md hover:text-blue-600
Misc:         transition-shadow sticky top-0 z-50
```

## Key Takeaways

1. **Utility Classes**: Each class does one thing (`p-4` = padding)
2. **No CSS Files**: Style directly in HTML
3. **Consistent Scale**: Use predefined spacing/colors
4. **State Modifiers**: `hover:`, `focus:`, etc.
5. **Responsive**: `md:`, `lg:` for different screen sizes
6. **Composition**: Combine many classes to build complex styles

## Next Steps

Tutorial 7 will show you practical, step-by-step guides to customize your site's look.

---

**Try this:**
Change your story cards to have a colored left border based on confidence:

```astro
<article class:list={[
  'bg-white rounded-lg border-l-4 border-r border-t border-b',
  story.confidence >= 0.9 ? 'border-l-green-500' :
  story.confidence >= 0.7 ? 'border-l-amber-500' : 'border-l-red-500',
  'border-r-gray-200 border-t-gray-200 border-b-gray-200',
  'p-4'
]}>
```
