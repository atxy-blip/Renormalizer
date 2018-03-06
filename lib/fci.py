import numpy as np
import scipy.linalg
from itertools import izip

def fci_configs(nsites,pdim,pbond=None):
    """
    int,int -> tuple(int)
    Generate list of all possible configs
    associated with a given number of sites
    """
    if pbond is None:
        return [tuple(config) for config in 
            np.ndindex(tuple([pdim]*nsites))]
    else:
        return [tuple(config) for config in 
            np.ndindex(tuple(pbond))]


def fci_mps(fci,trunc=1.e-12,pbond=None,normalize=None,scheme=1):
    """
    convert fci->mps
    
    truncates by singular value if trunc<1,
    else, truncate by max m
    
    returns *left* canonicalized MPS
    """
    mps=[]
    nsites=len(fci.shape)

    if pbond is None:
        pdiml=fci.shape[0] # phys dim
        pdimr=fci.shape[0] # phys dim
    else:
        pdiml=pbond[0]

    residual=np.reshape(fci,[pdiml,np.prod(fci.shape[1:])])
    
    entropy = 0.0
    for i in xrange(nsites-1):
        if pbond is not None:
            pdiml=pbond[i]
            pdimr=pbond[i+1]
        
        u,sigma,vt=scipy.linalg.svd(residual,full_matrices=False)
        if trunc == 0:
            m_trunc = len(sigma)
            normed_sigma=sigma/scipy.linalg.norm(sigma)
            entropy += np.sum(normed_sigma*np.log(normed_sigma))
        elif trunc<1.:
            normed_sigma=sigma/scipy.linalg.norm(sigma)
            entropy += np.sum(normed_sigma*np.log(normed_sigma))
            if scheme == 1:
                # count how many sing vals < trunc            
                m_trunc = np.count_nonzero(normed_sigma>trunc)
            elif scheme == 2:
                tot = 0.0
                m_trunc = 0
                for isigma in normed_sigma:
                    tot += isigma ** 2
                    m_trunc += 1
                    #print "tot",tot
                    if tot > 1.-trunc:
                        break
        else:
            m_trunc=int(trunc)
            m_trunc=min(m_trunc,len(sigma))
        
        #print "m_trunc", m_trunc
        u=u[:,0:m_trunc]
        sigma=np.diag(sigma[0:m_trunc])
        vt=vt[0:m_trunc,:]

        residual=np.dot(sigma,vt)
        residual=np.reshape(residual,[m_trunc*pdimr,
                                     vt.shape[1]/pdimr])
        
        mpsi=np.reshape(u,[u.shape[0]/pdiml,pdiml,m_trunc])
        mps.append(mpsi)
    
    #print "entropy,", entropy
    #print "residual norm", np.linalg.norm(np.ravel(residual))

    if normalize is not None:
        residual = residual / np.linalg.norm(np.ravel(residual)) * normalize

    # last site, append residual
    mpsi=np.reshape(residual,[m_trunc,pdimr,1])
    mps.append(mpsi)
    
    return mps
