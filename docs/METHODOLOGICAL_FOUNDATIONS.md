# Methodological Foundations

This project is informed by three published works that address complementary aspects of using large language models to analyze noisy, large-scale social media data. Each paper influenced specific design decisions in the WGU Reddit Analyzer. None are treated as blueprints, and no claim of full replication is made.

What follows describes, for each source:
- what the paper contributes,
- why it is relevant to this project,
- how its ideas are applied,
- and where the project intentionally diverges.

---

## You et al. (2025): LLM-as-Classifier Framework

### What the paper does

You et al. present a framework for using large language models as classifiers without fine-tuning. The paper emphasizes:
- explicit and stable label schemas,
- frozen benchmark datasets,
- prompt-as-classifier artifacts,
- iterative prompt refinement,
- and controlled evaluation using paired statistical tests (for example, McNemar’s test).

Prompt changes are framed as methodological changes that should be justified empirically on held-out labeled data.

---

### Why it is relevant

Stage 1 of this project is a classification task: determining whether a Reddit post contains a fixable, course-side pain point. The problem matches the paper’s core use case:
- short, noisy text,
- semantic judgment rather than keyword matching,
- and a need for reproducible and auditable prompt iteration.

---

### How it is applied

This project adopts core principles from the paper’s classification discipline:
- an explicit schema (`y / n / u`) with normalization rules,
- frozen DEV and TEST splits with human-labeled gold data,
- prompt snapshots stored with each run,
- reproducible artifacts and run manifests,
- iterative refinement informed by error analysis,
- paired evaluation of prompt variants on identical examples,
- and statistical testing used to guide prompt selection and identify regressions.

These practices inform how prompt variants are compared and selected, rather than enforcing mechanical acceptance rules.

---

### Limits of alignment

The project does not implement all diagnostics discussed in the paper, such as:
- sequence invariance testing,
- adversarial prompt injection defenses,
- or post-deployment drift monitoring.

These components fall outside the scope of this work. The implementation adopts core principles rather than claiming completeness with respect to the paper’s full methodology.

---

## Rao et al. (2025): QuaLLM

### What the paper does

Rao et al. introduce QuaLLM, a multi-stage framework for extracting, aggregating, and organizing themes from large-scale Reddit data using LLMs. The framework draws inspiration from qualitative research practices and emphasizes:
- structured extraction,
- aggregation across many posts,
- and consistency through scale.

Human involvement is assumed for schema definition, evaluation, and interpretation.

---

### Why it is relevant

The WGU Reddit Analyzer processes thousands of Reddit posts distributed across dozens of subreddits. The core challenge is not individual post interpretation, but organizing dispersed discussion into stable, analyzable structures.

---

### How it is applied

The overall pipeline structure reflects QuaLLM’s staged approach:
- extraction of structured records from individual posts,
- aggregation within bounded contexts (courses),
- normalization into shared issue categories across contexts,
- and reliance on scale and aggregation to reduce sensitivity to individual errors.

Stages 2 and 3 align conceptually with QuaLLM’s aggregation and normalization steps, adapted to course-level and cross-course analysis.

---

### Limits of alignment

There are important differences:
- runtime inference is fully automated, with no human-in-the-loop decision making,
- human involvement occurs in labeling, schema design, and interpretation, not during inference,
- outputs are treated as authoritative artifacts derived from pinned runs, not as exploratory qualitative hypotheses.

The pipeline adopts a similar structure but prioritizes determinism, reproducibility, and artifact authority.

---

## De Santis et al. (2025): Classification of Noisy Social Media Text

### What the paper does

De Santis et al. compare traditional NLP methods, transformer-based models, and LLM-based approaches on short, informal social media posts. The paper shows that:
- bag-of-words methods perform poorly on noisy social text,
- contextual models perform better with minimal preprocessing,
- and F1-based metrics are critical under class imbalance.

---

### Why it is relevant

Reddit posts about WGU courses share the same properties:
- informal language,
- implicit complaints,
- ambiguity,
- and meaningful class imbalance.

The project faces the same modeling and evaluation challenges described in the paper.

---

### How it is applied

The paper supports:
- the choice to use LLM-based classification rather than classical NLP baselines,
- minimal preprocessing for LLM inputs,
- and emphasis on precision, recall, and F1 rather than accuracy alone.

Its role here is methodological justification rather than direct replication or validation.

---

## Summary

Each source informs a different layer of the project:
- You et al. guide how classification is defined, evaluated, and refined.
- Rao et al. motivate a staged pipeline for large-scale Reddit analysis.
- De Santis et al. support the use of LLMs and F1-based evaluation on noisy social text.

These ideas are applied selectively and transparently, adapted to the goals of a reproducible, artifact-driven research pipeline.