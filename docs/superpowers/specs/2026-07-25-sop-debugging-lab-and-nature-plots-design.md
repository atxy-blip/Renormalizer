# SOP Debugging Lab and Nature Plot Refactor Design

## Goal

Produce two connected deliverables:

1. an executable Jupyter notebook that lets the user learn the current SOP
   implementation by answering concrete debugger-driven questions; and
2. a consistent Nature-style refactor of all three current publication figure
   groups without changing the underlying benchmark data, fit definitions, or
   scientific claims.

The learning material must support a complete oral explanation to a supervisor:
what changed, why each change was needed, what object or contraction it
introduced, and what effect the completed experiments measured.

## Scientific Boundary

The formal comparison measures
`local_effective_1site_apply_all_nodes`: the collection of one-site local
effective-Hamiltonian actions across all active tree nodes. It does not measure
a complete TDVP propagation step.

The three publication paths are:

- `sop_no_env`: flat SOP terms without a sweep-level environment;
- `sop_mctdh_like_state_env`: strict per-term, directed-edge state messages
  reused across active nodes, without cross-term operator sharing;
- `ttno_with_env`: a compressed TTNO representation with operator-bond-aware
  TTN environments.

`sop_env_plus_operator_cache` remains an explanatory intermediate path. It is
useful in the notebook for showing operator-signature reuse, but it is excluded
from the formal three-method figures because it is not the strict flat-SOP
baseline.

## Guided Notebook

Create `notebooks/sop_debugging_lab.ipynb`. It must run on a deterministic,
small Li.W.2024 spin--boson case and must not require Slurm or a production-size
calculation.

Every investigation uses the same structure:

1. a question in the form a supervisor might ask;
2. the matching mathematical expression;
3. a small executable setup;
4. the exact source function and suggested breakpoint;
5. a short list of variables, shapes, or cache keys to inspect;
6. an answer prompt for the user;
7. an expected observation that allows self-checking;
8. a three-sentence oral explanation.

The notebook contains the following investigations.

### 1. End-to-End Experiment Map

Trace the path from symbolic Hamiltonian terms through TTNS construction, SOP
or TTNO representation, local-action timing, per-task NPZ snapshots, aggregate
CSV files, power-law fitting, and final figures.

### 2. Product-Term Representation

Relate an `Op` and an `SOPTerm` to

\[
H = \sum_l c_l \prod_\kappa h_l^{(\kappa)}.
\]

Inspect the coefficient, degrees of freedom, symbolic operators, number of
terms, and number of nontrivial local operators.

### 3. Splitting a Product Term Across Tree Nodes

Step through `Op.split_elementary()` and `SOPTerm.from_op()`. Record the
mapping from physical degrees of freedom to basis/tree nodes and identify
identity versus nontrivial nodes for one term.

### 4. Symbolic Local Operators to Matrices

Step through `BasisSet.op_mat()`. Inspect the local basis dimension, matrix
shape, dtype, identity matrix, and one nontrivial spin or boson operator.

### 5. No-Environment SOP Application

Step through `SOPBaselineOperator._apply_term_to_ttns()` and the no-environment
term loop. Observe state copies, node-local actions, term coefficients, and the
final sum. Connect the repeated full-tree work to the no-environment baseline.

### 6. Strict MCTDH-Like Directed-Edge Messages

Inspect `SOPMCTDHSweepEnvironment` using

\[
E_{l,u\rightarrow v}
=
\operatorname{contract}
\left(
\text{bra subtree},
\{h_l^{(x)}\},
\text{ket subtree}
\right).
\]

Observe cache keys of the form `(source, target, term_index)`, both directions
of a tree edge, cache cardinality, and reuse of messages when the active node
changes.

### 7. Strict Term Cache Versus Operator-Signature Cache

Construct terms with a repeated branch operator and compare term-index and
operator-signature cache keys. The exercise must make cross-term sharing
directly visible and explain why that optimized path is not the strict
MCTDH-like comparison baseline.

### 8. TTNO Compression and Environment

Inspect the TTNO maximum operator bond, a numeric TTNO node tensor, and a TTN
environment tensor. Relate the operator-bond axis to sharing repeated operator
structure across symbolic product terms.

### 9. Numerical Identity and Timing Identity

Run all three formal paths on one small case, compare local actions and relative
errors, and inspect environment-build, term-loop, apply, and total timing
fields. Explicitly distinguish the measured all-node local action from full
TDVP propagation and from full-state `H|psi>`.

