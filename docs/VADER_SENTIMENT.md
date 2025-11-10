# VADER Sentiment Filter

_Last updated: 2025-11-07_

## Purpose

VADER (Valence Aware Dictionary and sEntiment Reasoner) is used in this project **only as a filtering tool** — not as a primary analytical model.  
Its role is to isolate **pain point posts** (negative sentiment) before applying the LLM extraction and clustering stages.

This ensures the Large Language Models receive only posts that are likely to describe frustration, confusion, or difficulty — rather than neutral or positive discussion.

---

## Threshold Selection

The sentiment threshold was empirically determined by iterative testing:

- **Threshold used:** `compound < -0.2`
- **Goal:** Exclude neutral or off-topic posts while retaining authentic “struggle” narratives.
- **Validation method:** manual review of a stratified sample (short, medium, long posts) across sentiment ranges.

This process produced a clean cutoff where:
- Most clearly negative posts (complaints, confusion) were retained.
- Neutral or mixed posts (e.g., “Just finished D335!”) were excluded.

---

## Validation Approach

The threshold selection was guided by a small evaluation study performed in Jupyter Notebook.

### 1. Build Evaluation Sample
- Stratified by post length and sentiment bucket:
  - **Short:** <50 chars  
  - **Medium:** 50–250 chars  
  - **Long:** >250 chars  
  - **Sentiment buckets:** very negative (< −0.5), neutral (−0.5 to 0.5), very positive (> 0.5)
- Ensured coverage of edge cases (e.g., posts with code snippets or links).

### 2. Manual Review
- Approximately 100 posts were manually labeled for sentiment correctness:
  - True Positive (correctly negative)
  - False Positive (neutral but flagged negative)
  - True Negative (correctly excluded)
  - False Negative (negative but missed)
- Notes were kept on common misclassifications (e.g., posts containing code blocks or sarcasm).

### 3. Preprocessing Adjustment
- Code blocks, URLs, and Markdown artifacts were stripped before re-evaluating with VADER.
- This significantly improved classification of borderline-neutral posts.

### 4. Decision Criteria
- Post-cleanup accuracy exceeded ~80% for identifying negative vs. non-negative cases.
- The −0.2 threshold was adopted as the final operating point for all subsequent filtering.

---

## Summary

| Purpose | Threshold | Validation | Outcome |
|----------|------------|-------------|----------|
| Isolate negative posts for LLM input | compound < −0.2 | Manual validation on stratified sample | Balanced recall of pain points with minimal neutral noise |

---

## Known Limitation: Programming Courses

Many WGU Reddit posts originate from programming and data courses where students paste **error logs, stack traces, or compiler messages** when asking for help.  
These messages often contain negative language ("error", "failed", "exception") which causes VADER to assign artificially low sentiment scores.

As a result:
- Some **neutral technical questions** are flagged as negative (false positives).
- True pain points embedded in code discussions may be **under- or over-counted** depending on message formatting.

At present, these posts are manually reviewed or filtered during labeling.  
An automated mitigation (e.g., an LLM-based code-text detector) is planned for a future pipeline revision.

---

## Future Considerations

While VADER remains sufficient for pre-filtering, future iterations could evaluate modern sentiment models such as **DistilBERT** or **OpenAI’s `text-sentiment`** endpoint for improved subtlety in mixed-tone posts.

---