# SOP Baseline Code Audit

## Scope

This audit covers `SOPBaselineOperator`, `SOPTerm`,
`benchmarks/archive/legacy_sop_vs_ttno/benchmark_sop_vs_ttno.py`, the junction source pattern in
`../ttns-test/junction_zt_hubbard.py`, and the current TTNS/TTNO interfaces.

## Findings

1. **Symbolic term source**

   The SOP baseline reads existing `renormalizer.model.Op` terms through
   `SOPBaselineOperator.from_symbolic_terms(model_or_terms, tree, basis=None)`.
   It accepts a `Model`, a single `Op`, an `OpSum`, or an iterable of `Op`.
   For junction benchmarks, the term construction follows the symbolic pattern
   in `../ttns-test/junction_zt_hubbard.py`: lead hopping terms explicitly include the
   fermionic `Z` strings in the `Op` list, and phonon terms are ordinary local
   `x`, `p^2`, and `x^2` terms.

2. **SOP term representation**

   Each `SOPTerm` stores a scalar `coeff` and a mapping from `BasisTree` node
   index to a local symbolic `Op`.  Missing nodes are identities.  The mapping is
   built once by splitting the existing symbolic operator with
   `Op.split_elementary`, so the baseline reuses the existing fermionic/parity
   convention instead of inventing a Jordan-Wigner rule.

3. **Identity handling**

   Identity local operators are skipped when constructing `SOPTerm.local_ops`.
   An identity-only product term is applied as a scalar multiplication of the
   TTNS.  Identity sites are therefore not visited with explicit local matrix
   multiplication.

4. **Local operator matrix caching**

   `SOPBaselineOperator` caches local matrix factors per `(node_idx,
   op.to_tuple())`.  This cache is local to the SOP baseline object.  It does
   not combine different SOP terms into shared TTNO paths or do subtree
   compression.

5. **Apply path**

   The initial implementation applied each SOP product term by constructing a
   one-term `TTNO` and calling `TTNO.apply`.  That put symbolic TTNO
   construction inside the SOP apply timing and was not a fair ML-MCTDH-style
   flat SOP baseline.

   The current implementation applies each product term directly to the TTNS
   tensors by multiplying the relevant local operator matrices into physical
   axes, shifting node quantum-number metadata by the product term's subtree
   quantum number, and summing term results as TTNS objects.

6. **Large intermediate objects**

   `apply_to_ttns(psi)` still creates one TTNS contribution per term and adds it
   to the accumulated result.  This is intentional for a flat SOP baseline: each
   product term contributes independently.  It no longer constructs a TTNO,
   tree, basis, or dense global matrix for each term.

7. **TTNO vs SOP fairness**

   Benchmark points construct `SOPBaselineOperator` and `TTNO` from the same
   symbolic `Op` list, use the same `BasisTree`, and apply both operators to the
   same `TTNS` state.  The dense correctness comparisons use the same physical
   basis order, skipping dummy tree nodes.

8. **Construction vs apply timing**

   The earlier benchmark script reported single build/apply timings but did not
   use warm-up or repeat medians.  The benchmark has been updated to report
   construction, apply, and expectation medians separately.

9. **Warm-up and repeat timing**

   The updated benchmark warms up apply and expectation calls before timing and
   records repeat medians.  File I/O happens only after all measurements for a
   benchmark point.

10. **Why the initial `n_lead=1, n_phonon=1` SOP timing was slow**

    The initial SOP apply timing included one-term TTNO construction and TTNO
    apply for every SOP product term.  Even a tiny model paid repeated symbolic
    MPO/TTNO table construction, local operator tensor assembly, and TTNS
    metadata allocation costs.  That made the baseline a measurement of
    repeated TTNO construction rather than a fair flat SOP product-action
    baseline.

## Remaining Caveats

The baseline remains intentionally uncompressed across terms.  It may cache
local matrix factors, but it does not share subtrees, identity strings, or common
operator paths across different SOP terms.  That is the intended contrast with
TTNO.

Expectation values are computed as an overlap after applying the SOP operator.
This keeps the operator representation flat, but it may allocate a larger TTNS
intermediate for many terms.  That is representative of straightforward
term-by-term action, not an optimized ML-MCTDH mean-field implementation.
