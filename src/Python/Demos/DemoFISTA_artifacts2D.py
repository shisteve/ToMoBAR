#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GPLv3 license (ASTRA toolbox)
Note that the TomoPhantom package is released under Apache License, Version 2.0

Script to generate 2D analytical phantoms and their sinograms with added noise and artifacts
Sinograms then reconstructed using tomobar using different data fidelities

>>>>> Dependencies (reconstruction): <<<<<
1. ASTRA toolbox: conda install -c astra-toolbox astra-toolbox
2. tomobar: conda install -c dkazanc tomobar
or install from https://github.com/dkazanc/tomobar

This demo demonstrates frequent inaccuracies which are accosiated with X-ray imaging:
zingers, rings and noise
"""
import numpy as np
import matplotlib.pyplot as plt
from tomophantom import TomoP2D
import os
import tomophantom
from tomophantom.supp.qualitymetrics import QualityTools

model = 4 # select a model
N_size = 512 # set dimension of the phantom
# one can specify an exact path to the parameters file
# path_library2D = '../../../PhantomLibrary/models/Phantom2DLibrary.dat'
path = os.path.dirname(tomophantom.__file__)
path_library2D = os.path.join(path, "Phantom2DLibrary.dat")
phantom_2D = TomoP2D.Model(model, N_size, path_library2D)

plt.close('all')
plt.figure(1)
plt.rcParams.update({'font.size': 21})
plt.imshow(phantom_2D, vmin=0, vmax=1, cmap="gray")
plt.colorbar(ticks=[0, 0.5, 1], orientation='vertical')
plt.title('{}''{}'.format('2D Phantom using model no.',model))

# create sinogram analytically
angles_num = int(0.5*np.pi*N_size); # angles number
angles = np.linspace(0.0,179.9,angles_num,dtype='float32')
angles_rad = angles*(np.pi/180.0)
P = int(np.sqrt(2)*N_size) #detectors

sino_an = TomoP2D.ModelSino(model, N_size, P, angles, path_library2D)

plt.figure(2)
plt.rcParams.update({'font.size': 21})
plt.imshow(sino_an,  cmap="gray")
plt.colorbar(ticks=[0, 150, 250], orientation='vertical')
plt.title('{}''{}'.format('Analytical sinogram of model no.',model))

#%%
# Adding artifacts and noise
from tomophantom.supp.artifacts import ArtifactsClass

# adding noise
artifacts_add = ArtifactsClass(sino_an)
#noisy_sino = artifacts_add.noise(sigma=0.1,noisetype='Gaussian')
noisy_sino = artifacts_add.noise(sigma=10000,noisetype='Poisson')

# adding object shifts (misalignment)
artifacts_add = ArtifactsClass(noisy_sino)
noisy_sino_misalign = artifacts_add.shifts(maxamplitude = 10)

# adding zingers
artifacts_add =ArtifactsClass(noisy_sino)
noisy_zing = artifacts_add.zingers(percentage=0.25, modulus = 10)

#adding stripes
artifacts_add =ArtifactsClass(noisy_zing)
noisy_zing_stripe = artifacts_add.stripes(percentage=1, maxthickness = 1)
noisy_zing_stripe[noisy_zing_stripe < 0] = 0

plt.figure()
plt.rcParams.update({'font.size': 21})
plt.imshow(noisy_zing_stripe,cmap="gray")
plt.colorbar(ticks=[0, 150, 250], orientation='vertical')
plt.title('{}''{}'.format('Analytical noisy sinogram with artifacts.',model))
#%%
from tomobar.methodsDIR import RecToolsDIR
RectoolsDIR = RecToolsDIR(DetectorsDimH = P,  # DetectorsDimH # detector dimension (horizontal)
                    DetectorsDimV = None,  # DetectorsDimV # detector dimension (vertical) for 3D case only
                    AnglesVec = angles_rad, # array of angles in radians
                    ObjSize = N_size, # a scalar to define reconstructed object dimensions
                    device='gpu')

print ("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
print ("Reconstructing analytical sinogram using FBP (tomobar)...")
print ("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
FBPrec_ideal = RectoolsDIR.FBP(sino_an)  # ideal reconstruction
FBPrec_error = RectoolsDIR.FBP(noisy_zing_stripe) # reconstruction with artifacts
FBPrec_misalign = RectoolsDIR.FBP(noisy_sino_misalign) # reconstruction with misalignment

plt.figure()
plt.subplot(131)
plt.imshow(FBPrec_ideal, vmin=0, vmax=1, cmap="gray")
plt.colorbar(ticks=[0, 0.5, 1], orientation='vertical')
plt.title('Ideal FBP reconstruction')
plt.subplot(132)
plt.imshow(FBPrec_error, vmin=0, vmax=1, cmap="gray")
plt.colorbar(ticks=[0, 0.5, 1], orientation='vertical')
plt.title('Erroneous data FBP Reconstruction')
plt.subplot(133)
plt.imshow(FBPrec_misalign, vmin=0, vmax=1, cmap="gray")
plt.colorbar(ticks=[0, 0.5, 1], orientation='vertical')
plt.title('Misaligned noisy FBP Reconstruction')
plt.show()

plt.figure() 
plt.imshow(abs(FBPrec_ideal-FBPrec_error), vmin=0, vmax=1, cmap="gray")
plt.colorbar(ticks=[0, 0.5, 1], orientation='vertical')
plt.title('FBP reconsrtuction differences')
#%%
print ("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
print ("Reconstructing using FISTA method (tomobar)")
print ("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
from tomobar.methodsIR import RecToolsIR
RectoolsIR = RecToolsIR(DetectorsDimH = P,  # DetectorsDimH # detector dimension (horizontal)
                    DetectorsDimV = None,  # DetectorsDimV # detector dimension (vertical) for 3D case only
                    CenterRotOffset = None, # Center of Rotation (CoR) scalar (for 3D case only)
                    AnglesVec = angles_rad, # array of angles in radians
                    ObjSize = N_size, # a scalar to define reconstructed object dimensions
                    datafidelity='LS', #data fidelity, choose LS, PWLS, GH (wip), Student (wip)
                    nonnegativity='ENABLE', # enable nonnegativity constraint (set to 'ENABLE')
                    OS_number = None, # the number of subsets, NONE/(or > 1) ~ classical / ordered subsets
                    tolerance = 1e-06, # tolerance to stop outer iterations earlier
                    device='gpu')

lc = RectoolsIR.powermethod() # calculate Lipschitz constant

# Run FISTA reconstrucion algorithm with regularisation 
RecFISTA_LS_reg = RectoolsIR.FISTA(noisy_zing_stripe,
                                   iterationsFISTA = 350, 
                                   regularisation = 'ROF_TV', 
                                   regularisation_parameter = 0.003,
                                   lipschitz_const = lc)
plt.figure()
plt.imshow(RecFISTA_LS_reg, vmin=0, vmax=1, cmap="gray")
plt.colorbar(ticks=[0, 0.5, 1], orientation='vertical')
plt.title('FISTA-LS-TV reconstruction')
#%%
RectoolsIR = RecToolsIR(DetectorsDimH = P,  # DetectorsDimH # detector dimension (horizontal)
                    DetectorsDimV = None,  # DetectorsDimV # detector dimension (vertical) for 3D case only
                    CenterRotOffset = None, # Center of Rotation (CoR) scalar (for 3D case only)
                    AnglesVec = angles_rad, # array of angles in radians
                    ObjSize = N_size, # a scalar to define reconstructed object dimensions
                    datafidelity='LS', #data fidelity, choose LS, PWLS, GH (wip), Student (wip)
                    nonnegativity='ENABLE', # enable nonnegativity constraint (set to 'ENABLE')
                    OS_number = None, # the number of subsets, NONE/(or > 1) ~ classical / ordered subsets
                    tolerance = 1e-06, # tolerance to stop outer iterations earlier
                    device='gpu')

RecFISTA_Huber_reg = RectoolsIR.FISTA(noisy_zing_stripe, 
                                   huber_data_threshold = 4.0,
                                   iterationsFISTA = 350, 
                                   regularisation = 'ROF_TV', 
                                   regularisation_parameter = 0.003,
                                   lipschitz_const = lc)

plt.figure()
plt.subplot(121)
plt.imshow(RecFISTA_LS_reg, vmin=0, vmax=1, cmap="gray")
plt.colorbar(ticks=[0, 0.5, 1], orientation='vertical')
plt.title('FISTA-LS-TV reconstruction')
plt.subplot(122)
plt.imshow(RecFISTA_Huber_reg, vmin=0, vmax=1, cmap="gray")
plt.colorbar(ticks=[0, 0.5, 1], orientation='vertical')
plt.title('FISTA-Huber-TV reconstruction')
plt.show()

# calculate errors 
Qtools = QualityTools(phantom_2D, RecFISTA_LS_reg)
RMSE_FISTA_LS_TV = Qtools.rmse()
Qtools = QualityTools(phantom_2D, RecFISTA_Huber_reg)
RMSE_FISTA_HUBER_TV = Qtools.rmse()
print("RMSE for FISTA-LS-TV reconstruction is {}".format(RMSE_FISTA_LS_TV))
print("RMSE for FISTA-Huber-TV is {}".format(RMSE_FISTA_HUBER_TV))
#%%
print ("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
print ("Reconstructing using FISTA-OS method (tomobar)")
print ("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")

from tomobar.methodsIR import RecToolsIR
RectoolsIR = RecToolsIR(DetectorsDimH = P,  # DetectorsDimH # detector dimension (horizontal)
                    DetectorsDimV = None,  # DetectorsDimV # detector dimension (vertical) for 3D case only
                    CenterRotOffset = None, # Center of Rotation (CoR) scalar (for 3D case only)
                    AnglesVec = angles_rad, # array of angles in radians
                    ObjSize = N_size, # a scalar to define reconstructed object dimensions
                    datafidelity='LS', #data fidelity, choose LS, PWLS, Huber, GH (wip), Student (wip)
                    nonnegativity='ENABLE', # enable nonnegativity constraint (set to 'ENABLE')
                    OS_number = 12, # the number of subsets, NONE/(or > 1) ~ classical / ordered subsets
                    tolerance = 1e-06, # tolerance to stop outer iterations earlier
                    device='gpu')


lc = RectoolsIR.powermethod() # calculate Lipschitz constant

# Run FISTA reconstrucion algorithm with regularisation 
RecFISTA_LS_reg = RectoolsIR.FISTA(noisy_zing_stripe, 
                                   iterationsFISTA = 15, 
                                   regularisation = 'ROF_TV', 
                                   regularisation_parameter = 0.01,
                                   regularisation_iterations = 300,
                                   lipschitz_const = lc)
#%%
RectoolsIR = RecToolsIR(DetectorsDimH = P,  # DetectorsDimH # detector dimension (horizontal)
                    DetectorsDimV = None,  # DetectorsDimV # detector dimension (vertical) for 3D case only
                    CenterRotOffset = None, # Center of Rotation (CoR) scalar (for 3D case only)
                    AnglesVec = angles_rad, # array of angles in radians
                    ObjSize = N_size, # a scalar to define reconstructed object dimensions
                    datafidelity='LS', #data fidelity, choose LS, PWLS, GH (wip), Student (wip)
                    nonnegativity='ENABLE', # enable nonnegativity constraint (set to 'ENABLE')
                    OS_number = 12, # the number of subsets, NONE/(or > 1) ~ classical / ordered subsets
                    tolerance = 1e-06, # tolerance to stop outer iterations earlier
                    device='gpu')

RecFISTA_Huber_reg = RectoolsIR.FISTA(noisy_zing_stripe, 
                                   huber_data_threshold = 4.0,
                                   iterationsFISTA = 15, 
                                   regularisation = 'ROF_TV', 
                                   regularisation_parameter = 0.01,
                                   regularisation_iterations = 300,
                                   lipschitz_const = lc)

plt.figure()
plt.subplot(121)
plt.imshow(RecFISTA_LS_reg, vmin=0, vmax=1, cmap="gray")
plt.colorbar(ticks=[0, 0.5, 1], orientation='vertical')
plt.title('FISTA-OS-LS-TV reconstruction')
plt.subplot(122)
plt.imshow(RecFISTA_Huber_reg, vmin=0, vmax=1, cmap="gray")
plt.colorbar(ticks=[0, 0.5, 1], orientation='vertical')
plt.title('FISTA-OS-Huber-TV reconstruction')
plt.show()

# calculate errors 
Qtools = QualityTools(phantom_2D, RecFISTA_LS_reg)
RMSE_FISTA_LS_TV = Qtools.rmse()
Qtools = QualityTools(phantom_2D, RecFISTA_Huber_reg)
RMSE_FISTA_HUBER_TV = Qtools.rmse()
print("RMSE for FISTA-OS-LS-TV reconstruction is {}".format(RMSE_FISTA_LS_TV))
print("RMSE for FISTA-OS-Huber-TV is {}".format(RMSE_FISTA_HUBER_TV))
#%%
print ("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
print ("Reconstructing using FISTA-Group-Huber method (tomobar)")
print ("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")

from tomobar.methodsIR import RecToolsIR

RectoolsIR = RecToolsIR(DetectorsDimH = P,  # DetectorsDimH # detector dimension (horizontal)
                    DetectorsDimV = None,  # DetectorsDimV # detector dimension (vertical) for 3D case only
                    CenterRotOffset = None, # Center of Rotation (CoR) scalar (for 3D case only)
                    AnglesVec = angles_rad, # array of angles in radians
                    ObjSize = N_size, # a scalar to define reconstructed object dimensions
                    datafidelity='LS', #data fidelity, choose LS, PWLS, Huber, GH (wip), Student (wip)
                    nonnegativity='ENABLE', # enable nonnegativity constraint (set to 'ENABLE')
                    OS_number = None, # the number of subsets, NONE/(or > 1) ~ classical / ordered subsets
                    tolerance = 1e-06, # tolerance to stop outer iterations earlier
                    device='gpu')

lc = RectoolsIR.powermethod() # calculate Lipschitz constant

# Run FISTA reconstrucion algorithm with regularisation 
RecFISTA_LS_GH_reg = RectoolsIR.FISTA(noisy_zing_stripe, 
                                   lambdaR_L1 = 0.0025,
                                   alpha_ring = 150,
                                   iterationsFISTA = 150, 
                                   regularisation = 'ROF_TV', 
                                   regularisation_parameter = 0.01,
                                   regularisation_iterations = 80,
                                   lipschitz_const = lc)

plt.figure()
plt.imshow(RecFISTA_LS_GH_reg, vmin=0, vmax=1, cmap="gray")
plt.colorbar(ticks=[0, 0.5, 1], orientation='vertical')
plt.title('FISTA-OS-GH-TV reconstruction')
plt.show()

# calculate errors 
Qtools = QualityTools(phantom_2D, RecFISTA_LS_GH_reg)
RMSE_FISTA_LS_GH_TV = Qtools.rmse()
print("RMSE for FISTA-LS-GH-TV reconstruction is {}".format(RMSE_FISTA_LS_GH_TV))
#%%
