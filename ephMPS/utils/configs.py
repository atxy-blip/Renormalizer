# -*- coding: utf-8 -*-
from enum import Enum
import logging

import scipy.linalg
import numpy as np

from ephMPS.utils.rk import RungeKutta

logger = logging.getLogger(__name__)


class BondOrderDistri(Enum):
    uniform = "uniform"
    center_gauss = "center gaussian"
    runtime = "runtime"


class CompressCriteria(Enum):
    threshold = "threshold"
    fixed = "fixed"
    both = "both"


class CompressConfig:
    def __init__(
        self,
        criteria: CompressCriteria = CompressCriteria.threshold,
        threshold: float = 1e-3,
        bondorder_distri: BondOrderDistri = BondOrderDistri.uniform,
        max_bondorder: int = None,
    ):
        # two sets of criteria here: threshold and max_bondorder
        # `criteria` is to determine which to use
        self.criteria: CompressCriteria = criteria
        self._threshold = 0.001
        self.threshold = threshold
        self.bond_order_distribution: BondOrderDistri = bondorder_distri
        self.max_bondorder = max_bondorder
        # the length should be len(mps) + 1, the terminals are also counted. This is for accordance with mps.bond_dims
        self.bond_orders: np.ndarray = None

    @property
    def threshold(self):
        return self._threshold

    @threshold.setter
    def threshold(self, v):
        if v <= 0:
            raise ValueError("non-positive threshold")
        elif v == 1:
            raise ValueError("1 is an ambiguous threshold")
        elif 1 < v:
            raise ValueError("Can't set threshold to be larger than 1")
        self._threshold = v

    def set_bondorder(self, length, max_value=None):
        if self.criteria is CompressCriteria.threshold:
            raise ValueError("compress config is using threshold criteria")
        if max_value is None:
            max_value = self.max_bondorder
        else:
            self.max_bondorder = max_value
        if max_value is None:
            raise ValueError("max value is not set")
        if self.bond_order_distribution == BondOrderDistri.uniform:
            self.bond_orders = np.full(length, max_value)
        else:
            assert length % 2 == 1
            half_length = length // 2
            x = np.arange(-half_length, half_length + 1)
            sigma = half_length / np.sqrt(np.log(max_value / 3))
            seq = list(max_value * np.exp(-(x / sigma) ** 2))
            self.bond_orders = np.int64(seq)
            assert not (self.bond_orders == 0).any()

    def set_runtime_bondorder(self, bond_orders):
        self.bond_order_distribution = BondOrderDistri.runtime
        self.bond_orders = np.array(bond_orders)

    def _threshold_m_trunc(self, sigma: np.ndarray) -> int:
        assert 0 < self.threshold < 1
        # count how many sing vals < trunc
        normed_sigma = sigma / scipy.linalg.norm(sigma)
        return int(np.sum(normed_sigma > self.threshold))

    def _fixed_m_trunc(self, sigma: np.ndarray, idx: int, left: bool) -> int:
        assert self.bond_orders is not None
        bond_idx = idx if left else idx + 1
        return min(self.bond_orders[bond_idx], len(sigma))

    def compute_m_trunc(self, sigma: np.ndarray, idx: int, left: bool) -> int:
        if self.criteria is CompressCriteria.threshold:
            trunc = self._threshold_m_trunc(sigma)
        elif self.criteria is CompressCriteria.fixed:
            trunc = self._fixed_m_trunc(sigma, idx, left)
        elif self.criteria is CompressCriteria.both:
            # use the smaller one
            trunc = min(
                self._threshold_m_trunc(sigma), self._fixed_m_trunc(sigma, idx, left)
            )
        else:
            assert False
        return trunc

    def update(self, other: "CompressConfig"):
        # use the stricter of the two
        if self.criteria != other.criteria:
            raise ValueError("Can't update configs with different standard")
        # look for minimum
        self.threshold = min(self.threshold, other.threshold)
        # look for maximum
        if self.bond_orders is None:
            self.bond_orders = other.bond_orders
        elif other.bond_orders is None:
            pass  # do nothing
        else:
            self.bond_orders = np.maximum(self.bond_orders, other.bond_orders)

    def relax(self):
        # relax the two criteria simultaneously
        self.threshold = min(
            self.threshold * 3, 0.9
        )  # can't set to 1 which is ambiguous
        if self.bond_orders is not None:
            self.bond_orders = np.maximum(
                np.int64(self.bond_orders * 0.8), np.full_like(self.bond_orders, 2)
            )

    def copy(self) -> "CompressConfig":
        new = self.__class__.__new__(self.__class__)
        # shallow copies
        new.__dict__ = self.__dict__.copy()
        # deep copy
        if self.bond_orders is not None:
            new.bond_orders = self.bond_orders.copy()
        return new


