# Per-book glossary

The authoritative glossary is JSON in the book's work directory. Use this
shape and keep the source examples that justified each decision:

```json
{
  "version": 1,
  "source_language": "English",
  "target_language": "zh-Hant-TW",
  "entries": [
    {
      "source": "social self-efficacy",
      "target": "社會自我效能",
      "sense": "belief in one's ability to perform social behaviours",
      "status": "accepted",
      "variants": ["社交自我效能"],
      "examples": ["Social self-efficacy predicted..."],
      "scope": "book"
    }
  ]
}
```

Allowed statuses are `proposed`, `accepted`, `confirmed`, and `rejected`.
Only `accepted` and `confirmed` entries are rendered to the upstream pin file.
The renderer rejects two accepted targets for the same exact source string;
resolve that case with a longer source phrase or a single clarified sense.

`scripts/render_glossary.py` produces the upstream `term -> translation` file.
The optional `sense` and `examples` stay in the JSON and in the custom prompt
context, while the upstream pin remains compact and is sent only when a term
occurs in a request.

Do not silently add every model suggestion to a long-term personal glossary.
That requires an explicit user request after the book is accepted.
