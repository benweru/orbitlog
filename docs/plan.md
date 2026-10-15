# OrbitLog v2: Gemma 4 E2B fault diagnosis under a 512 MiB RAM cap
_Plan written 15 Oct 2026, 11:30 AM EAT. Every number below carries its source. Items marked **[est]** are my own arithmetic, and **[verify]** marks items to confirm in week 1._

## 1. The open problem (Satlyt's own words, via third parties)
- Satlyt flew a quantized **Gemma 3 1B** (through llama.cpp) on a Momentus spacecraft. Reported results: diagnostic payloads cut by 64.4% and 64.8% (1,319→469 B and 1,318→464 B) at 22.71 and 25.48 tok/s. The team is working on pruning and distillation, targeting a memory-footprint reduction of more than 90%. https://deepmind.google/models/gemma/gemmaverse/satlyt/
- "As of April, Satlyt was working to upgrade its stack to … **Gemma 4 E2B** … goal of lowering the Gemma 4 E2B's memory usage by more than 90%." https://siliconangle.com/2026/10/01/satellite-software-provider-satlyt-closes-8m-investment/
- Satlyt has **not said what the 90% is measured against.** We pick an explicit baseline (section 3) and say so.

## 2. Verified facts the plan rests on
| Fact | Value | Source |
|---|---|---|
| Gemma 4 E2B parameters | 2.3B effective, 5.1B with embeddings; 35 layers; 262K vocabulary; 512-token sliding window; ~150M vision and ~300M audio encoders | https://huggingface.co/google/gemma-4-E2B-it-qat-q4_0-gguf |
| Per-layer embedding (PLE) table | `embed_tokens_per_layer` is 4.375 GiB bf16 / 1.230 GiB int4; `embed_tokens` is 0.750 GiB bf16. Text-only checkpoint is 6.11 GiB bf16 | https://dev.to/gde/gemma-4-on-a-tesla-t4-part-3-int4-embeddings-serve-e2b-in-286-gib-at-230x-bf16-3kch |
| Google QAT Q4_0 GGUF | 3.35 GB (PPL +8.5% vs bf16 in one third-party test) | https://huggingface.co/roman220220/gemma-4-E2B-it-qat-phone-GGUF |
| Bytes actually read per token | ≈1.19 GB of transformer weights per decode step for a Q4_K_M-class E2B; the PLE lookup is ≈7 KB/token | https://huggingface.co/fraQtl/Gemma-4-E2B-it-Hi-Fi-GGUF |
| PLE can live in flash | It is a static lookup table, so it need not be in DRAM (community explanation) | https://www.reddit.com/r/LocalLLaMA/comments/1sd5utm/perlayer_embeddings_a_simple_explanation_of_the/ |
| llama.cpp weight formats | IQ2_XXS 2.06 bpw, IQ2_XS 2.31, IQ2_M 2.7, IQ1_S 1.56, IQ1_M 1.75, Q2_K; **TQ1_0 1.69 / TQ2_0 2.06 "ternarization"**; Q1_0 1.125 and Q2_0 2.25 also listed | https://github.com/ggml-org/llama.cpp/blob/master/tools/quantize/quantize.cpp and https://github.com/ggml-org/llama.cpp/wiki/Tensor-Encoding-Schemes |
| Ternary caveat | TQ1_0/TQ2_0 were built for natively ternary models (TriLM, BitNet b1.58), so applying them to a normally trained model after the fact is expected to break it | https://github.com/ggml-org/llama.cpp/commit/9bc6db28d011d47a5f318dc4aebbe7927fac4629 |
| Layer pruning | `llama-quantize` has a `prune_layers` option (seen in source) | quantize.cpp above **[verify the CLI flag name]** |
| KV-cache quantization | `--cache-type-k/--cache-type-v` (q8_0, q4_0…); q4_0/q4_0 is 4.75 bits per value vs 16 for f16 | https://github.com/ggml-org/llama.cpp/pull/7527 ; experimental 3.5-bpw TurboQuant KV: https://github.com/ggml-org/llama.cpp/discussions/20969 |
| Distillation target | Gemma 3 270M: 170M embedding + 100M transformer parameters, made for task fine-tuning, QLoRA on a free Colab T4, "under 300MB" after quantization | https://developers.googleblog.com/introducing-gemma-3-270m/ , https://developers.googleblog.com/own-your-ai-fine-tune-gemma-3-270m-for-on-device/ |

