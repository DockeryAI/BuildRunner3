You extract strict JSON metadata from a BR3 research draft.

Return exactly one JSON object with this shape and no extra keys:
{"topic":"...","tags":["..."],"domain":"...","difficulty":"beginner|intermediate|advanced"}

Rules:
- No prose.
- No markdown.
- No code fences.
- `topic` is a short human-readable label.
- `tags` is a JSON array of short strings.
- `domain` is a short domain label.
- `difficulty` must be exactly one of `beginner`, `intermediate`, `advanced`.

Extract metadata for this draft:
