from raytracing import *


def inch_to_mm(inch):
    return inch * 25.4

lentille1 = {'f': 70, 'diameter': inch_to_mm(1)}
lentille2 = {'f': 50, 'diameter': inch_to_mm(1)}
lentille3 = {'f': 100, 'diameter': inch_to_mm(1)}




lentille_1 = Lens(f=lentille1['f'], diameter=lentille1['diameter'])
lentille_2 = Lens(f=lentille2['f'], diameter=lentille2['diameter'])
lentille_3 = Lens(f=lentille3['f'], diameter=lentille3['diameter'])
Miroir_1 = CurvedMirror(R=-10000000000, diameter=inch_to_mm(1))
Miroir_2 = CurvedMirror(R=-10000000000, diameter=inch_to_mm(1))


path = ImagingPath()
path.fanAngle=0.5
path.fanNumber=5
path.append(Space(d=200))
path.append(lentille_1)
path.append(Space(d=lentille1['f']+lentille2['f']))
path.append(lentille_2)
path.append(Space(d=lentille2['f']))
path.append(Miroir_1)
path.append(Space(d=100))
path.append(Miroir_2)
path.append(Space(d=100))
path.append(lentille_3)
path.append(Space(d=lentille3['f']))
path.display(onlyPrincipalAndAxialRays = False)



# path.append(System4f(f1=lentille_1['f'], f2=lentille_2['f'], diameter1=lentille_1['diameter'], diameter2=lentille_2['diameter']))
# # path.append(olympus.XLUMPlanFLN20X())
# # path.append(thorlabs.AC254_100_A())

# path.display()



path = ImagingPath()
# path.objectHeight=0.001
# path.fanAngle=0.1
# path.fanNumber=5
# path.append(Space(d=200))
# path.append(System4f(f1=lentille_1['f'], f2=lentille_2['f'], diameter1=lentille_1['diameter'], diameter2=lentille_2['diameter']))
# path.append(Space(d=100))
# path.append(Lens(f=100, diameter=25))
# path.display(onlyPrincipalAndAxialRays = False)