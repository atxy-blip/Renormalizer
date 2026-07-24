# Contraction Scaling Figures Design

## Goal

Turn the completed 144-task contraction diagnostic into figures that separate
nominal tensor-contraction complexity from observed wall time and explain the
paired-versus-contracted primitive-basis trend.

## Inputs and statistical contract

The plotter reads only
`benchmarks/results/operator_env_scaling/contraction_diagnostics/aggregate/summary.csv`.
Every plotted point is the median of three independent Slurm tasks; the shaded
band is median plus or minus one sample standard deviation, clipped to positive
values on logarithmic axes.  Scaling exponents are ordinary least-squares fits
in log--log coordinates.  The reported asymptotic exponent uses the largest
four parameter values.  No raw snapshot or aggregate table is modified.

## Outputs

The output directory is
`benchmarks/results/operator_env_scaling/contraction_diagnostics/figures/`.
The plotter writes:

- `complexity_validation.pdf` and `complexity_validation.png`;
- `model_mechanism.pdf` and `model_mechanism.png`;
- `plot_fits.csv`, containing every exponent displayed in the figures.

## Figure 1: complexity validation

A 2-by-2 figure separates optimized FLOPs from wall time:

1. SOP and TTNO internal-node optimized FLOPs versus state bond dimension.
2. SOP and TTNO internal-node dense-kernel apply time versus state bond dimension.
3. Paired and primitive-contracted leaf optimized FLOPs versus primitive basis dimension.
4. Paired and primitive-contracted leaf dense-kernel apply time versus primitive basis dimension.

The FLOP panels include anchored theoretical guides for `M_s^4`, `d^4`, and
`d^2`.  Legends report the largest-four-point exponent.  The wall-time panels
do not relabel measured exponents as mathematical complexity.

## Figure 2: full-model mechanism

A second 2-by-2 figure explains the real Hubbard-junction result:

1. Total TTNO local-effective-action workflow time for paired and contracted trees.
2. Paired-tree operator construction, environment construction, and apply times.
3. TTNO and TTNS tensor element counts for both tree layouts.
4. Peak resident memory for both layouts.

These panels expose the causal chain: pairing two primitive modes on one leaf
creates an operator tensor with four physical axes, so its elements, memory,
construction, environment contraction, and application become fourth order in
`d`.  Primitive contraction puts one mode on each leaf and leaves two physical
operator axes, giving asymptotic second-order operator storage.  The contracted
whole-model wall time may remain nearly constant over the tested range because
fixed internal-node work dominates its inexpensive leaf contractions.

## Validation

Automated tests cover numeric sorting, tail-fit selection, exact recovery of a
synthetic fourth-order law, and generation of all declared artifacts from a
small synthetic summary.  Final verification runs the plotter on the complete
aggregate, checks that every output is non-empty, and visually inspects both
PNG files.
