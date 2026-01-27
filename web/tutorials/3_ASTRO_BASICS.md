# 3. Astro File Basics

## The `.astro` File Format

An `.astro` file has two parts, separated by `---` fences:

```astro
---
// 1. FRONTMATTER (JavaScript/TypeScript)
// This runs at BUILD TIME (like Python running on your server)
const title = "My Page";
const data = await fetchData();
---

<!-- 2. TEMPLATE (HTML with dynamic parts) -->
<!-- This becomes the HTML sent to browsers -->
<h1>{title}</h1>
<p>Data: {data}</p>
```

### Python Analogy

```python
# This is like a Flask route:
@app.route('/page')
def my_page():
    # This is the "frontmatter" - runs on server
    title = "My Page"
    data = fetch_data()

    # This is the "template" - becomes HTML
    return render_template('page.html', title=title, data=data)
```

## Part 1: Frontmatter (The JavaScript Part)

Everything between `---` fences runs **at build time** (or server-side for dynamic routes).

### Importing Modules

```astro
---
// Import other components
import Layout from '../layouts/Layout.astro';
import StoryCard from '../components/StoryCard.astro';

// Import Node.js modules (only works in frontmatter!)
import fs from 'node:fs';
import path from 'node:path';

// Import TypeScript types
import type { Digest } from '../types/digest';
---
```

### Reading Data (Your Current Pages Do This!)

**Example from `index.astro`:**

```astro
---
// Read JSON files from your Python output
const digestsDir = path.resolve('../outputs/web');
const files = fs.readdirSync(digestsDir)
  .filter(f => f.endsWith('.json'));

// Parse each JSON file
const digests = files.map(filename => {
  const content = fs.readFileSync(path.join(digestsDir, filename), 'utf-8');
  const data = JSON.parse(content);
  return {
    digest_id: data.digest_id,
    project: data.project,
    // ... extract what you need
  };
});
---

<!-- Now use 'digests' in your template -->
<div>Found {digests.length} digests</div>
```

**Python equivalent:**
```python
import os
import json

digests_dir = '../outputs/web'
files = [f for f in os.listdir(digests_dir) if f.endswith('.json')]

digests = []
for filename in files:
    with open(os.path.join(digests_dir, filename)) as f:
        data = json.load(f)
        digests.append({
            'digest_id': data['digest_id'],
            'project': data['project'],
        })
```

### Defining Props (Component Inputs)

**Example from `StoryCard.astro`:**

```astro
---
import type { Story } from '../types/digest';

interface Props {
  story: Story;
  showReasoning?: boolean;  // Optional prop (? means optional)
}

// Extract props from Astro.props
const { story, showReasoning = false } = Astro.props;
---

<!-- Use props in template -->
<h2>{story.title}</h2>
```

**Python equivalent:**
```python
def story_card(story: Story, show_reasoning: bool = False):
    # story and show_reasoning are like "props"
    return f"<h2>{story.title}</h2>"
```

## Part 2: Template (The HTML Part)

After the frontmatter, you write HTML with dynamic parts.

### Inserting Variables

```astro
---
const name = "Claude";
const count = 42;
---

<p>Hello, {name}!</p>          <!-- Output: Hello, Claude! -->
<p>Count: {count * 2}</p>       <!-- Output: Count: 84 -->
```

**Python Jinja2 equivalent:**
```jinja2
<p>Hello, {{ name }}!</p>
<p>Count: {{ count * 2 }}</p>
```

### Conditional Rendering

```astro
---
const isLoggedIn = true;
---

{isLoggedIn ? (
  <p>Welcome back!</p>
) : (
  <p>Please log in</p>
)}
```

Or use `&&` for simple conditions:

```astro
{isLoggedIn && <p>Welcome back!</p>}
```

**Python equivalent:**
```python
{% if is_logged_in %}
  <p>Welcome back!</p>
{% else %}
  <p>Please log in</p>
{% endif %}
```

