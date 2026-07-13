# Root One-Site Legacy Results

Included adaptive benchmark jobs:

```text
114110 114116 114119 114123 114126 114311 114312 114313
```

These runs measure `quantity=local_effective_1site_apply` at the TTNS root.
For that timing object, naive SOP work is
`n_sop_terms * n_tree`, so an approximately quadratic exponent is expected.
The results must not be used to test the all-node `N^3/N^2/N` hierarchy.

Job 114126 is the large run documented in
`llmdoc/memory/decisions/2026-07-09-operator-env-large-benchmark.md`. Job
114313 repeats that root-only experiment with the later four-method labels.