## 3. Headline target, baseline and measurement
**Headline:** "Gemma 4 E2B (text-only) diagnoses the correct root cause on **≥80% of 60 held-out spacecraft faults** while capped at **512 MiB of RAM**. That is **91.8% below the 6.11 GiB bf16 text checkpoint**, with no more than 10 points of accuracy lost against the unconstrained Q4_0 baseline."
- **Baseline A (the 90% denominator):** the bf16 text-only checkpoint, 6.11 GiB. 512 MiB / 6,257 MiB = 8.2%, a reduction of **91.8%**. **[est]**
- **Baseline B (the practical one):** Google's QAT Q4_0 GGUF, 3.35 GB, with no cap. Its accuracy is the quality ceiling we measure loss against. The cap is about 84% below it. **[est]**
- **Reference:** Gemma 3 1B Q4 (Satlyt's flown setup, per DeepMind) on the same dataset.
- **Memory measurement:** run each model inside a cgroup v2 (`systemd-run --scope -p MemoryMax=512M -p MemorySwapMax=0 llama-cli …`) and report `memory.peak` **[verify the kernel version on the Pi]**. This counts page cache too. A memory-mapped (mmap'd) PLE table therefore counts only for the pages actually touched, and the kernel has to evict pages to stay under the cap. That is honest: nothing is hidden on disk without the cost being counted. We also report RSS, flash bytes read per token, and tok/s, so the cost of swapping weights in from flash is visible.
- **Accuracy measurement:** the model must output JSON `{root_cause_class, component, evidence_line, action}`. **Correct** means an exact match on `root_cause_class` (one of 15 classes) **and** the right component. A second metric is an action-appropriateness score from an LLM judge, with 20% of the cases checked by hand. We report 95% Wilson confidence intervals; with n=60 they are about ±10 points, so we say that openly.

**Why 80%:** it is a placeholder. Week 2 measures Baseline B, and the target is then fixed at (Baseline B − 10 points) **before** any compression runs. It is published in the repo's PREREGISTRATION.md with a git timestamp.

## 4. Fault dataset (≥50 train/dev + 60 held-out test)
- **Generator:** run **NASA cFS** (open source, https://github.com/nasa/cFS) in Docker on Linux, plus a Python payload app such as an OpenCV image pipeline, mirroring Satlyt's published scenarios. Inject real faults and capture the real artefacts: cFS event messages (EVS), housekeeping telemetry, syslog/dmesg, stack traces.
- **15 fault classes** (around 8 instances each, varied in parameters): OOM/allocation failure, I2C/sensor NACK (simulated by unbinding the driver or using a fake i2c-stub device), disk full, read-only filesystem, thermal throttling (fake sysfs values), segfault in a C app, Python exception in the payload, corrupt input file, clock jump or NTP drift, a cFS app crash restarted by its health checker, a full software-bus pipe, a table-load validation failure, a watchdog reset, a network/link drop, and a CPU-starvation deadline miss.
- **Labels are ground truth by construction:** the injector writes `{class, component, injected_param, timestamp}` before it triggers the fault, so no human labelling is needed for the class. Ben hand-writes the correct `action` for each class, and a second reviewer (a peer or mentor) checks 20%.
- **Realism controls:** add distractor noise (benign warnings, unrelated events), vary log length (0.5–4 KB), and include 10 "no fault" cases to measure false alarms. The split is by fault *instance seed*, and some test cases use **parameters never seen in training**.
- **Caveat:** these are emulated faults on a ground Linux box, not flight data. They are described that way in the write-up.

## 5. Experiments
**E1. The key result: an accuracy-vs-memory curve.** x-axis: peak memory under the cap (128 MiB to 4 GiB); y-axis: accuracy on the test set. Each point is one configuration from the grid:
1. Q4_0 QAT (ceiling), with mmap on and off.
2. Mixed precision per tensor (`--tensor-type`): attention/MLP at Q4_K→IQ3→IQ2_M→IQ2_XXS, using an importance matrix (imatrix) built from the **training** logs only.
3. PLE handling: Q4_K and memory-mapped from SD/NVMe (only touched rows stay resident), plus token embedding at Q4/Q6.
4. KV cache: f16 → q8_0 → q4_0, with context capped at 2,048 tokens (enough for a 4 KB log) **[est]**.
5. Layer pruning: drop 0, 4, 8 or 12 of the 35 layers, choosing which ones by measuring the change in loss on the training logs.
6. Ternary TQ1_0/TQ2_0 on a few tensors only, **expected to fail**. It is included to show where the floor is.
7. A drop-in replacement: **Gemma 3 270M** fine-tuned (QLoRA) on diagnoses that E2B-Q4 produced and that match the labels (distillation, Q4/Q8). This is the likely winner below 300 MiB.
8. E2B + LoRA fine-tune + IQ2 (to recover accuracy after quantization).
Plot the Pareto frontier. **Back-of-envelope:** the ≈1.19 GB of transformer weights at about 2.1 bpw instead of about 5 bpw comes to roughly 0.5 GB, which is right at the cap **[est]**. So pruning or fine-tuning is probably *required*, and that is what makes the result interesting.

**E2. Beat 64% report compression without losing the diagnosis.**
- Baselines, measured on the same 60 test cases: (a) the raw log bundle, (b) zstd -19 of the raw bundle, (c) Satlyt-style free-text summary (~64%), (d) a rule-based regex extractor.
- Ours: a schema-constrained output (llama.cpp GBNF grammar) holding a class ID, component ID, evidence-line index and action code, packed into a fixed binary frame with CRC (≈16–32 B **[est]**). Optionally the frame also carries a zstd-compressed one-line evidence quote.
- Metric: bytes on the downlink against "diagnostic fidelity", meaning a ground-side decoder (or a blind human reader) recovers the correct class, component and action from the frame alone. Target: **≥95% byte reduction with fidelity ≥ the free-text summary.** We report candidly where zstd alone does almost as well.

**E3 (light).** Latency, tok/s and energy on the Pi (USB power meter) for the 3 Pareto-best configurations.

## 6. Reproducible with one command
`git clone … && make reproduce` (or `docker compose run bench`):
- llama.cpp pinned by commit; models pulled by Hugging Face revision and verified by sha256.
- The dataset regenerated from seeds (and also published as a frozen release), then the full grid, then `results/*.jsonl`, plots and REPORT.md.
- `make quick` runs 3 configs × 10 cases in under 30 minutes on a laptop. GitHub Actions runs `make quick` on every push.
- Hardware and kernel fingerprint logged in every result.

## 7. Public write-up
TL;DR with the curve; the exact baseline definition and why; the dataset design and its limits; the preregistered target and whether it was met; the full Pareto table; failures (ternary, aggressive pruning); the E2 comparison including the zstd baseline; reproduction instructions; what would differ on real flight hardware (radiation, Jetson-class SoC, cFS integration); and links to the dataset on Hugging Face and the code under Apache-2.0. Post it on GitHub plus a blog post, and send the link to Satlyt (outreach drafts still need Ben's approval).

## 8. Week-by-week plan (10–15 h/week, ~12 weeks)
| Week | Work | Deliverable |
|---|---|---|
| 1 | Set up llama.cpp, run E2B Q4_0, build the cgroup memory harness, check the [verify] items | `bench/` harness that measures memory.peak |
| 2 | cFS in Docker, injector for 5 classes, JSON schema | first 40 cases; Baseline B measured; preregistration committed |
| 3–4 | All 15 classes, noise, split; second-reviewer check | dataset v1 (≥110 cases) |
| 5 | Quantization grid (Q4→IQ2, imatrix, KV, PLE mmap) | first curve |
| 6 | Layer-pruning sweep | curve v2 |
| 7–8 | Distillation into 270M + LoRA on E2B (Colab/Kaggle) | fine-tuned GGUFs |
| 9 | E2 (binary frame, GBNF) | compression table |
| 10 | Runs on the Pi, energy measurements | hardware numbers |
| 11 | `make reproduce`, CI, run on a clean machine | reproducible release |
| 12 | Write-up and a 3-minute video | public post |
Buffer: +2 weeks.

## 9. Hardware and costs (approximate; check local prices)
- Laptop he already owns (development and the main grid): KES 0.
- Raspberry Pi 5 (8 GB, so the cap is enforced in software) + NVMe/SD + PSU: about USD 120–150 **[verify the Nairobi price]**.
- USB-C power meter: about USD 15–25.
- GPU for fine-tuning: free Colab T4 / Kaggle (QLoRA on 270M is documented on a free T4, per Google). Budget USD 0–50 for Colab Pro or a rented GPU for the E2B LoRA.
- **Total: about USD 150–250.**

## 10. Risks and fallbacks
| Risk | Fallback |
|---|---|
| E2B can't stay coherent at ≤512 MiB, even pruned | Report the real frontier (e.g. "80% at 768 MiB"). The distilled 270M carries the 512 MiB claim, labelled clearly as distillation, not E2B |
| llama.cpp support for Gemma 4 PLE + mmap behaves unexpectedly under a cgroup | Use `--mlock` off/on variants; report RSS and page cache separately; document it |
| Synthetic faults are too easy (a regex scores 100%) | The regex baseline exposes this; add distractors and cases where several faults look alike; report it honestly |
| The labels share bias with the injector | Hold out unseen parameters and some new log formats |
| Thrashing makes tok/s unusable | Report tok/s; set a usability floor (≥2 tok/s) as part of success |
| Time overrun | Cut E3 and the ternary experiments; keep E1 + E2 |

## 11. Success and failure criteria
- **Full success:** the preregistered accuracy at ≤512 MiB `memory.peak` on held-out faults with E2B-derived weights, ≥2 tok/s on the Pi 5, E2 at ≥95% fewer bytes with no loss of fidelity, and `make reproduce` working on a clean machine.
- **Partial success (still worth publishing):** the target met only by the distilled 270M, or by E2B at 513–1024 MiB, with the full curve published.
- **Failure:** no reproducible curve, or claims that depend on unmeasured memory. Negative results with a clean harness still count as a publishable artefact.

## 12. What is truly novel (candid)
- **Not novel:** the quantization types, KV quantization, mmap, LoRA/distillation and PLE-in-flash. These are all existing techniques, and others have already shrunk E2B to 2.86 GB.
- **Novel, as far as I found:** (1) a public, labelled, cFS/Linux flight-software fault-diagnosis benchmark with ground truth by construction; (2) the first public accuracy-vs-memory frontier for E2B *on this task* under a hard cgroup cap that counts page cache; (3) a structured diagnostic downlink format measured against zstd and free-text summaries. I found no existing work that does (1)–(3), but the search was not exhaustive.
- **Caveat:** this does not prove flight readiness, and it is not Satlyt's dataset. It shows Ben can turn their stated open problem into a rigorous, reproducible experiment.
