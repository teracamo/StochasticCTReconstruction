"""
The pipeline of this algorithms is inspired the paper written by H. Li et al. [1], [2] in attempts to generalize their
method for the use of medical computer tomography (CT). The algorithm consist of th e



References:

  [1] Li, Hechao, et al. Accurate stochastic reconstruction of heterogeneous microstructures by limited x-ray
      tomographic projections. Journal of Microscopy 264.3 2016: 339-350.

  [2] Li, Hechao, Nikhilesh Chawla, and Yang Jiao. "Reconstruction of heterogeneous materials via stochastic
      optimization of limited-angle X-ray tomographic projections." Scripta Materialia 86 (2014): 48-51.

"""

import numpy as np
import SimpleITK as sitk
import skimage.transform as tr
import Algorithm.AstraWrapper as awrapper
import os
import cv2

# Testing
import matplotlib as mpl
import matplotlib.pyplot as plt
import Algorithm.GaussianMixtureFitter as GFitter
import Algorithm.GaussianMixtureModel as MyGMM

mpl.style.use('ggplot')

def SampleImage(prob, sd):
    return np.random.normal(prob, sd)


# Use wat to cal the prior?
# Current enerty, current probability, GMM trend
def CalculatePrior(curPro, GMM_half, GMM_full):
    #--------------------------------------------
    # Process current probability
    cv2.bilateralFilter(curPro, 8, 100, 100)

    pair = GFitter.GaussianComponenetMatching(GMM_half, GMM_full)
    if len(pair < len(GMM_full)):
        raise ArithmeticError("Matching failed")

    #--------------------------------------------
    # Compare Gaussians' mean and sd changes


    #--------------------------------------------
    # Extrapolate trend

    #--------------------------------------------
    # Use predicted GMM to process current prob.

    return prob, sd


def main(inImage, reconmethod='sklearn', thetas = None, N = 128):
    if (thetas is None):
        thetas = np.linspace(0, 180, N)
    else:
        N =len(thetas)

    #====================================================================
    # Preprocessing
    #--------------------------------------------------------------------
    # Obtain n projections from input (psuedo raw data, theta in degrees)
    # The projections are then normalized based on the sum of all pixels
    # in the sinogram
    if (reconmethod == 'sklearn'):
        D = tr.radon(inImage, theta=thetas, circle=True)
    elif (reconmethod == 'astra'):
        D = awrapper.Projector()
        D.SetInputImage3D(inImage)
        D = D.Project(thetas)
    normD = D / abs(np.sum(D, axis=0))


    #--------------------------------------------------------------------
    # Filtered back projection based on N projectionsm, use ramp filter
    if (reconmethod == 'sklearn'):
        reconQuad = tr.iradon(D[:,::4], theta=thetas[::4], circle=True)
        reconTri = tr.iradon(D[:,::3], theta=thetas[::3], circle=True)
        reconHalf = tr.iradon(D[:,::2],theta=thetas[::2], circle=True)
        reconFull = tr.iradon(D, theta=thetas, circle=True)
        recon = reconHalf*reconFull/np.mean(reconHalf)


    #--------------------------------------------------------------------
    # Sirt algorithm reconstruction
    if (reconmethod == 'astra'):
        iterations = 1500
        astraMethod = 'SIRT_CUDA'
        reconFull = awrapper.Reconstructor()
        reconFull.SetReconVolumeGeom(imageShape=inImage.shape, circle_mask=True)
        reconFull.SetInputSinogram(D, thetas=thetas)
        reconFull = reconFull.Recon(astraMethod, iterations)
        reconHalf = awrapper.Reconstructor()
        reconHalf.SetReconVolumeGeom(imageShape=inImage.shape, circle_mask=True)
        reconHalf.SetInputSinogram(D[:,::2], thetas=thetas[::2])
        reconHalf = reconHalf.Recon(astraMethod, iterations)
        reconTri = awrapper.Reconstructor()
        reconTri.SetReconVolumeGeom(imageShape=inImage.shape, circle_mask=True)
        reconTri.SetInputSinogram(D[:,::3], thetas=thetas[::3])
        reconTri = reconTri.Recon(astraMethod, iterations)
        reconQuad = awrapper.Reconstructor()
        reconQuad.SetReconVolumeGeom(imageShape=inImage.shape, circle_mask=True)
        reconQuad.SetInputSinogram(D[:,::4], thetas=thetas[::4])
        reconQuad = reconQuad.Recon(astraMethod, iterations)

        reconImages = {'128': reconFull , '42': reconTri, '64': reconHalf, '32': reconQuad}
        for keys in reconImages:
            index = 0
            im = sitk.GetImageFromArray(reconImages[keys])
            fname = "Recon_%s_i%04d_s%03du%03d_%03d"%(astraMethod,
                                                      iterations,
                                                      int(thetas[0]),
                                                      int(thetas[-1]),
                                                      int(keys))
            fpath = "../TestData/"
            suffix = ".nii.gz"
            f =  fpath + fname + suffix
            while (os.path.isfile(f)):
                f = fpath + fname + "_%d"%index + suffix
                index += 1
            sitk.WriteImage(im, f)

    #
    # #-------------------------------------------
    # # Plot the reconstruction images
    # if (reconmethod == 'sklearn'):
    #     reconImages = {'128': reconFull , '42': reconTri, '64': reconHalf, '32': reconQuad}
    # elif (reconmethod == 'astra'):
    #     slicenum = 70
    #     reconImages = {'128': reconFull[N] , '42': reconTri[N], '64': reconHalf[N], '32': reconQuad[N]}
    # PlotGaussianFit(reconImages)
    # return
    #
    # #===========================================
    # # Simulated Annealling
    # #-------------------------------------------
    # # While Tempreture != 0, do while loop
    # trial = None
    # T = 100 #init temperature
 # E = 1.e31 # float 32 max
    # while(T > 10):
    #     #------------------------------------
    #     # Sample new image configuration
    #     # from the probability distribution
    #     trial = SampleImage(recon, 10)
    #
    #     #------------------------------------
    #     # Calculate energy by equation (3)
    #     D_star = tr.radon(trial, theta=thetas)
    #     normD_star = D_star / abs(np.sum(D_star, axis=0))
    #     trial_energy = np.sum(np.abs(normD - normD_star))
    #
    #     #-----------------------------------------------------------
    #     # Establish probability of excepting this configuration
    #     try:
    #         prob = np.min([1., np.exp(E/T)/np.exp(trial_energy/T)])
    #     except(OverflowError):
    #         print "Overflow error"
    #         prob = 1
    #     except(ValueError):
    #         print "Value Error"
    #         prob = 1
    #
    #     #----------------------------------------------------
    #     # Base on above probability roll dice see if except
    #     roll = np.random.rand()
    #     ###   if except, renew energy, reduce temperature
    #     if (roll <= prob):
    #         dE = trial_energy - E
    #         E = trial_energy
    #         T -= 1
    #         print "Current E %.05f  dE %.05f excepted at prob: %.2f"%(E, dE, prob)
    #
    #
    # #==============================================
    # # Plot Results
    # #==============================================
    # fig = plt.figure()
    # ax1 = fig.add_subplot(221)
    # ax2 = fig.add_subplot(222)
    # ax3 = fig.add_subplot(212)
    # ax1.imshow(recon, cmap="Greys_r", vmax=0, vmin=-3000)
    # ax2.imshow(trial, cmap="Greys_r", vmax=0, vmin=-3000)
    # ax3.imshow(inImage, cmap="Greys_r", vmax=0, vmin=-3000)
    # plt.show()
    pass


