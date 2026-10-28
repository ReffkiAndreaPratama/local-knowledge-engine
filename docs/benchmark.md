# Retrieval benchmark

This page reports **measured** retrieval quality for the synthetic corpus in
[`sample_documents/`](../sample_documents/) — not estimates. The script builds a
throw-away database, indexes the corpus with the real pipeline, runs a fixed set of
labelled queries through the real search service, and computes document-level
metrics.

Reproduce it yourself:

```bash
cd backend
.venv\Scripts\python.exe ..\scripts\benchmark.py --json ..\docs\benchmark-results.json
# with semantic + hybrid (downloads the model on first run, ~90 MB):
.venv\Scripts\python.exe ..\scripts\benchmark.py --download-model --json ..\docs\benchmark-results.json
```

The full machine-readable output is in
[`benchmark-results.json`](benchmark-results.json).

## Setup

| Item | Value |
|------|-------|
| Corpus | 7 documents / 32 chunks (Markdown, TXT, CSV, HTML) |
| Queries | 12, each with exhaustively labelled relevant document(s) |
| Cut-off | k = 5, `limit` = 10, `max_per_document` = 2 |
| Full-text | SQLite FTS5 + bm25 |
| Semantic | `sentence-transformers/all-MiniLM-L6-v2`, CPU, L2-normalised cosine |
| Hybrid | Reciprocal Rank Fusion of the two ranked lists, k = 60, equal weights |
| Hardware | Windows 10 (19045), Intel 8-core CPU, no GPU |
| Runtime | Python 3.12.10, SQLite 3.49.1, sentence-transformers 6.2.0, torch 2.14.1+cpu |
| Generated | 2026-10-27T16:22:02Z |

Each query is run twice: the first call warms caches/model, the second is timed.
The index lives in a temporary SQLite file, so results do not depend on your own
documents.

## Results

| Mode | P@1 | Hit@5 | Precision@5 | Recall@5 | MRR | nDCG@5 | Mean latency | p95 latency |
|------|-----|-------|-------------|----------|-----|--------|--------------|-------------|
| full-text | **1.000** | 1.000 | 0.217 | 1.000 | **1.000** | **0.993** | 1.4 ms | 2.3 ms |
| semantic | 0.833 | 1.000 | 0.217 | 1.000 | 0.917 | 0.938 | 16.3 ms | 19.0 ms |
| hybrid | 0.917 | 1.000 | 0.217 | 1.000 | 0.958 | 0.969 | 32.2 ms | 183.8 ms |

**Read Precision@5 carefully.** Ten of the twelve queries have exactly one relevant
document, so the maximum attainable P@5 is 0.2 for those. The reported 0.217 is
essentially perfect: the only query with two relevant documents placed both in the
top five. P@1, Hit@5, Recall@5, MRR and nDCG@5 are the meaningful columns here.

The p95 for hybrid (183.8 ms) is a single slow first-call outlier from model
inference; the mean (32.2 ms) is the more representative figure. This is CPU-only
and unoptimised.

## Per-query behaviour

Full-text ranked the correct document first on all 12 queries.

Semantic search placed the correct document second in two cases:

| Query | Relevant | Top result | Cause |
|-------|----------|------------|-------|
| "Which port does the Atlas API listen on?" | `atlas-handbook.md` | `atlas-faq.md` | The FAQ also asks/answers the port question, so it is genuinely similar. |
| "What was the p95 latency in March 2026?" | `atlas-service-metrics.csv` | `atlas-handbook.md` | Dense embeddings are weak at exact numeric/table lookup. |

Hybrid placed the correct document second once:

| Query | Relevant | Top result | Cause |
|-------|----------|------------|-------|
| "Which formats were added in release 2.2.0?" | `atlas-release-notes.md` | `atlas-security.md` | Both contain format/dependency vocabulary; one FTS rank was enough to outvote the other list. |

## What this does and does not prove

**Proves:**

- The end-to-end pipeline (parse → chunk → FTS → embeddings → search) works.
- Query escaping and the natural-language AND→OR fallback retrieve the right
  document for question-style queries.
- RRF fusion is wired correctly and is stable: it never loses the correct document
  from the top five, even when one retriever ranks it lower.
- Full-text search is fast on a small local corpus.

**Does not prove:**

- Real-world quality. Seven synthetic documents and twelve queries are far too
  small to generalise. A larger, messier corpus (scanned PDFs, long reports,
  multilingual text) will behave differently.
- Anything about scale. 32 chunks fit in memory; 100,000 will not behave the same.
- That semantic or hybrid is "better". On this corpus, exact-keyword full-text is
  the strongest baseline, which is a useful and honest result. Semantic search
  adds value for paraphrases that keyword search misses; this query set is
  deliberately keyword-friendly because the corpus is small.
- Multilingual quality. `all-MiniLM-L6-v2` is English-centric.

## Improving the benchmark

If you extend the corpus, keep the labels exhaustive and committed alongside the
queries in `scripts/benchmark.py`. Useful additions:

- paraphrased queries with no shared keywords (to reward semantic search);
- multi-document questions that require more than one source;
- negative queries with no answer (to measure false-answer rate of the assistant);
- latency at 1k / 10k / 100k chunks;
- a reranker comparison.

Do not publish numbers from a corpus you have not committed, and do not tune the
query set until the numbers look good. The point of the file is to make regressions
visible.
