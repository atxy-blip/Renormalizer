# -*- coding: utf-8 -*-

from ephMPS.sbm import SBM, param2mollist
from ephMPS.utils import Quantity, CompressConfig, EvolveConfig


if __name__ == "__main__":
    alpha = 0.05
    raw_delta = Quantity(1)
    raw_omega_c = Quantity(20)
    n_phonons = 300
    mol_list = param2mollist(alpha, raw_delta, raw_omega_c, n_phonons)

    compress_config = CompressConfig(threshold=1e-4)
    evolve_config = EvolveConfig(adaptive=True, evolve_dt=0.1)
    sbm = SBM(mol_list, Quantity(0), compress_config=compress_config, evolve_config=evolve_config, dump_dir="./", job_name="sbm")
    sbm.evolve(evolve_time=20)