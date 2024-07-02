# Reference: JCP2016, 145, 164105 and JCTC2023, 19, 6070

from renormalizer import BasisHalfSpin, Op, Quantity, BasisSHO, BasisDummy
from renormalizer.mps.mps import expand_bond_dimension_general
from renormalizer.sbm import ColeDavidsonSDF
from renormalizer.utils.configs import (
    EvolveMethod,
    EvolveConfig,
    CompressConfig,
    CompressCriteria,
)
from renormalizer.utils import constant
from renormalizer.utils.log import package_logger as logger
from renormalizer.tn import BasisTree, TreeNodeBasis, TTNS, TTNO

import numpy as np


n_ph_mode = 500
omega_c = Quantity(500, "cm-1").as_au()
ita = Quantity(2000, "cm-1").as_au() / 2
beta = 0.5
upper_limit = Quantity(1, "eV").as_au() * 5
logger.info(("phonon parameters", omega_c, ita, beta, upper_limit))
sdf = ColeDavidsonSDF(ita, omega_c, beta, upper_limit)
w, c2 = sdf.Wang1(n_ph_mode)
c = np.sqrt(c2)
logger.info(w)
logger.info(c)

reno = sdf.reno(w[-1])
logger.info(f"renormalization constant: {reno}")


n_e_mode = 160

beta_e = Quantity(1, "eV").as_au() * reno
alpha_e = Quantity(0.2, "eV").as_au() * reno
v = 0.1 * reno
mu_l = Quantity(v / 2, "eV").as_au()
mu_r = Quantity(-v / 2, "eV").as_au()


e_k = np.arange(1, n_e_mode + 1) / (n_e_mode + 1) * 4 * beta_e - 2 * beta_e
rho_e = 1 / (e_k[1] - e_k[0])
e_k_l = e_k - mu_l
e_k_r = e_k - mu_r

mode_with_e = [(f"L{i}", e) for i, e in enumerate(e_k_l)] + [(f"R{i}", e) for i, e in enumerate(e_k_r)]
mode_with_e.sort(key=lambda x: x[1])
logger.info(mode_with_e)

# subtree for the electrodes. Two subtrees depending on the energy level
# (rather than which electrode)
basis = []
first_positive = True
for mode, e in mode_with_e:
    if e > 0 and first_positive:
        first_positive = False
        basis.append(BasisHalfSpin("s"))
    basis.append(BasisHalfSpin(mode))

dofs = [b.dofs[0] for b in basis]
logger.info(dofs)
s_idx = dofs.index("s")
basis_tree_l = BasisTree.binary_mctdh(basis[:s_idx], dummy_label="EL-dummy")
basis_tree_r = BasisTree.binary_mctdh(basis[s_idx + 1 :], dummy_label="ER-dummy")


# the Hamiltonian
ham_terms = []
# current for the left electrode
i_l_terms = []
# current for the right electrode
i_r_terms = []
for mode, e in mode_with_e:
    if mode[0] == "L":
        mu = mu_l
        i_terms = i_l_terms
    else:
        assert mode[0] == "R"
        mu = mu_r
        i_terms = i_r_terms

    ham_terms.append(Op("+ -", mode, e + mu))
    v2 = alpha_e**2 / beta_e**2 * np.sqrt(4 * beta_e**2 - (e + mu) ** 2) / 2 / np.pi / rho_e
    v = np.sqrt(v2)
    idx = dofs.index(mode)
    if idx < s_idx:
        z_idx = list(range(idx + 1, s_idx))
    else:
        assert s_idx < idx
        z_idx = list(range(s_idx + 1, idx))
    z_dofs = [dofs[i] for i in z_idx]
    op1 = Op("+ " + "Z " * len(z_idx) + "-", [mode] + z_dofs + ["s"], v)
    op2 = Op("- " + "Z " * len(z_idx) + "+", [mode] + z_dofs + ["s"], v)
    ham_terms.extend([op1, op2])
    # move 1j to expectation
    i_terms.extend(op2 - op1)

# initial condition transformation
initial_occupied = True