def PlotGaussianFit(reconImages):
    """
    Plot the histogram and the gaussian mixture model fitting result

    :param reconImages  Dictionary of input images
    :return:
    """
    #============================================
    # Setting up the figure
    #---------------------------------------------
    # Displaying a total of four subplots, two
    # holds the image inputs two holds the
    # histogram generate from them
    numOfImages = len(reconImages)
    fig = plt.figure(figsize=(8, 13), dpi=80)
    fig2 = plt.figure(figsize=(5,13), dpi=80)
    bx1 = fig2.add_subplot(311)
    bx2 = fig2.add_subplot(312)
    bx3 = fig2.add_subplot(313)

    #----------------------------------------------
    # Plot for every images
    resArray = []
    keys = reconImages.keys()
    print keys
    for i in xrange(len(reconImages)):
        ax1 = fig.add_subplot(numOfImages, 2, i * 2 + 1)
        ax2 = fig.add_subplot(numOfImages, 2, i * 2 + 2)
        ax1.imshow(reconImages[keys[i]], cmap="Greys_r")
        ax1.set_title("Input %s"%keys[i])
        hist = ax2.hist(reconImages[keys[i]].flatten(), alpha=0.8, bins=200, normed=True)
        ax2.set_title("Gaussian fitting for input %s"%keys[i])

        #============================================
        # Gaussian fitting
        #--------------------------------------------
        # Fit initial guess first, then fit 1D curve
        initGuess = GFitter.SKLearnFitter(reconImages[keys[i]].flatten(), numOfGaussians=[5])
        initGuess = np.array(initGuess)
        numOfFittedGauss = len(initGuess)
        res = GFitter.Fitter1D(hist[0], hist[1][:-1], energy='distancesq', numOfGaussians=numOfFittedGauss,
                                   initialGuess=initGuess, removeDistinct=True)
        resArray.append(res)
        res = res.Eval(hist[1][:-1])
        ax2.plot(hist[1][:-1], res)
        ax2.set_ylim([0, 0.010])
    changes = MyGMM.GMM.SortGMMs(resArray, True)


    #---------------------------------
    # Plot the change in SD and mean
    bx1.set_title("Change in mean")
    bx2.set_title("Change in sd")
    bx3.set_title("Change in weight")
    [bx1.plot(changes['mean'][i]) for i in xrange(len(changes['mean']))]
    [bx2.plot(changes['sd'][i]) for i in xrange(len(changes['sd']))]
    [bx3.plot(changes['weight'][i]) for i in xrange(len(changes['weight']))]

    #--------------------------
    # Maximize the plot window
    fig.set_tight_layout(True)
    plt.show()
    return

from multiprocessing import Process

if __name__ == '__main__':
    filename = "../TestData/LCTSP.nii.gz"
    input = sitk.GetArrayFromImage(sitk.ReadImage(filename))
    input[input == -3024] = 0

    N = 128
    for i in xrange(5):
        thetas = np.linspace(np.random.randint(0, 90), np.random.randint(90, 180), N)

        p = Process(target=main, args=[input, 'astra', thetas])
        p.start()

    p = Process(target=main, args=[input, 'astra', np.linspace(0, 1+80, 180)])
    p.start()
