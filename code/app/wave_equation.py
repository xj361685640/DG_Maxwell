#! /usr/bin/env python3

import arrayfire as af
af.set_backend('opencl')
import numpy as np
from matplotlib import pyplot as plt
import pylab as pl
from tqdm import trange

from app import params
from app import lagrange
from utils import utils

plt.rcParams['figure.figsize'  ] = 9.6, 6.
plt.rcParams['figure.dpi'      ] = 100
plt.rcParams['image.cmap'      ] = 'jet'
plt.rcParams['lines.linewidth' ] = 1.5
plt.rcParams['font.family'     ] = 'serif'
plt.rcParams['font.weight'     ] = 'bold'
plt.rcParams['font.size'       ] = 20
plt.rcParams['font.sans-serif' ] = 'serif'
plt.rcParams['text.usetex'     ] = True
plt.rcParams['axes.linewidth'  ] = 1.5
plt.rcParams['axes.titlesize'  ] = 'medium'
plt.rcParams['axes.labelsize'  ] = 'medium'
plt.rcParams['xtick.major.size'] = 8
plt.rcParams['xtick.minor.size'] = 4
plt.rcParams['xtick.major.pad' ] = 8
plt.rcParams['xtick.minor.pad' ] = 8
plt.rcParams['xtick.color'     ] = 'k'
plt.rcParams['xtick.labelsize' ] = 'medium'
plt.rcParams['xtick.direction' ] = 'in'
plt.rcParams['ytick.major.size'] = 8
plt.rcParams['ytick.minor.size'] = 4
plt.rcParams['ytick.major.pad' ] = 8
plt.rcParams['ytick.minor.pad' ] = 8
plt.rcParams['ytick.color'     ] = 'k'
plt.rcParams['ytick.labelsize' ] = 'medium'
plt.rcParams['ytick.direction' ] = 'in'




def mapping_xi_to_x(x_nodes, xi):
    '''
    Maps points in :math: `\\xi` space to :math:`x` space using the formula
    :math:  `x = \\frac{1 - \\xi}{2} x_0 + \\frac{1 + \\xi}{2} x_1`
    
    Parameters
    ----------
    
    x_nodes : arrayfire.Array
              Element nodes.
    
    xi      : numpy.float64
              Value of :math: `\\xi`coordinate for which the corresponding
              :math: `x` coordinate is to be found.
    
    Returns
    -------
    x : arrayfire.Array
        :math: `x` value in the element corresponding to :math:`\\xi`.
    '''
    N_0 = (1 - xi) / 2
    N_1 = (1 + xi) / 2
    
    N0_x0 = af.broadcast(utils.multiply, N_0, x_nodes[0])
    N1_x1 = af.broadcast(utils.multiply, N_1, x_nodes[1])
    
    x = N0_x0 + N1_x1
    
    return x



def dx_dxi_numerical(x_nodes, xi):
    '''
    Differential :math: `\\frac{dx}{d \\xi}` calculated by central differential
    method about xi using the mapping_xi_to_x function.
    
    Parameters
    ----------
    
    x_nodes : arrayfire.Array
              Contains the nodes of elements
    
    xi      : float
              Value of :math: `\\xi`
    
    Returns
    -------
    dx_dxi : arrayfire.Array
             :math:`\\frac{dx}{d \\xi}`. 
    '''
    dxi = 1e-7
    x2  = mapping_xi_to_x(x_nodes, xi + dxi)
    x1  = mapping_xi_to_x(x_nodes, xi - dxi)
    
    dx_dxi = (x2 - x1) / (2 * dxi)
    
    return dx_dxi


def dx_dxi_analytical(x_nodes, xi):
    '''
    The analytical result for :math:`\\frac{dx}{d \\xi}` for a 1D element is
    :math: `\\frac{x_1 - x_0}{2}`
    Parameters
    ----------
    x_nodes : arrayfire.Array
              An array containing the nodes of an element.
    
    Returns
    -------
    analytical_dx_dxi : arrayfire.Array
                        The analytical solution of :math:
                        `\\frac{dx}{d\\xi}` for an element.
    
    '''
    analytical_dx_dxi = (x_nodes[1] - x_nodes[0]) / 2
    
    return analytical_dx_dxi


