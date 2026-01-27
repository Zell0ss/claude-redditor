# 4. Understanding Components

## What is a Component?

A component is a **reusable piece of UI**. Instead of copying HTML everywhere, you create a component once and reuse it.

**Python analogy:**
```python
# Without components (repetition)
def page1():
    return "<div class='card'>Story 1</div><div class='card'>Story 2</div>"

# With components (reusable function)
def story_card(title):
    return f"<div class='card'>{title}</div>"

def page1():
    return story_card("Story 1") + story_card("Story 2")
```

## Your Components

Your project has 3 main components:

| Component | Purpose | Used In |
|-----------|---------|---------|
| `TagBadge.astro` | Colored tag badges | StoryCard, everywhere |
| `StoryCard.astro` | Display a single story | digest pages |
| `BookmarkCard.astro` | Display a bookmark | bookmarks page |

## Deep Dive: TagBadge.astro

This is your simplest component. Let's understand every line:

```astro
---
// 1. DEFINE PROPS (What inputs does this component accept?)
interface Props {
  tag: string;                              // The tag text (e.g., "Python", "AI")
  type: 'topic' | 'format' | 'category';    // What kind of tag is it?
}

// 2. EXTRACT PROPS
const { tag, type } = Astro.props;

// 3. LOGIC - Determine color based on type and tag
const getColorClasses = (tag: string, type: string): string => {
  // Format tags are always gray
  if (type === 'format') {
    return 'bg-gray-100 text-gray-700 border-gray-300';
  }

  // Category tags have specific colors
  if (type === 'category') {
    const categoryColors: Record<string, string> = {
      technical: 'bg-blue-100 text-blue-800 border-blue-300',
      industry: 'bg-purple-100 text-purple-800 border-purple-300',
      tutorial: 'bg-green-100 text-green-800 border-green-300',
      // ... more categories
    };
    return categoryColors[tag.toLowerCase()] || 'bg-slate-100 text-slate-700';
  }

  // Topic tags rotate through colors based on tag name hash
  const topicColors = [
    'bg-blue-100 text-blue-800 border-blue-300',
    'bg-green-100 text-green-800 border-green-300',
    'bg-purple-100 text-purple-800 border-purple-300',
    // ... more colors
  ];

  // Simple hash: sum character codes
  const hash = tag.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
  return topicColors[hash % topicColors.length];  // Pick color by hash
};

const colorClasses = getColorClasses(tag, type);
---

<!-- 4. TEMPLATE - Render the badge -->
<span
  class:list={[
    'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border',
    colorClasses  <!-- Add the dynamic color classes -->
  ]}
>
  <!-- Show # symbol for format tags -->
  {type === 'format' && <span class="mr-1 opacity-60">#</span>}
  {tag}
</span>
```

### How to Use TagBadge

```astro
---
import TagBadge from './components/TagBadge.astro';
---

<!-- Different types of tags -->
<TagBadge tag="Python" type="topic" />         <!-- Blue/green/purple badge -->
<TagBadge tag="technical" type="category" />   <!-- Blue badge -->
<TagBadge tag="article" type="format" />       <!-- Gray badge with # -->
```

## Deep Dive: StoryCard.astro

This component displays a complete story with metadata. Let's break it down:

```astro
---
import type { Story } from '../types/digest';
import TagBadge from './TagBadge.astro';

// Props definition
interface Props {
  story: Story;              // The story object from your JSON
  showReasoning?: boolean;   // Optional: show classification reasoning
}

const { story, showReasoning = false } = Astro.props;

// Helper function: Pick emoji based on source
const getSourceIcon = (source: string): string => {
  if (source.startsWith('r/')) return '🔴';  // Reddit
  if (source.includes('HN')) return '🟠';    // Hacker News
  return '📰';                                // Other
};

const sourceIcon = getSourceIcon(story.source);
---

<article class="bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md transition-shadow">
  <!-- HEADER: Title and metadata -->
  <header class="mb-3">
    <!-- Story title (link to detail page) -->
    <a href={`/story/${story.id}`} class="text-lg font-semibold">
      {story.title}
    </a>

    <!-- Metadata line: source, author, score, comments -->
    <div class="flex items-center gap-3 mt-2 text-sm text-gray-500">
      <span>{sourceIcon} {story.source}</span>
      <span>by {story.author}</span>

      {story.score > 0 && (
        <span>▲ {story.score}</span>
      )}

      {story.num_comments > 0 && (
        <span>💬 {story.num_comments}</span>
      )}
    </div>
  </header>

  <!-- TAGS: Category, topics, format -->
  <div class="flex flex-wrap gap-2 mb-3">
    <TagBadge tag={story.category} type="category" />

    {story.topic_tags.map((tag) => (
      <TagBadge tag={tag} type="topic" />
    ))}

    {story.format_tag && (
      <TagBadge tag={story.format_tag} type="format" />
    )}
  </div>

  <!-- RED FLAGS (if any) -->
  {story.red_flags.length > 0 && (
    <div class="flex flex-wrap gap-1 mb-3">
      {story.red_flags.map((flag) => (
        <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-50 text-red-700">
          ⚠️ {flag}
        </span>
      ))}
    </div>
  )}

  <!-- REASONING (optional) -->
  {showReasoning && story.reasoning && (
    <p class="text-sm text-gray-600 mt-3 pt-3 border-t border-gray-100">
      {story.reasoning}
    </p>
  )}

  <!-- FOOTER: ID and confidence -->
  <footer class="mt-3 flex items-center justify-between text-xs text-gray-400">
    <span>ID: {story.id}</span>
    <span class="flex items-center gap-1">
      <span>Confidence:</span>
      <!-- Color based on confidence level -->
      <span class:list={[
        'font-medium',
        story.confidence >= 0.9 ? 'text-green-600' :
        story.confidence >= 0.7 ? 'text-amber-600' : 'text-red-600'
      ]}>
        {Math.round(story.confidence * 100)}%
      </span>
    </span>
  </footer>
</article>
```