### 10. Reproducing a Formal Data Point

Follow one row through the manifest, point runner, atomic NPZ snapshot,
finalizer, summary/fits CSV, and plotter. Interpret what changing `N_b`, `M_s`,
and `d` changes in the model and contraction.

The final notebook section contains:

- a formula-to-code-object lookup table;
- a modification / motivation / observed-effect table;
- a supervisor-facing oral recap;
- common interpretation mistakes;
- blank answer cells for the user to complete after running the exercises.

The observed results included in the recap are the completed formal results:

- mode-count tail exponents approximately `3.109`, `2.035`, and `0.916` for
  no-environment SOP, strict state-environment SOP, and TTNO respectively;
- full-workflow state-bond tail exponents near `2.18`, `2.243`, and `2.223`,
  while the isolated full-rank internal contraction has `M_s^4` FLOPs;
- near-constant large-`d` formal timings after adaptive primitive contraction,
  while isolated paired and contracted leaves expose `d^4` and `d^2`
  mathematical/storage behavior.

## Shared Nature Plot Style

Create `benchmarks/nature_plot_style.py` and use it from:

- `benchmarks/plot_li2024_operator_scaling.py`;
- `benchmarks/plot_contraction_scaling_diagnostics.py`;
- `benchmarks/plot_operator_env_scaling.py`.

The shared style uses:

- sans-serif fonts with Arial, Helvetica, then DejaVu Sans fallback;
- PDF/PS font type 42;
- 8 pt base, axis-label, and tick text;
- 7 pt legends and 9 pt panel titles;
- 0.8 pt axes and tick widths;
- 1.2 pt data lines and 4--4.5 pt markers;
- inward ticks, with top and right ticks enabled;
- fixed margins and explicit panel spacing;
- transparent PDF export without `bbox_inches="tight"`;
- 300 dpi PNG previews.

The formal method encoding is:

- blue `#00529B`, filled circle: SOP without environment;
- red `#CC0000`, open circle: strict SOP state environment;
- green `#007A33`, filled square: TTNO with environment.

Color is never the only method encoding. Measured data use solid lines;
theoretical scaling guides use thin dashed lines. Dense major/minor grids,
framed legends, and figure-level presentation titles are removed. Panel labels
and concise titles carry the hierarchy normally supplied by a manuscript
caption.

## Figure-Specific Layout

### Li.W.2024 Three-Panel Figure

Use a `10.5 x 2.8 in` single-row layout with a shared y-axis. Keep the three
variables `N_b`, `M_s`, and `d`, the measured error bars, and the existing
reference powers. Move guide annotations inward so they remain inside the
fixed export boundary. Use one compact, frameless legend.

### Complexity Validation

Use a `7.0 x 5.4 in` two-by-two layout. Retain all mathematical-cost and
wall-time series and their fit records. Use compact fit notation in legends,
consistent panel labels, and lighter uncertainty bands.

### Model Mechanism

Use a `7.0 x 5.4 in` two-by-two layout. Keep paired versus contracted topology
as the primary color/marker encoding. Distinguish TTNO and TTNS storage with
line style, and keep construction, environment, and local-action decomposition
semantically consistent.

## Compatibility and Outputs

The refactor must not change:

- CSV parsing or summary rows;
- fitting windows or fit values;
- method inclusion/exclusion rules;
- the all-node quantity validation;
- raw NPZ or CSV benchmark results.

Each figure group produces its publication PDF and a PNG preview. Existing
stable output stems are preserved so documentation and downstream references
remain valid.

## Testing and Review

Add tests that verify:

- the shared style contains the required physical sizes, fonts, font embedding,
  tick directions, and line dimensions;
- all three plotters generate nonempty PDF and PNG outputs from fixture or
  existing summary data;
- summary and fit computations are unchanged;
- guide annotations and method legends remain present;
- the notebook is valid notebook JSON, contains all ten investigations, and
  its executable cells run non-interactively with debugger pauses disabled.

Run the focused plot and benchmark tests in the documented `reno-3.9`
environment. Render every regenerated PDF to a raster preview and visually
inspect text size, clipping, legend placement, line distinguishability, and
panel balance before declaring the work complete.

## Documentation

Add an llmdoc guide for the debugging lab and a plotting-style reference for
this repository. Link both from `llmdoc/index.md` and record the notebook,
shared style module, refactored plotters, output locations, execution command,
and scientific interpretation boundary.
