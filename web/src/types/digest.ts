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
