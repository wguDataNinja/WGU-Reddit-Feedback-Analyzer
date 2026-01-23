# Methodological Foundations

This project draws on three published works addressing complementary challenges in using large language models to analyze noisy, large-scale social media data. Each source informed specific design choices in the WGU Reddit Analyzer. None are treated as prescriptive templates, and no claim of full replication is made.

For each source, this document explains:
- what the paper contributes,
- why it is relevant here,
- how its ideas are applied,
- and where the project diverges.

---

## You et al. (2025): LLM-as-Classifier Discipline

### Contribution
You et al. describe a disciplined approach to using large language models as classifiers without fine-tuning. Key elements include:
- explicit label schemas,
- frozen benchmark datasets,
- prompt snapshots treated as classifier artifacts,
- iterative prompt refinement,
- and paired statistical testing (e.g., McNemar’s test) to compare prompt variants.

Prompt changes are treated as methodological changes that require empirical justification on held-out labeled data.

---

### Relevance
Stage 1 of this project is a classification task: determining whether a Reddit post contains a fixable, course-side pain point. The setting closely matches the paper’s target use case:
- short, noisy text,
- semantic judgment rather than keyword detection,
- and a need for reproducible, auditable prompt iteration.

---

### Application
This project adopts the paper’s core classification discipline:
- an explicit `y / n / u` label schema with normalization rules,
- frozen DEV and TEST splits with human-labeled gold data,
- prompt snapshots stored with each run,
- reproducible artifacts and run manifests,
- error-driven prompt refinement,
- paired evaluation of prompt variants on identical examples,
- and statistical testing used to guide prompt selection and detect regressions.

These practices guide comparison and selection without acting as mechanical acceptance gates.

---

### Divergence
The project does not implement all diagnostics discussed in the paper, such as sequence invariance testing, adversarial prompt defenses, or post-deployment drift monitoring. These elements fall outside scope. The alignment is conceptual and procedural rather than exhaustive.

---

## Rao et al. (2025): QuaLLM

### Contribution
Rao et al. introduce QuaLLM, a multi-stage framework for extracting and organizing themes from large-scale Reddit data. The approach emphasizes:
- structured extraction,
- aggregation across many posts,
- and stability through scale.

Human involvement is assumed for schema definition, evaluation, and interpretation.

---

### Relevance
The WGU Reddit Analyzer processes thousands of posts across many courses. The primary challenge is not interpreting individual posts, but organizing dispersed discussion into stable, analyzable structures.

---

### Application
The pipeline reflects QuaLLM’s staged structure:
- extraction of structured records from individual posts,
- aggregation within bounded contexts (courses),
- normalization across contexts into shared issue categories,
- and reliance on scale and aggregation to reduce sensitivity to individual errors.

Stages 2 and 3 align conceptually with QuaLLM’s aggregation and normalization steps, adapted to course-level and cross-course analysis.

---

### Divergence
Key differences include:
- fully automated inference with no human-in-the-loop decisions,
- human involvement limited to labeling, schema design, and interpretation,
- outputs treated as deterministic artifacts from pinned runs rather than exploratory qualitative hypotheses.

The pipeline adopts the staged structure while prioritizing determinism and reproducibility.

---

## De Santis et al. (2025): Noisy Social Media Classification

### Contribution
De Santis et al. compare traditional NLP methods, transformer-based models, and LLM-based approaches on short, informal social media text. The study shows that:
- bag-of-words methods perform poorly on noisy text,
- contextual models perform better with minimal preprocessing,
- and F1-based metrics are essential under class imbalance.

---

### Relevance
Reddit posts about WGU courses exhibit the same characteristics:
- informal language,
- implicit complaints,
- ambiguity,
- and meaningful class imbalance.

The evaluation challenges closely match those described in the paper.

---

### Application
This work supports:
- the choice to use LLM-based classification rather than classical NLP baselines,
- minimal preprocessing of inputs,
- and emphasis on precision, recall, and F1 rather than accuracy alone.

Its role is to justify modeling and evaluation choices, not to validate results.

---

## Summary

Each source informs a distinct layer of the project:
- You et al. guide how classification is defined, evaluated, and refined.
- Rao et al. motivate a staged, aggregation-based pipeline for large-scale Reddit analysis.
- De Santis et al. support the use of LLMs and F1-based evaluation on noisy social text.

These ideas are applied selectively and transparently in service of a reproducible, artifact-driven analysis pipeline.