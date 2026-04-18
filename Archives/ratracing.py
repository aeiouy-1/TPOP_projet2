import numpy as np
import matplotlib.pyplot as plt
from raytracing import *

# --- 1. VOS SPÉCIFICATIONS MATÉRIELLES ---

# Lentille Thorlabs LB1471-A
focale_lentille = 50.0  # Focale exacte en mm

# Contraintes de contrôle (Red Pitaya -> Galvos Thorlabs GVS002)
tension_max_rp = 1.0    # Sortie maximum de la Red Pitaya en Volts
facteur_galvo = 0.5     # Calibration : 0.5V = 1 degré mécanique

# Calcul de l'angle optique réel
angle_mecanique_max = tension_max_rp / facteur_galvo # = 2 degrés
angle_optique_max = angle_mecanique_max * 2          # = 4 degrés de déviation du faisceau

# --- 2. DÉFINITION DU CHEMIN OPTIQUE ---
distance_galvo_lentille = 90 # Configuration télécentrique standard

path = ImagingPath()
path.label = "Télescope Hyperspectral (Red Pitaya + LB1471-A)"
path.append(Space(d=distance_galvo_lentille, label="Espace Galvos-Lentille"))
path.append(Lens(f=focale_lentille, label="Thorlabs LB1471-A (f=50mm)"))
path.append(Space(d=90, label="Espace Lentille-Détecteur"))

# --- 3. PARAMÈTRES DE LA SOURCE LED ---
diametre_faisceau = 2.0  # Diamètre du faisceau LED sur le galvo (en mm, à ajuster)
divergence = 0.02        # Divergence propre à la LED (en radians)

# On va simuler les 3 états extrêmes de votre Red Pitaya : -1V, 0V (centre), et +1V
tensions_test = [-1.0, -0.5, 0.0, 0.5, 1.0] 

plt.figure(figsize=(10, 6))

for tension in tensions_test:
    # 1. On convertit la tension en angle de balayage optique
    angle_meca = tension / facteur_galvo
    angle_optique_deg = angle_meca * 2
    angle_optique_rad = angle_optique_deg * np.pi / 180
    
    # 2. On intègre l'angle de la LED (balayage + divergence naturelle)
    theta_max = angle_optique_rad + divergence
    theta_min = angle_optique_rad - divergence
    
    # 3. Création du faisceau
    faisceau_led = RandomUniformRays(
        yMax=diametre_faisceau/2, 
        yMin=-diametre_faisceau/2, 
        thetaMax=theta_max, 
        thetaMin=theta_min, 
        maxCount=2000 # On augmente le nombre de rayons pour un bel histogramme
    )
    
    # 4. Lancement de la simulation
    rayons_sortie = path.traceManyThrough(faisceau_led)
    positions_impact = [r.y for r in rayons_sortie]
    
    # 5. On trace l'intensité lumineuse pour cette tension
    plt.hist(positions_impact, bins=50, alpha=0.7, 
             label=f"Red Pitaya: {tension}V (Déviation optique {angle_optique_deg}°)")

# --- 4. AFFICHAGE DES LIMITES THÉORIQUES ---
# Calcul de la position maximale théorique du centre du spot
pos_max_theorique = focale_lentille * np.tan(angle_optique_max * np.pi / 180)

plt.title("Profil du spot LED sur le détecteur vs. Tension Red Pitaya", fontsize=14)
plt.xlabel("Position Y sur le détecteur (mm)", fontsize=12)
plt.ylabel("Intensité lumineuse", fontsize=12)

# Lignes pointillées pour marquer les bords de votre champ de vision atteignable
plt.axvline(pos_max_theorique, color='k', linestyle='--', label=f"Limite Max (+{pos_max_theorique:.2f} mm)")
plt.axvline(-pos_max_theorique, color='k', linestyle='--', label=f"Limite Min (-{pos_max_theorique:.2f} mm)")

plt.legend()
plt.grid(True, linestyle=':', alpha=0.8)
plt.show()