# -*- coding: utf-8 -*-
# Author: Jiajun Ren <jiajunren0522@gmail.com>

'''
automatic Runge-Kutta method coefficient calculation
'''

import numpy as np
from scipy.misc import factorial


class Runge_Kutta(object):
    
    def __init__(self, method="C_RK4", TD=False, adaptive=False, rtol=1e-3):

        assert method in \
            ["Forward_Euler","midpoint_RK2","Heun_RK2","Ralston_RK2",\
                "Kutta_RK3","C_RK4","38rule_RK4","Fehlberg5", "RKF45"]
        self.method = method
        
        # if the propagator is time dependent
        self.TD = TD   
        self.adaptive = adaptive
        
        if method == "RKF45":
            self.adaptive = True
        
        self.rtol = rtol
        # if self.adaptive == True, please set rtol
    
        self.tableau, self.stage, self.order = self.tableau()
        if self.TD == False:
            # if time independent, stage is the same as order because of the
            # taylor expansion
            self.stage = self.order[-1]

    def Te_coeff(self):
        '''
        Taylor_expansion_coefficient
        '''
        assert self.TD == False
        return np.array([1./ factorial(i) for i in range(self.order[-1]+1)])


    def tableau(self):
        '''	
        Butcher tableau of the explicit Runge-Kutta methods.
        
        different types of propagation methods: e^-iHdt \Psi
        1.      classical 4th order Runge Kutta
                0   |
                1/2 |  1/2
                1/2 |   0    1/2
                1   |   0     0     1
                ----------------------------
                    |  1/6   1/3   1/3   1/6
    
        2.      Heun's method
                0   |  
                1   |   1    
                ----------------------------
                       1/2   1/2
        '''
    
        if self.method == "Forward_Euler":
            # Euler explicit
            a = np.array([[0]])
            b = np.array([1])
            c = np.array([0])
            Nstage = 1
            order = (1,)

        elif self.method in ["midpoint_RK2","Heun_RK2","Ralston_RK2"]:
            if self.method == "midpoint_RK2":
            # if alpha == 1, midpoint method
                alpha = 1.0
            elif self.method == "Heun_RK2":
            # if alpha == 0.5, heun's method
                alpha = 0.5
            elif self.method == "Ralston_RK2":
                alpha = 2.0/3.0
    
            a = np.array([[0,0],[alpha,0]])
            b = np.array([1-0.5/alpha,0.5/alpha])
            c = np.array([0,alpha])
            Nstage = 2
            order = (2,)

        elif self.method == "Kutta_RK3":
            # Kutta's third-order method
            a = np.array([[0,0,0],[0.5,0,0],[-1,2,0]])
            b = np.array([1.0/6.0,2.0/3.0,1.0/6.0])
            c = np.array([0,0.5,1])
            Nstage = 3
            order = (3,)

        elif self.method == "C_RK4":
            # Classic fourth-order method
            a = np.array([[0,0,0,0],[0.5,0,0,0],
                          [0,0.5,0,0],[0,0,1,0]])
            b = np.array([1.0/6.0,1.0/3.0,1.0/3.0,1.0/6.0])
            c = np.array([0,0.5,0.5,1.0])
            Nstage = 4
            order = (4,)

        elif self.method == "38rule_RK4":
            # 3/8 rule fourth-order method
            a = np.array([[0,0,0,0],\
                          [1.0/3.0,0,0,0],\
                          [-1.0/3.0,1,0,0],\
                          [1,-1,1,0]])
            b = np.array([1.0/8.0, 3.0/8.0, 3.0/8.0, 1.0/8.0])
            c = np.array([0.0, 1.0/3.0, 2.0/3.0 ,1.0])
            Nstage = 4
            order = (4,)

        elif self.method == "Fehlberg5":
            a = np.array([[0,0,0,0,0,0],
                         [1/4., 0., 0., 0., 0., 0.],
                         [3./32, 9./32, 0, 0, 0, 0 ],
                         [1932./2197, -7200./2197, 7296./2197, 0, 0, 0],
                         [439./216, -8., 3680./513, -845/4104, 0., 0.],
                         [-8./27, 2., -3544./2565, 1859./4104, -11./40, 0.]])
            b = np.array([16./135,0.,6656./12825,28561./56430,-9./50,2./55])
            c = np.array([0., 1./4, 3./8, 12./13, 1., 1./2])
            Nstage = 6
            order  = (5,)

        elif self.method == "RKF45":
            a = np.array(
    	        [[0.0,    0.0,       0.0,          0.0,          0.0,  0.0],
    	        [1./4,    0.0,       0.0,          0.0,          0.0,  0.0],
    	        [3./32,	 9./32,     0.0,          0.0,          0.0,  0.0],
    	        [1932./2197,-7200./2197, 7296./2197, 0.0,        0.0,  0.0],
    	        [439./216, -8.,     3680./513,   -845./4104,     0.0,  0.0],
    	        [-8./27,   2.,   -3544./2565,   1859./4104,    -11./40,0.0]])	
    	    c = np.array([0.0, 1./4, 3./8, 12./13, 1., 1/2.])  
    	    b = np.array(
    	        [[16./135, 0., 6656./12825, 28561./56430, -9./50, 2./55],
    	        [25./216, 0., 1408./2565,  2197./4104,   -1./5,  0.]])
            Nstage = 6
            order = (4,5)

        a = a.astype(np.float64)
        b = b.astype(np.float64)
        c = c.astype(np.float64)
        
        return [a,b,c], Nstage, order
    
    
    def runge_kutta_explicit_coefficient(self):
        '''
        only suited for time-independent propagator
        y'(t) = fy(t) f is time-independent
        the final formula is 
        y(t+dt) = d0 y(t) + d1 fy(t) dt + d2 f^2 y(t) dt^2 + ...
            0  f  f^2 f^3 f^4 
        v0
        v1
        v2
        v3
        Though, each order has different versions of RK methods, if f is time
        independent, the coefficient is the same. For example, Classical 4th order
        Runge Kutta and 3/8 rule Runge Kutta has some coefficient.
        '''
    
        a, b, c = self.tableau
        Nstage = self.stage

        table = np.zeros([Nstage+1, Nstage+1])
        table[0,0] = 1.0
        for istage in range(Nstage):
            table[istage+1,2:] = a[istage,:].dot(table[1:,1:])[:-1]
            table[istage+1,1] = 1.0
        
        if b.ndim == 1:
            # before RK4 
            coeff = np.zeros(Nstage+1)
            coeff[0] = 1.0
            coeff[1:] = b.dot(table[1:,1:])
        else:
            # after RK4
            coeff = np.zeros((b.shape[0],Nstage+1))
            coeff[:,0] = 1.0
            coeff[:,1:] = b.dot(table[1:,1:])
        
        # actully it is Taylor expansion for time independent f
    
        return coeff

def adaptive_fix(p):
    if p > 4:
        p = 4
        print ("p is fixed to 4")
    elif p < 0.1:
        p = 0.1
        print ("p is fixed to 0.1")

    return p

       
