# Legacy SOP vs TTNO Benchmark

This directory preserves the first full-state SOP-vs-TTNO benchmark workflow.
It predates the strict all-node local-effective-Hamiltonian comparison.

The archived scripts measure full-state operator application, current-operator
equivalence, synthetic shared structure, and the original Slurm array. They do
not implement or benchmark the strict MCTDH-like directed-edge environment.

The regression test
`renormalizer/tn/tests/test_sop_vs_ttno_equivalence.py` still imports the
archived junction builder because that builder also returns current-operator
terms. The active adaptive builder intentionally has a different three-value
return contract and is not a drop-in replacement.

Historical CSV, figures, notebook, summaries, point outputs, and Slurm logs are
stored under:

```text
benchmarks/results/operator_env_scaling/archive/legacy_sop_vs_ttno/
```