class OptimizeConfig:
    def __init__(self, procedure=None):
        if procedure is None:
            self.procedure = [[10, 0.4], [20, 0.2], [30, 0.1], [40, 0], [40, 0]]
        else:
            self.procedure = procedure
        self.method = "2site"
        self.nroots = 1
        self.inverse = 1.0
        # for dmrg-hartree hybrid to check converge. Not to confuse with compress threshold
        self.niterations = 20
        self.dmrg_thresh = 1e-5
        self.hartree_thresh = 1e-5


class EvolveMethod(Enum):
    prop_and_compress = "P&C"
    tdvp_ps = "TDVP_PS"
    tdvp_mctdh = "TDVP_MCTDH"
    tdvp_mctdh_new = "TDVP_MCTDHnew"


def parse_memory_limit(x) -> float:
    if x is None:
        return float("inf")
    try:
        return float(x)
    except (TypeError, ValueError):
        pass
    try:
        x_str = str(x)
        num, unit = x_str.split()
        unit = unit.lower()
        mapping = {"kb": 2 ** 10, "mb": 2 ** 20, "gb": 2 ** 30}
        return float(num) * mapping[unit]
    except:
        # might error when converting to str, but the message is clear enough.
        raise ValueError(f"invalid input for memory: {x}")


class EvolveConfig:
    def __init__(
        self,
        scheme: EvolveMethod = EvolveMethod.prop_and_compress,
        memory_limit=None,
        adaptive=False,
        evolve_dt=1e-1,
        enhance_symmetry=False,
    ):

        self.scheme = scheme
        if self.scheme == EvolveMethod.prop_and_compress:
            # note this memory limit is for single mps and not the whole program
            self.memory_limit: float = parse_memory_limit(memory_limit)
        else:
            if memory_limit is not None:
                raise ValueError(
                    "Memory limit is only valid in propagation and compression method."
                )

        if self.scheme != EvolveMethod.prop_and_compress:
            self.max_bond_order = 32
        else:
            self.max_bond_order = None

        # tdvp also requires prop and compress
        if adaptive:
            self.rk_config: RungeKutta = RungeKutta("RKF45")
        else:
            self.rk_config: RungeKutta = RungeKutta()
        self.adaptive = adaptive
        self.evolve_dt = evolve_dt  # a wild guess

        self.prop_method = "C_RK4"

        self.enhance_symmetry = enhance_symmetry
        self._enhance_symmetry_counter = 0
        # should adjust bond order before any tdvp evolution
        self._adjust_bond_order_counter = 10

    def enlarge_evolve_dt(self, ratio=1.5):
        self.evolve_dt *= ratio
        self._enhance_symmetry_counter += 3 * ratio
        self._adjust_bond_order_counter += 3 * ratio

    @property
    def should_adjust_bond_order(self):
        assert self.scheme != EvolveMethod.prop_and_compress
        self._adjust_bond_order_counter += 1
        if 10 < self._adjust_bond_order_counter:
            self._adjust_bond_order_counter = self._adjust_bond_order_counter % 10
            return True
        else:
            return False

    @property
    def should_switch_side(self):
        assert self.scheme != EvolveMethod.prop_and_compress
        if self.enhance_symmetry:
            self._enhance_symmetry_counter += 1
            if 10 < self._enhance_symmetry_counter:
                self._enhance_symmetry_counter = self._enhance_symmetry_counter % 10
                return True
        return False

    def copy(self):
        new = self.__class__.__new__(self.__class__)
        new.__dict__ = self.__dict__.copy()
        return new
