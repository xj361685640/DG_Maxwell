#! /usr/bin/env python3

import numpy as np
import arrayfire as af
af.set_backend('opencl')

from app import lagrange
from utils import utils
from app import wave_equation


# The domain of the function.
x_nodes    = af.np_to_af_array(np.array([-1., 1.]))

# The number of LGL points into which an element is split.
N_LGL      = 8

# Number of elements the domain is to be divided into.
N_Elements = 10

# The scheme to be used for integration. Values are either
# 'gauss_quadrature' or 'lobatto_quadrature'
scheme     = 'lobatto_quadrature'

# Wave speed.
c          = 1

# The total time for which the wave is to be evolved by the simulation. 
total_time = 10

# The c_lax to be used in the Lax-Friedrichs flux.
c_lax      = 1

# Array containing the LGL points in xi space.
xi_LGL     = lagrange.LGL_points(N_LGL)

# Array of the lobatto weights used during integration.
lobatto_weights = af.np_to_af_array(lagrange.lobatto_weights(N_LGL, xi_LGL))

# An array containing the coefficients of the lagrange basis polynomials.
lagrange_coeffs = af.np_to_af_array(lagrange.lagrange_polynomials(xi_LGL)[1])

# Refer corresponding functions.
dLp_xi               = lagrange.dLp_xi_LGL(lagrange_coeffs)
lagrange_basis_value = lagrange.lagrange_basis_function(lagrange_coeffs)


# Obtaining an array consisting of the LGL points mapped onto the elements.
element_size    = af.sum((x_nodes[1] - x_nodes[0]) / N_Elements)
elements_xi_LGL = af.constant(0, N_Elements, N_LGL)
elements        = utils.linspace(af.sum(x_nodes[0]),
                  af.sum(x_nodes[1] - element_size), N_Elements)

np_element_array   = np.concatenate((af.transpose(elements),
                               af.transpose(elements + element_size)))

element_mesh_nodes = utils.linspace(af.sum(x_nodes[0]),
                                    af.sum(x_nodes[1]), N_Elements + 1)

element_array = af.transpose(af.interop.np_to_af_array(np_element_array))
element_LGL   = wave_equation.mapping_xi_to_x(af.transpose(element_array), xi_LGL)


# The minimum distance between 2 mapped LGL points.
delta_x = af.min((element_LGL - af.shift(element_LGL, 1, 0))[1:, :])

# The value of time-step.
delta_t = delta_x / (20 * c)

# Array of timesteps seperated by delta_t.
time    = utils.linspace(0, int(total_time / delta_t) * delta_t,
                                                    int(total_time / delta_t))

# Initializing the amplitudes. Change u_init to required initial conditions.
u_init     = np.e ** (-(element_LGL) ** 2 / 0.4 ** 2)
u          = af.constant(0, N_LGL, N_Elements, time.shape[0],\
                                 dtype = af.Dtype.f64)
u[:, :, 0] = u_init





lagrange_poly1d_list = lagrange.lagrange_polynomials(xi_LGL)[0]

poly1d_product_list = lagrange.product_lagrange_poly(xi_LGL)



N_Gauss = 10

gauss_points  = lagrange.gauss_nodes(N_Gauss)
gauss_weights = af.np_to_af_array(np.zeros([N_Gauss]))

for i in range(0, N_Gauss):
    gauss_weights[i] = lagrange.gaussian_weights(N_Gauss, i)

differential_lagrange_polynomial = []
for i in range (0, N_LGL):
    test_diff = np.poly1d.deriv(lagrange_poly1d_list[i])
    differential_lagrange_polynomial.append(test_diff)
