from raytracing import *

f1 = 70
f2 = 50
diameter1 = 25
diameter2 = 25   




path = ImagingPath()
path.append(Space(d=400))
path.append(Lens(f=f1, diameter=diameter1))
path.append(Space(d=f1 + f2))
path.append(Lens(f=f2, diameter=diameter2))
path.append(Space(d=f2))
path.display()