if initial_occupied:
    ham_terms.append(Op("+ -", "s", qn=[0, 0], factor=-4 * (c**2 / w**2).sum()))

# vibrations at last

# boson energy
for imode in range(n_ph_mode):
    op1 = Op(r"p^2", f"v_{imode}", factor=0.5, qn=0)
    op2 = Op(r"x^2", f"v_{imode}", factor=0.5 * w[imode] ** 2, qn=0)
    ham_terms.extend([op1, op2])

# system-boson coupling
for imode in range(n_ph_mode):
    sys_op = Op("+ -", "s", qn=[0, 0])
    if initial_occupied:
        sys_op = sys_op - Op.identity("s")

    op = sys_op * Op(r"x", f"v_{imode}", factor=2 * c[imode], qn=[0])
    ham_terms.extend(op)

# put subtrees together for the final tree
nbas = np.max([16 * c2 / w**3, np.ones(n_ph_mode) * 4], axis=0)
nbas = np.round(nbas).astype(int)
logger.info(nbas)
basis_list_phonon = []
for imode in range(n_ph_mode):
    basis_list_phonon.append(BasisSHO(f"v_{imode}", w[imode], int(nbas[imode])))

basis_tree_phonon = BasisTree.binary_mctdh(basis_list_phonon, dummy_label="phonon-dummy")
node1 = TreeNodeBasis([BasisDummy("dummy")])
node1.add_child([basis_tree_l.root, basis_tree_r.root])
node2 = TreeNodeBasis([basis[s_idx]])
node2.add_child([node1, basis_tree_phonon.root])
basis_tree = BasisTree(node2)
basis_tree.print(logger.info)


# model = Model(basis, ham_terms)
ttno = TTNO(basis_tree, ham_terms)
i_l_mpo = TTNO(basis_tree, i_l_terms)
i_r_mpo = TTNO(basis_tree, i_r_terms)
n_l_mpo = TTNO(basis_tree, terms=[Op("+ -", f"L{i}") for i in range(n_e_mode)])
n_r_mpo = TTNO(basis_tree, terms=[Op("+ -", f"R{i}") for i in range(n_e_mode)])
n_s_mpo = TTNO(basis_tree, terms=Op("+ -", "s"))
ttno.print_shape(False, logger.info)
i_l_mpo.print_shape(False, logger.info)
i_r_mpo.print_shape(False, logger.info)
n_r_mpo.print_shape(False, logger.info)
n_s_mpo.print_shape(False, logger.info)
# 0 - [1, 0] (spin up) means occupation, 1 - [0, 1] (spin down) means unoccupation
# initial condition is taken care of in the Hamiltonian
condition = {dofs[i]: 1 for i in range(s_idx + 1, len(dofs))}
if initial_occupied:
    condition["s"] = 0
else:
    condition["s"] = 1

ttns = TTNS(basis_tree, condition=condition)
ttns.compress_config = CompressConfig(CompressCriteria.fixed, max_bonddim=32)
ttns = expand_bond_dimension_general(ttns, ttno, ex_mps=None)
ttns.evolve_config = EvolveConfig(EvolveMethod.tdvp_ps)
ttns.print_shape(print_function=logger.info, full=False)

step = 0.5 * constant.fs2au
# step = 5
nsteps = 100
au2muA = 6.623618237510e3
i = 0
current_list = []
while True:
    i_l = (1j * ttns.expectation(i_l_mpo)).real
    i_r = (1j * ttns.expectation(i_r_mpo)).real
    n_l = ttns.expectation(n_l_mpo)
    n_r = ttns.expectation(n_r_mpo)
    n_s = ttns.expectation(n_s_mpo)
    logger.info((i, ttns.bond_dims))
    current = (i_r - i_l) / 2 * au2muA
    logger.info((n_l, n_r, n_s, i_l * au2muA, i_r * au2muA, current))
    current_list.append(current)
    i += 1
    if i == nsteps:
        break
    if i > 0:
        ttns.evolve_config = EvolveConfig(EvolveMethod.tdvp_ps)
    ttns = ttns.evolve(ttno, step)
logger.info(current_list)
