# Search schema (Tantivy)

Contract between this repo's scoped catalog and `cbeta-mcp`.
Index id: `{cbeta_tag}+{scope_hash}` (see README). Scope change always rebuilds.

## Engine choice

| Option | Use? | Reason |
|---|---|---|
| **Tantivy** (Rust, mmap) | yes, default | Lucene-class, no daemon, concurrent readers |
| SQLite FTS5 trigram | fallback only | weaker phrase + facets |
| Meilisearch / ES | no | extra server, not offline-first |
| jieba-only tokenizer | no | fails on 佛典/偈颂; char n-gram is required |

## Units (one Tantivy doc each)

| `unit_type` | Source | Role |
|---|---|---|
| `line` | TEI `<lb>` | 頁欄行 lookup |
| `p` | TEI `<p>` | keyword search |
| `l` / `lg` | TEI verse | quote verify |
| `window` | 16–32 chars, step 8 | short near-miss recall |

Default search: `p` + `lg`. `verify_quote`: `lg` → `window` → `p`.
Text field uses `<lem>` (CBETA/Taishō). `<rdg>` goes to `variants`.

## Fields

Identity: `doc_id`, `cbeta_tag`, `canon`, `work_id`, `xml_id`, `volume`, `juan`, `line_id` (`T30n1578_p0268a12`), `pb`, `lb`, `unit_type`.

Filters (facet): `title`, `author`, `translator`, `dynasty`, `category`, `work_type` (`jing|lun|lv|shu`), `license_class` (`A` CC / `B` restricted).

Text:

| Field | Tokenizer | Purpose |
|---|---|---|
| `text_raw` | none, stored | display |
| `text_norm` | none, stored | NFKC + OpenCC + strip punct |
| `text_ngram` | CJK char 2–3-gram | keyword / fuzzy recall |
| `text_phrase` | CJK char unigram + positions | exact phrase |
| `text_hash` | blake3(`text_norm`) | O(1) original hit |

Sidecar (not Tantivy): optional `vectors.usearch`, `simhash64`.

## Query

```text
search({ q, mode: keyword|phrase|fuzzy, filters, limit, offset })
```

`fuzzy` = n-gram recall then RapidFuzz on top 200 `text_norm`.
Return `doc_id, work_id, title, juan, line_id, text_raw, score, cbeta_tag`.

## Concurrency and artifacts

- One writer; atomic rename `index/{tag}-{scope_hash}.tmp` → final.
- Many mmap readers. HTTP MCP shares one `IndexReader`.
- Artifact: `MANIFEST.json` + `catalog.sqlite` + `tantivy/` + `quote-hash.sqlite`.
