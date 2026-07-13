# SOP vs TTNO Summary

Junction benchmark source pattern: `../ttns-test/junction_zt_hubbard.py`.

The SOP baseline represents an ML-MCTDH-style operator layer: the symbolic Hamiltonian remains a flat sum of product terms and each product term is applied independently on the same TTNS tree and local basis. It is not a full ML-MCTDH propagator.

TTNO can be more efficient because the operator is also represented as a tree tensor network. Shared identity strings, common subtrees, and repeated bridge/lead/phonon structure can be reused through operator bonds instead of being visited once per flattened SOP term.

Small systems may favor SOP because TTNO construction and contraction overheads are visible. Interpret the table as scaling and crossover data, not as a universal speed claim.

The lead and phonon cases isolate basis-size growth in the Hubbard junction construction. The shared-structure case isolates operator-count growth with an artificial low-rank product-operator family.

| case | n_lead | n_phonon | terms | ttno max bond | sop apply (s) | ttno apply (s) | speedup | rel err | status |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| shared-structure | 0 | 0 | 256 | 16 | 54.7579 | 0.00408343 | 1.34e+04 | 4.467e-09 | ok |