### Loops (Mapping Arrays)

**Example from your `index.astro`:**

```astro
---
const digests = [...]; // Array of digest objects
---

<div>
  {digests.map((digest) => (
    <a href={`/digest/${digest.filename}`}>
      <h2>{digest.project}</h2>
      <span>{digest.story_count} stories</span>
    </a>
  ))}
</div>
```

**Python equivalent:**
```python
{% for digest in digests %}
  <a href="/digest/{{ digest.filename }}">
    <h2>{{ digest.project }}</h2>
    <span>{{ digest.story_count }} stories</span>
  </a>
{% endfor %}
```

### Using Components

Components work like function calls:

```astro
---
import TagBadge from './TagBadge.astro';
---

<!-- Pass props like function arguments -->
<TagBadge tag="Python" type="topic" />
<TagBadge tag="tutorial" type="category" />
```

## Real Example from Your Project

Let's analyze `src/components/TagBadge.astro`:

```astro
---
// FRONTMATTER - Runs at build time
interface Props {
  tag: string;          // Required prop
  type: 'topic' | 'format' | 'category';  // Must be one of these
}

const { tag, type } = Astro.props;  // Extract props

// Function to determine color based on type/tag
const getColorClasses = (tag: string, type: string): string => {
  if (type === 'category') {
    const colors = {
      technical: 'bg-blue-100 text-blue-800',
      industry: 'bg-purple-100 text-purple-800',
      // ... more colors
    };
    return colors[tag.toLowerCase()] || 'bg-gray-100';
  }
  // ... more logic
};

const colorClasses = getColorClasses(tag, type);
---

<!-- TEMPLATE - Becomes HTML -->
<span class:list={['inline-flex items-center px-2 py-0.5 rounded-full', colorClasses]}>
  {type === 'format' && <span class="mr-1 opacity-60">#</span>}
  {tag}
</span>
```

**What this does:**
1. Accepts `tag` and `type` as inputs (props)
2. Calculates the right color classes based on type
3. Renders a colored badge with the tag name
4. Adds a `#` symbol for format tags

## Special Astro Features

### `class:list` - Dynamic Classes

```astro
<div class:list={['base-class', someCondition && 'conditional-class', dynamicClass]}>
```

### `set:html` - Insert HTML Strings

```astro
---
const htmlString = "<strong>Bold</strong>";
---
<div set:html={htmlString} />  <!-- Renders: <div><strong>Bold</strong></div> -->
```

### Slots - Like Children in React

```astro
<!-- Layout.astro -->
<div class="wrapper">
  <slot />  <!-- Child content goes here -->
</div>

<!-- Using the layout -->
<Layout>
  <p>This content replaces the slot</p>
</Layout>
```

## Common Patterns

### Loading JSON Data

```astro
---
import fs from 'node:fs';
const data = JSON.parse(fs.readFileSync('data.json', 'utf-8'));
---

<pre>{JSON.stringify(data, null, 2)}</pre>
```

### Formatting Dates

```astro
---
const formatDate = (dateStr: string): string => {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
};
---

<time>{formatDate('2026-01-27')}</time>
```

## Key Takeaways

1. **Frontmatter (---)**: JavaScript code that runs at build time
2. **Template (HTML)**: Uses `{variable}` for dynamic content
3. **Props**: Components accept inputs via `Astro.props`
4. **Loops**: Use `.map()` instead of `{% for %}`
5. **Conditions**: Use `? :` or `&&` instead of `{% if %}`

## Next Steps

Tutorial 4 will explore your components in detail and show you how to modify them.

---

**Try this:**
Edit `src/pages/index.astro` and change line 46:
```astro
<h1 class="text-3xl font-bold text-gray-900 mb-2">Content Digests</h1>
```
to:
```astro
<h1 class="text-3xl font-bold text-gray-900 mb-2">My Awesome Digests! 🚀</h1>
```

Run `npm run dev` and see the change!