def A_matrix():
    '''
    Calculates A matrix whose elements :math:`A_{p i}` are given by
    :math: `A_{p i} &= \\int^1_{-1} L_p(\\xi)L_i(\\xi) \\frac{dx}{d\\xi}`
    These elements are to be arranged in an :math:`N \times N` array with p
    varying from 0 to N - 1 along the rows and i along the columns.
    The integration is carried out using Gauss-Lobatto quadrature.
    
    Full description of the algorithm can be found here-
    `https://goo.gl/Cw6tnw`
    Returns
    -------
    A_matrix : arrayfire.Array
               The value of integral of product of lagrange basis functions
               obtained by LGL points, using Gauss-Lobatto quadrature method
               using :math: `N_LGL` points.
    '''
    A_matrix = np.zeros([params.N_LGL, params.N_LGL])

    for i in range (params.N_LGL):
        for j in range(params.N_LGL):
            A_matrix[i][j] = lagrange.Integrate(\
                    params.poly1d_product_list[params.N_LGL * i + j],\
                    9, 'lobatto_quadrature')

    dx_dxi = af.mean(dx_dxi_numerical((params.element_mesh_nodes[0 : 2]),\
                                                        params.xi_LGL))

    A_matrix *= dx_dxi

    A_matrix = af.np_to_af_array(A_matrix)
    

    return A_matrix



def flux_x(u):
    '''
    A function which returns the value of flux for a given wave function u.
    :math:`f(u) = c u^k`
    
    Parameters
    ----------
    u    : arrayfire.Array
           A 1-D array which contains the value of wave function.
    
    Returns
    -------
    flux : arrayfire.Array
           The value of the flux for given u.
    '''
    flux = params.c * u

    return flux

def wave_equation_lagrange_polynomials(u):
    '''
    '''
    wave_equation_in_lagrange_basis = []

    for i in range(0, params.N_Elements):
        element_wave_equation = lagrange.wave_equation_lagrange_basis(u, i)
        wave_equation_in_lagrange_basis.append(element_wave_equation)  

    return wave_equation_in_lagrange_basis


def volume_integral_flux(u_n):
    '''
    Calculates the volume integral of flux in the wave equation.
    :math:`\\int_{-1}^1 f(u) \\frac{d L_p}{d\\xi} d\\xi`
    This will give N values of flux integral as p varies from 0 to N - 1.
    
    This integral is carried out over an element with LGL nodes mapped onto it.
    
    Parameters
    ----------
    u : arrayfire.Array [N_LGL N_Elements 1 1]
        A 2D array containing the value of the wave function at
        the mapped LGL nodes in all the elements.
    
    Returns
    -------
    flux_integral : arrayfire.Array [N_LGL N_Elements 1 1]
                    A 1-D array of the value of the flux integral calculated
                    for various lagrange basis functions.
    '''
    wave_equation_in_lagrange_polynomials = wave_equation_lagrange_polynomials(u_n)
    differential_lagrange_poly = params.differential_lagrange_polynomial
    flux_integral = np.zeros([params.N_LGL, params.N_Elements])

    for i in range(params.N_LGL):
        for j in range(params.N_Elements):
            integrand = wave_equation_in_lagrange_polynomials[j] * differential_lagrange_poly[i]
            flux_integral[i][j] = lagrange.Integrate(integrand, 9, 'gauss_quadrature')

    flux_integral = af.np_to_af_array(flux_integral)

    return flux_integral


