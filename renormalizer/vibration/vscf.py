
import numpy as np
import scipy
import logging

from renormalizer.mps.backend import xp, OE_BACKEND
from renormalizer.mps.lib import Environ, cvec2cmat
from renormalizer.mps import Mpo, Mps
from renormalizer.mps.svd_qn import get_qn_mask
from renormalizer.mps.matrix import asnumpy, asxp
from renormalizer.mps.oe_contract_wrap import oe_contract
from renormalizer.utils import CompressConfig, CompressCriteria

logger = logging.getLogger(__name__)

class Vscf():
    r"""
        Vibrational Self-Consistent Field 
        
        The algorithm is like a DMRG sweep.
    """


    def __init__(self, model, mps=None):
        self.model = model
        self.c = [None,]*model.nsite # coefficient
        self.e = [None,]*model.nsite # energy

        if "h_mpo" in model.mpos.keys():
            logger.info("load h_mpo form model.mpos")
            self.h_mpo = model.mpos["h_mpo"]
        else:
            self.h_mpo = Mpo(model, algo="Hopcroft-Karp")
        if mps is None:
            self.mps = Mps.hartree_product_state(self.model, dict())
        else:
            self.mps = mps
    
    def kernel(self, nsweeps=100):
        mps = self.mps
        mpo = self.h_mpo

        # the default hartree_product_state is both L-/R- canonical
        if mps.is_left_canonical:
            mps.ensure_right_canonical()
            env = "R"
        else:
            mps.ensure_left_canonical()
            env = "L"
        environ = Environ(mps, mpo, env)

        converged = [False,]*len(mps)
        # DIIS algorithm may make this sweep converge more quickly
        for isweep in range(nsweeps):
            if isweep != 0:
                latest_c = [x.copy() for x in self.c]
                latest_e = [x.copy() for x in self.e]

            logger.info(f"isweep:{isweep}")
            for imps in mps.iter_idx_list(full=True):
                if mps.to_right:
                    lmethod, rmethod = "System", "Enviro"
                else:
                    lmethod, rmethod = "Enviro", "System"
                
                lidx = imps - 1
                cidx = [imps]
                ridx = imps + 1
                
                logger.debug(f"optimize site: {cidx}")
                
                ltensor = environ.GetLR("L", lidx, mps, mpo, itensor=None, method=lmethod)
                rtensor = environ.GetLR("R", ridx, mps, mpo, itensor=None, method=rmethod)
                
                # get the quantum number pattern
                qnbigl, qnbigr, qnmat = mps._get_big_qn(cidx)
                qn_mask = get_qn_mask(qnmat, mps.qntot)

                # center mo
                cmo = [asxp(mpo[idx]) for idx in cidx]

                # S-a   l-S
                #     d
                # O-b-O-f-O
                #     e
                # S-c   k-S
                ham = oe_contract(
                    "abc,bdef,lfk->adlcek",
                    ltensor, cmo[0], rtensor,
                    backend=OE_BACKEND
                )
                ham = ham[:, :, :, qn_mask][qn_mask, :]
                
                w, v = scipy.linalg.eigh(asnumpy(ham))
                # update modal energy
                self.e[imps] = w

                cstruct = cvec2cmat(v, qn_mask, nroots=len(w))
                mps.compress_config = CompressConfig(CompressCriteria.fixed,
                        max_bonddim=1)
                mps._update_mps(cstruct[0], cidx, qnbigl, qnbigr, 0)

                for cs in cstruct:
                    assert cs.shape == mps[imps].shape
                self.c[imps] = np.stack([x.ravel() for x in cstruct], axis=-1)               
                
                # check convergence       
                if isweep != 0:
                    converged[imps] = np.allclose(self.c[imps], latest_c[imps]) \
                        and np.allclose(self.e[imps], latest_e[imps])
            if np.all(converged):
                logger.info("vscf is converged!")
                break

            mps._switch_direction()
            
                    
            


        


