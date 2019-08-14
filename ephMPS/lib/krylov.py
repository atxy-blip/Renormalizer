# -*- coding: utf-8 -*-
# adopted from https://github.com/cmendl/pytenet/blob/master/pytenet/krylov.py

import logging

from scipy.linalg import eigh_tridiagonal
import numpy as np

from ephMPS.mps.backend import xp


logger = logging.getLogger(__name__)


def _expm_krylov(alpha, beta, V, v_norm, dt):
    # diagonalize Hessenberg matrix
    w_hess, u_hess = eigh_tridiagonal(alpha, beta)
    xp_w_hess = xp.array(w_hess)
    xp_u_hess = xp.array(u_hess)

    return V @ xp_u_hess @ (v_norm * xp.exp(dt*xp_w_hess) * xp_u_hess[0])


def expm_krylov(Afunc, dt, vstart):
    """
    Compute Krylov subspace approximation of the matrix exponential
    applied to input vector: `expm(dt*A)*v`.
    Reference:
        M. Hochbruck and C. Lubich
        On Krylov subspace approximations to the matrix exponential operator
        SIAM J. Numer. Anal. 34, 1911 (1997)
    """

    # normalize starting vector
    vstart = xp.asarray(vstart)
    nrmv = xp.linalg.norm(vstart)
    assert nrmv > 0
    vstart = vstart / nrmv
    # max iteration
    MAX_ITER = 50

    alpha = np.zeros(MAX_ITER)
    beta  = np.zeros(MAX_ITER-1)

    V = xp.zeros((MAX_ITER, len(vstart)), dtype=vstart.dtype)
    V[0] = vstart
    res = None

    for j in range(len(vstart) - 1):
        if MAX_ITER == j:
            raise RuntimeError("krylov not converged")
        w = Afunc(V[j])
        alpha[j] = xp.vdot(w, V[j]).real
        w -= alpha[j]*V[j] + (beta[j-1]*V[j-1] if j > 0 else 0)
        beta[j] = xp.linalg.norm(w)
        if beta[j] < 100*len(vstart)*np.finfo(float).eps:
            logger.warning(f'beta[{j}] ~= 0 encountered during Lanczos iteration.')
            return _expm_krylov(alpha[:j+1], beta[:j], V[:j+1, :].T, nrmv, dt)

        if 3 < j and j % 2 == 0:
            new_res = _expm_krylov(alpha[:j+1], beta[:j], V[:j+1].T, nrmv, dt)
            if res is not None and xp.allclose(res, new_res):
                return new_res
            else:
                res = new_res
        V[j + 1] = w / beta[j]
    return _expm_krylov(alpha, beta, V.T, nrmv, dt)



