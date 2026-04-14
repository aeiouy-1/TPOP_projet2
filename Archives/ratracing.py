import envexamples

from raytracing import *

import matplotlib.pyplot as plt

import numpy as np

thetas = []

positions1 = []

objectHalfHeight =focalRadius= 0.000250

scanAngle = 10*np.pi/180

pinholeModifier = {1 / 3: [], 1: [], 3: []}

positions = [1000, 800, 500, 300, 150, 100, 50, 25, 0, -25, -50, -100, -150, -300, -500, -800, -1000]

nRays = 100000

scanRays = UniformRays(yMax=0, thetaMax=scanAngle, M=1, N=nRays)

inputRays = RandomUniformRays(yMax=focalRadius, yMin=-focalRadius, maxCount=nRays)

focalSpotPosition=objFocalLength = 5

class UISUPLAPO60XW(Objective):

    def __init__(self):

        super(UISUPLAPO60XW, self).__init__(f=180/60,

        NA=1.2,

        focusToFocusLength=40,

        backAperture=7,

        workingDistance=0.28,

        magnification=60,

        fieldNumber=22,

        label=’UISUPLAPO60XW Objective’)

    def illuminationPath1():

        illumination1 = ImagingPath()
    # The object in this situation is the laser beam at the scanning element.

        illumination1.objectHeight = objectHalfHeight*2

        illumination1.rayNumber = 3

        illumination1.fanNumber = 3

        illumination1.fanAngle = 0

        illumination1.append(System4f(f1=40, f2=75, diameter1=24.5, diameter2=24.5))

        illumination1.append(System4f(f1=100, f2=100, diameter1=24.5, diameter2=24.5)) illumination1.append(Space(d=180/40))

        illumination1.append(UISUPLAPO60XW())

        illumination1.append(Space(d=180/40))

    return illumination1

    path1 = illuminationPath1()

    outputRays1 = path1.traceManyThrough(scanRays)

    for i in range(len(outputRays1)):

        thetas.append(scanRays[i].theta*180/np.pi)

        positions1.append(outputRays1[i].y*1000)

        scanRays.displayProgress()

        plt.plot(thetas,positions1)

        plt.xlabel(’Scan angle (degrees)’, fontsize=20)

        plt.ylabel(’Scanning position of the focal spot ($\micro$m)’, fontsize=20)

        plt.show()

    #--------------------------------------------------

    def path(focalSpotPosition=objFocalLength):

        illumination2 = ImagingPath()

        illumination2.append(Space(d=focalSpotPosition))

        illumination2.append(Lens(f=objFocalLength))

        illumination2.append(Space(d=105))

        illumination2.append(Lens(f=100))

        illumination2.append(Space(d=100))

        illumination2.append(System4f(f1=100, f2=75))

        illumination2.append(System4f(f1=40, f2=50)) # Path finishes at the pinhole position

    return illumination2

    def optimalPinholeSize():

    """

    Finds the magnification of the optical path and use it to find the optimal pinhole size when the focal spot is at one

    focal length distance of the objective.

    Return

    -----------

    pinholeIdeal : Float

    Returns the optimal pinhole size

    """

    # Dictionnary of the position and magnification of all conjugate planes of the focal spot.

        planes = path().intermediateConjugates()

        # The last conjugate plane is the pinhole. The magnification of this position is saved in mag.

        mag = planes[-1][1]

        # Calculates the pinhole size that fits perfectly the focal spot diameter.

        pinholeIdeal = abs(mag * (focalRadius * 2))

    return pinholeIdeal

    def rayEfficiency(pinholeFactor=None, focalSpotPosition2=None):

    """

    Determines the amount of rays emitted from the object that are detected at the pinhole plane.

    Parameter

    #---------------

    pinholeFactor : Float

    Factor changing the pinhole size according to the ideal pinhole size.

    focalSpotPosition : float

    Position of the focal spot according to the objective (first lens)

    Returns
    ------------

    illumination : object of ImagingPath class.

    Returns the illumination path

    """

        illumination2 = path(focalSpotPosition2)

        pinholeSize = optimalPinholeSize() * pinholeFactor

        illumination2.append(Aperture(diameter=pinholeSize))

        # Counts how many rays make it through the pinhole

        outputRays2 = illumination2.traceManyThroughInParallel(inputRays, progress=False)

    return outputRays2.count / inputRays.count

    for pinhole in pinholeModifier:

        print("\nComputing transmission for pinhole size {0:0.1f}".format(pinhole))

        efficiencyValues = []

    for z in positions:

        print(".",end='')

        newPosition = 5 + (z * 0.000001)

        efficiency = rayEfficiency(pinholeFactor=pinhole,   focalSpotPosition2=newPosition)

        efficiencyValues.append(efficiency)

        pinholeModifier[pinhole] = efficiencyValues

        plt.plot(positions, pinholeModifier[1 / 3], ’k:’, label=’Small pinhole’, linestyle=’dashed’)

        plt.plot(positions, pinholeModifier[1], ’k-’, label=’Ideal pinhole’)

        plt.plot(positions, pinholeModifier[3], ’k--’, label=’Large pinhole’, linestyle=’dotted’)

        plt.ylabel(’Transmission efficiency’, fontsize=20)

        plt.xlabel(’Position of the focal spot (nm)’, fontsize=20)

        plt.legend()

        plt.show()