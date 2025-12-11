## runXX_fixed25_20251119

| model | provider | split | prompt | num_examples | tp | fp | fn | tn | precision | recall | f1 | accuracy | run_dir |
|-------|----------|-------|--------|--------------|----|----|----|----|-----------|--------|----|----------|---------|
| gpt-5-mini | openai | DEV | s1_zero.txt | 25 | 7 | 15 | 0 | 3 | 0.318 | 1.000 | 0.483 | 0.400 | artifacts/benchmark/runs/stage1_/gpt-5-mini_DEV_20251119_052705 |
| gpt-5-mini | openai | DEV | s1_few.txt | 25 | 6 | 9 | 1 | 9 | 0.400 | 0.857 | 0.545 | 0.600 | artifacts/benchmark/runs/stage1_/gpt-5-mini_DEV_20251119_054333 |
| gpt-5-nano | openai | DEV | s1_zero.txt | 25 | 7 | 14 | 0 | 4 | 0.333 | 1.000 | 0.500 | 0.440 | artifacts/benchmark/runs/stage1_/gpt-5-nano_DEV_20251119_053145 |
| gpt-5-nano | openai | DEV | s1_few.txt | 25 | 7 | 12 | 0 | 6 | 0.368 | 1.000 | 0.538 | 0.520 | artifacts/benchmark/runs/stage1_/gpt-5-nano_DEV_20251119_054637 |
| gpt-5 | openai | DEV | s1_zero.txt | 25 | 6 | 5 | 1 | 13 | 0.545 | 0.857 | 0.667 | 0.760 | artifacts/benchmark/runs/stage1_/gpt-5_DEV_20251119_052210 |
| gpt-5 | openai | DEV | s1_few.txt | 25 | 6 | 1 | 1 | 17 | 0.857 | 0.857 | 0.857 | 0.920 | artifacts/benchmark/runs/stage1_/gpt-5_DEV_20251119_053836 |
| llama3 | ollama | DEV | s1_zero.txt | 25 | 7 | 8 | 0 | 10 | 0.467 | 1.000 | 0.636 | 0.680 | artifacts/benchmark/runs/stage1_/llama3_DEV_20251119_053712 |
| llama3 | ollama | DEV | s1_few.txt | 25 | 6 | 3 | 1 | 15 | 0.667 | 0.857 | 0.750 | 0.840 | artifacts/benchmark/runs/stage1_/llama3_DEV_20251119_055247 |

