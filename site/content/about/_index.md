---
title: "About"
---

## Overview

This site accompanies the **WGU-Reddit Analyzer**, a capstone project that examines whether large language models can be used to organize unstructured student discussion in a reproducible and inspectable way.

Students frequently discuss course difficulties informally and anonymously in public spaces such as Reddit. This text is noisy, inconsistent, and difficult to analyze using traditional rule-based methods. Recent research shows that large language models can be used to extract and organize recurring themes from Reddit discussions using staged, schema-driven pipelines (Rao et al., 2025). <a href="https://arxiv.org/abs/2405.05345" target="_blank" rel="noopener">Link to paper</a>

This project uses Reddit posts about WGU courses as a test case to evaluate whether recurring course-level student difficulties can be surfaced reliably using an artifact-based LLM pipeline.

## Pipeline overview

A multi-stage LLM pipeline processes a fixed snapshot of Reddit posts. Posts describing student-reported difficulties (pain points) are identified, grouped within courses, aligned across courses, and summarized into precomputed counts and supporting excerpts. These outputs are then published to a static, read-only website.

<img src="/img/pipeline-overview.png" alt="Pipeline overview" style="width:100%;max-width:1200px;" />
<p><em>High-level pipeline used to produce the published snapshot.</em></p>

The website itself performs no analysis and runs no models. It exists solely to present the frozen outputs of the pipeline in a transparent and inspectable form.