def lax_friedrichs_flux(u_n):
    '''
    A function which calculates the lax-friedrichs_flux :math:`f_i` using.
    :math:`f_i = \\frac{F(u^{i + 1}_0) + F(u^i_{N_{LGL} - 1})}{2} - \frac
                {\Delta x}{2\Delta t} (u^{i + 1}_0 - u^i_{N_{LGL} - 1})`
    
    Parameters
    ----------
    u_n : arrayfire.Array [N_LGL N_Elements 1 1]
          A 2D array consisting of the amplitude of the wave at the LGL nodes
          at each element.
    '''
    
    u_iplus1_0    = af.shift(u_n[0, :], 0, -1)
    u_i_N_LGL     = u_n[-1, :]
    flux_iplus1_0 = flux_x(u_iplus1_0)
    flux_i_N_LGL  = flux_x(u_i_N_LGL)
    
    boundary_flux = (flux_iplus1_0 + flux_i_N_LGL) / 2 \
                        - params.c_lax * (u_iplus1_0 - u_i_N_LGL) / 2
    
    
    return boundary_flux 


def surface_term(u_n):
    '''
    A function which is used to calculate the surface term,
    :math:`L_p (1) f_i - L_p (-1) f_{i - 1}`
    using the lax_friedrichs_flux function and lagrange_basis_value
    from params module.
    
    Parameters
    ----------
    u_n : arrayfire.Array [N_LGL N_Elements 1 1]
          A 2D array consisting of the amplitude of the wave at the LGL nodes
          at each element.

    Returns
    -------
    surface_term : arrayfire.Array [N_LGL N_Elements 1 1]
                   The surface term represented in the form of an array,
                   :math:`L_p (1) f_i - L_p (-1) f_{i - 1}`, where p varies from
                   zero to :math:`N_{LGL}` and i from zero to
                   :math:`N_{Elements}`. p varies along the rows and i along
                   columns.
    
    Reference
    ---------
    Link to PDF describing the algorithm to obtain the surface term.
    
    `https://goo.gl/Nhhgzx`
    '''

    L_p_minus1   = params.lagrange_basis_value[:, 0]
    L_p_1        = params.lagrange_basis_value[:, -1]
    f_i          = lax_friedrichs_flux(u_n)
    f_iminus1    = af.shift(f_i, 0, 1)
    surface_term = af.blas.matmul(L_p_1, f_i) - af.blas.matmul(L_p_minus1,\
                                                                    f_iminus1)
    
    return surface_term


def b_vector(u_n):
    '''
    Calculates the b vector for N_Elements number of elements.
    
    Parameters
    ----------
    u_n : arrayfire.Array [N_LGL N_Elements 1 1]
          A 2D array consisting of the amplitude of the wave at the
          LGL nodes at each element.
    Returns
    -------
    b_vector_array : arrayfire.Array
    '''

    volume_integral = volume_integral_flux(u_n)
    Surface_term    = surface_term(u_n)
    b_vector_array  = params.delta_t * (volume_integral - Surface_term)
    
    return b_vector_array


def time_evolution():
    '''
    Function which solves the wave equation
    :math: `u^{t_n + 1} = b(t_n) \\times A`
    iterated over time steps t_n and then plots :math: `x` against the amplitude
    of the wave. The images are then stored in Wave folder.
    '''
    
    A_inverse   = af.inverse(A_matrix())
    element_LGL = params.element_LGL
    delta_t     = params.delta_t
    amplitude   = params.u 
    time        = params.time
    
    for t_n in trange(0, time.shape[0] - 1):
        
        amplitude[:, :, t_n + 1] = amplitude[:, :, t_n] + af.blas.matmul(A_inverse,\
                b_vector(amplitude[:, :, t_n]))
    
    print('u calculated!')
    
    for t_n in trange(0, time.shape[0] - 1):
        
        if t_n % 100 == 0:
            
            fig = plt.figure()
            x   = params.element_LGL
            y   = amplitude[:, :, t_n]
            
            plt.plot(x, y)
            plt.xlabel('x')
            plt.ylabel('Amplitude')
            plt.title('Time = %f' % (t_n * delta_t))
            fig.savefig('results/1D_Wave_images/%04d' %(t_n / 100) + '.png')
            plt.close('all')
                
    return