### Key Features

1. **Source icon**: 🔴 for Reddit, 🟠 for HN
2. **Conditional rendering**: Only show score/comments if > 0
3. **Multiple tags**: Category + topics + format
4. **Red flags**: Warning badges if present
5. **Confidence coloring**: Green (>90%), amber (>70%), red (<70%)

### How to Use StoryCard

```astro
---
import StoryCard from '../components/StoryCard.astro';
import type { Digest } from '../types/digest';

// Load digest data
const digest: Digest = ...;
---

<!-- Render each story -->
{digest.stories.map((story) => (
  <StoryCard story={story} showReasoning={true} />
))}
```

## Creating Your Own Component

Let's create a simple component from scratch:

**Create `src/components/ProjectBadge.astro`:**

```astro
---
interface Props {
  project: string;
}

const { project } = Astro.props;

// Map project to color
const getProjectColor = (project: string): string => {
  const colors: Record<string, string> = {
    claudeia: 'bg-blue-100 text-blue-800',
    wineworld: 'bg-purple-100 text-purple-800',
  };
  return colors[project] || 'bg-gray-100 text-gray-800';
};

const colorClass = getProjectColor(project);
---

<div class:list={['inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium', colorClass]}>
  <span>📁</span>
  <span>{project}</span>
</div>
```

**Use it:**

```astro
---
import ProjectBadge from '../components/ProjectBadge.astro';
---

<ProjectBadge project="claudeia" />    <!-- Blue badge -->
<ProjectBadge project="wineworld" />   <!-- Purple badge -->
```

## Component Best Practices

### 1. Keep Components Focused

Each component should do ONE thing well:
- ✅ `TagBadge` - displays a tag
- ✅ `StoryCard` - displays a story
- ❌ `SuperMegaCard` - displays story + comments + related posts + ads

### 2. Use TypeScript Props

Always define prop types:

```astro
---
interface Props {
  title: string;      // Required
  count?: number;     // Optional (? means optional)
}
---
```

### 3. Extract Logic to Functions

Move complex logic to functions in frontmatter:

```astro
---
// Good: Logic in function
const formatDate = (date: string) => new Date(date).toLocaleDateString();
const formattedDate = formatDate(story.created_at);
---

<time>{formattedDate}</time>
```

### 4. Default Props

Provide sensible defaults:

```astro
---
const { showReasoning = false } = Astro.props;  // Defaults to false
---
```

## Modifying Components

Want to change how stories look? Edit `StoryCard.astro`:

```astro
<!-- Change title size -->
<a href={`/story/${story.id}`} class="text-2xl font-bold">  <!-- was text-lg -->
  {story.title}
</a>

<!-- Add border around red flags -->
{story.red_flags.length > 0 && (
  <div class="border-2 border-red-300 rounded p-2">  <!-- NEW! -->
    {story.red_flags.map((flag) => (
      <span class="...">⚠️ {flag}</span>
    ))}
  </div>
)}
```

## Key Takeaways

1. **Components = Reusable Functions**: Pass props, get HTML
2. **Props = Inputs**: Defined with TypeScript interfaces
3. **Logic in Frontmatter**: Keep template clean
4. **Composition**: Components can use other components
5. **Single Responsibility**: Each component does one thing

## Next Steps

Tutorial 5 will cover layouts and pages, showing how components fit into full pages.

---

**Try this:**
Create a new component `ScoreBadge.astro` that displays the story score with an up arrow:
```astro
---
interface Props {
  score: number;
}
const { score } = Astro.props;
---
<span class="bg-orange-100 text-orange-800 px-2 py-1 rounded">
  ▲ {score}
</span>
```

Use it in `StoryCard.astro` instead of the inline score display!
