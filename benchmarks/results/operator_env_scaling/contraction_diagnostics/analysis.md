# Contraction-scaling diagnostic analysis

## Data status and fitting convention

The diagnostic contains all 144 requested snapshots: six controls, eight
parameter values, and three independent repeats.  Every snapshot has
`status=ok`; `aggregate/missing_task_ids.json` is empty.  Plotted points use
the repeat median and sample standard deviation.  `alpha_tail` is the log--log
fit over the largest four parameter values.

## Exact operation and storage formulas

The shape-only optimized FLOP counts match the following formulas at every
sampled point (maximum absolute discrepancy zero).  `opt_einsum` counts a
multiply and an addition as two FLOPs.

For an internal node with state bond `M` and fixed TTNO bond `O=4`,

```text
SOP internal:   F(M) = 6 M^4
TTNO internal:  F(M) = 48 M^4 + 128 M^2
```

For a leaf with fixed `M=20` and `O=4`,

```text
paired leaf:     F(d) = 160 d^4 + 3200 d^2
contracted leaf: F(d) = 160 d^2 + 3200 d
```

The full Hubbard-junction TTNO storage is exactly

```text
paired tree:     N_TTNO(d) = 32 d^4 + 1354
contracted tree: N_TTNO(d) = 48 d^2 + 1642
```

The paired tree has eight phonon leaves, each containing two primitive modes.
Its state leaf has shape `(M,d,d)` and its operator leaf has shape
`(O,d,d,d,d)`.  The contracted tree has sixteen one-mode leaves with shapes
`(M,d)` and `(O,d,d)`.  The number of physical operator axes therefore changes
from four to two.

## State-bond trend

| Kernel | Optimized-FLOP alpha | Wall-time alpha | Tail FLOP alpha | Tail wall-time alpha |
| --- | ---: | ---: | ---: | ---: |
| SOP internal | 4.000 | 2.899 | 4.000 | 3.634 |
| TTNO internal | 3.993 | 3.175 | 4.000 | 3.811 |

The mathematical contraction is fourth order.  The approximately cubic
all-range wall-time fit is a finite-size performance effect.  Small tensors
spend a larger fraction of time in dispatch, expression calls, and poorly
utilized BLAS kernels.  Effective arithmetic throughput increases with `M`, so
wall time grows more slowly than the operation count.  Over the tail, SOP
throughput rises from about 24 to 37 GFLOP/s between `M=70` and `M=220`; TTNO
throughput rises from about 31 to 39 GFLOP/s.  This removes roughly 0.37 and
0.19, respectively, from the apparent time exponent.  As the fixed overhead
shrinks, both measured exponents move toward four.

The complete all-node Tree timing additionally sums leaves and internal nodes
with different actual dimensions and lower-order work.  Consequently its
finite-range wall-time exponent can remain nearer three even though a
full-rank internal-node contraction has fourth-order FLOP complexity.  The
current result distinguishes an effective measured exponent from an
asymptotic tensor-index count; it does not justify replacing the latter by
`M^3`.

## Primitive-basis trend

| Quantity | All-point alpha | Tail alpha |
| --- | ---: | ---: |
| Paired-leaf optimized FLOPs | 3.829 | 3.989 |
| Contracted-leaf optimized FLOPs | 1.524 | 1.758 |
| Paired full-model total time | 2.184 | 4.019 |
| Contracted full-model total time | 0.034 | 0.050 |
| Paired full-model TTNO elements | 3.983 | 4.000 |
| Contracted full-model TTNO elements | 1.745 | 1.981 |

The paired result reaches fourth order because `d^2` is the local Hilbert
dimension of a two-mode leaf.  A dense operator maps this product space to
itself and therefore has `d^2 * d^2 = d^4` entries.  At `d=100` the model TTNO
contains 3,200,001,354 elements.  With double precision this is 25.6 GB of raw
operator data; measured peak resident memory is about 27.7 GB.

The same fourth-order object is processed in all expensive paired-tree stages:

| Paired-tree stage | Tail alpha |
| --- | ---: |
| TTNO construction | 4.096 |
| Environment construction | 3.769 |
| Local actions | 4.176 |
| Total | 4.019 |

For `d=40,50,70,100`, total paired-tree time is approximately
`1.58, 4.08, 16.41, 62.40` seconds.  This agreement across storage,
construction, environment, application, memory, and total time identifies the
four-physical-axis leaf tensor as the cause; the trend is not an artifact of
including TTNO construction in one timer.

Primitive contraction changes each leaf operator to a two-axis `d by d`
matrix.  Its optimized cost contains both a linear and a quadratic term,

```text
F(d) = 160 d (d + 20).
```

Thus the tested range has not fully removed the linear contribution: even at
`d=100`, it is one sixth of the total.  This explains the tail FLOP exponent
1.758, while direct TTNO storage, whose lower-order constant is smaller,
already gives 1.981.

The contracted whole-model time stays near `0.16--0.17` seconds because the
new `d^2` leaf work remains below the fixed electronic and internal-tree work.
Its nearly zero fitted total-time exponent therefore does not mean that the
leaf is `O(1)`; the isolated FLOP count and TTNO storage show the expected
approach to `d^2`.

## Interpretation relative to the reference result

The paper's `d^2` behavior corresponds to a representation where a primitive
mode contributes one input and one output physical index.  The repository's
default paired phonon leaves instead combine two modes before forming the
dense TTNO tensor, producing four physical indices and `d^4` storage.  Enabling
primitive contraction restores the one-mode leaf structure and its asymptotic
`d^2` operator scaling.

Likewise, the paper's quoted bond-dimension wall-time exponent and the current
all-node Tree benchmark are different timing objects.  The controlled kernel
shows that the repository's full-rank internal contraction has `M^4` FLOPs;
the observed near-cubic wall time over the available range comes from changing
hardware efficiency, fixed/lower-order work, and aggregation over nonuniform
tree nodes.
