export interface Story {
  id: string;
  post_id?: string;
  title: string;
  source: string;
  author: string;
  url: string;
  score: number;
  num_comments: number;
  category: string;
  confidence: number;
  topic_tags: string[];
  format_tag: string | null;
  red_flags: string[];
  reasoning: string;
  // Article content (from Claude digest generation)
  article_title: string | null;
  article_body: string | null;
  radio_commentary: string | null;
}

export interface Digest {
  digest_id: string;
  generated_at: string;
  project: string;
  story_count: number;
  stories: Story[];
}

export interface DigestIndex {
  digests: DigestMeta[];
}

export interface DigestMeta {
  digest_id: string;
  project: string;
  story_count: number;
  generated_at: string;
  filename: string;
}

export interface Bookmark {
  id: string;
  story_id: string;
  digest_date: string | null;
  bookmarked_at: string | null;
  notes: string | null;
  status: 'to_read' | 'to_implement' | 'done';
  title: string;
  url: string;
  source: string;
  category: string;
  topic_tags: string[];
  format_tag: string | null;
  post_id: string | null;
  author: string;
  score: number;
  num_comments: number;
  confidence: number;
  red_flags: string[];
  reasoning: string;
}

export interface BookmarksExport {
  exported_at: string;
  bookmark_count: number;
  status_filter: string;
  bookmarks: Bookmark[];
}
