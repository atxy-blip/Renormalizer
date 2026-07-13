# Strict All-Node Development Results

This archive contains:

- job 114333: all-node benchmark before sweep-level strict state-environment
  reuse was implemented; both no-env and nominal state-env paths scaled near
  cubic because environments were rebuilt for every active node;
- job 114334: four-point sanity run validating the corrected strict
  `N^3/N^2/N` trend;
- job 114336 benchmark-native fits and automatic diagnostic PNGs, superseded
  by the publication-specific three-method plotter;
- SOP CPU validation logs from jobs 114059, 114118, and 114122.

The operator-cache path and these diagnostics are retained for implementation
history but are not part of the final figure.

