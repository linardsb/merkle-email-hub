---
version: "1.0.0"
---

<!-- L4 source: none (original content — RAG pipeline patterns) -->
# RAG Strategies for Email Knowledge

## Query Expansion

When the user's question is short or ambiguous, expand the query:

### Technique 1: Synonym Expansion
- "dark mode" → "dark mode" + "prefers-color-scheme" + "color-scheme" + "data-ogsc"
- "outlook" → "outlook" + "mso" + "word rendering engine" + "microsoft"
- "responsive" → "responsive" + "media query" + "mobile" + "viewport"

### Technique 2: Contextual Expansion
- "how to center" → "center" + "align" + "margin auto" + "table align center"
- "background image" → "background-image" + "VML" + "v:rect" + "v:fill"
- "button" → "button" + "CTA" + "bulletproof button" + "v:roundrect"

### Technique 3: Client-Specific Expansion
When a client is mentioned, also search for:
- Client name + "support" + "css"
- Client name + "rendering engine"
- Client name + "known issues"

## Hybrid Search Parameters

### Semantic Search (Vector)
- Embedding model: Vector(1024) via configured provider
- Similarity metric: cosine distance (HNSW index)
- Top-K: 5-10 results
- Minimum similarity: 0.65 (below this, flag as low confidence)

### Keyword Search (Full-Text)
- PostgreSQL tsvector with english dictionary
- Boost exact matches for CSS property names
- Boost matches in document titles

### Hybrid Fusion
- Reciprocal Rank Fusion (RRF) combining both result sets
- Keyword results slightly boosted for technical queries
- Semantic results boosted for conceptual queries

## Chunk Size Considerations

- **Small chunks (200-500 tokens):** Better for specific CSS property lookups
- **Medium chunks (500-1000 tokens):** Best for pattern explanations with code
- **Large chunks (1000-2000 tokens):** Best for architectural/strategy questions

The knowledge base uses medium chunks by default. For very specific queries,
request multiple small chunks and synthesize.

## Reranking Strategy

After initial retrieval:
1. Score each chunk for relevance to the specific question
2. Boost chunks that contain code examples (for "how to" questions)
3. Boost chunks from authoritative sources (Can I Email, official docs)
4. Demote chunks that are tangentially related
5. Return top 3-5 chunks for answer generation