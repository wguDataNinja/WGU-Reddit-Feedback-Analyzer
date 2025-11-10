
Methods — Deviation from HITL-CGT

This project builds on the Human-in-the-Loop Computational Grounded Theory (HITL-CGT) framework introduced by Alqazlan et al. (2025), which integrates statistical topic modeling (LDA, QDTM) with iterative human coding to scale grounded theory for large social datasets. While the original framework was validated on corpora of thousands of documents, our application targets per-course corpora in WGU-related Reddit discussions where pain point counts range from 0–50 posts (with many courses producing fewer than 20). This scale mismatch necessitated methodological changes to maintain topic stability and maximize usable data by course.

First, statistical topic modeling methods were replaced with LLM-based extraction and clustering. Sparse co-occurrence matrices in LDA and unreliable document frequency statistics in TF-IDF lead to unstable topics when applied to datasets as small as “a few dozen” documents (Gasparetto et al., 2022). In our N = 0–50 context, this instability is expected to be severe. By contrast, van Wanrooij et al. (2024) demonstrate that generative LLMs produce coherent, interpretable topics even with as few as 5–10 documents, consistently outperforming LDA and BERTopic in the 5–50 document range. This evidence directly supports substituting LLM-based topic modeling for statistical approaches in our adaptation.

Second, sentiment analysis was integrated earlier in the pipeline using VADER, a lexicon-based tool specifically tuned for social media language. VADER’s handling of informal syntax, emojis, and emphasis cues makes it well-suited for detecting negative sentiment associated with pain points in Reddit posts, which often contain informal and expressive markers of frustration or confusion. This targeted filtering increases the likelihood that extracted content reflects genuine pain points rather than neutral discussion.

Finally, course-code detection includes a ==1 filter, limiting analysis to posts tagged with exactly one official, current WGU course code from the June 2025 Institutional Catalog. This reduces noise from multi-course complaints, deprecated courses (if course-name matched) and prevents conflating unrelated pain points into the same cluster, simplifying downstream clustering and improving interpretability in per-course “Survival Guides.”

In summary, the adaptation retains HITL-CGT’s core strengths—iterative coding, constant comparison, and human validation—while replacing statistical topic models with LLMs to preserve coherence in very small corpora, employing VADER sentiment analysis to improve pain point identification in social media data, and applying strict course-code filtering to maintain cluster specificity.

⸻

Here’s the updated Stage 1 – Pain Point Extraction methodology, now aligned with van Wanrooij et al. (2024)’s small-data topic modeling approach:

⸻

Stage 1 – Pain Point Extraction
Starting from the 866 Reddit posts retained after Stage 01 filtering (course‐code match and VADER compound sentiment ≤ –0.2), we applied an LLM‐based extraction procedure adapted from van Wanrooij et al. (2024)’s candidate creation method. Each post was processed individually by a generative LLM with a strict JSON prompt to return one to three pain point candidates.

For this study, a pain point was defined as a negative, course‐related experience tied to a fixable aspect of course design, delivery, or support. For each candidate, the LLM produced: (1) a short label summarizing the problem (5–12 words, neither over‐general nor over‐specific), (2) a brief quoted snippet from the post illustrating the issue, and (3) a concise root‐cause phrase. Posts without course‐related complaints returned an empty list.

This step intentionally followed van Wanrooij’s separation of candidate creation from reduction and assignment: no merging of similar pain points was performed here. The output was validated for JSON compliance and schema integrity, ensuring deterministic pain_point_id assignment. These raw, post‐level candidates form the input to Stage 2, where similar pain points are merged into per‐course clusters for analysis and human‐in‐the‐loop review.

⸻




