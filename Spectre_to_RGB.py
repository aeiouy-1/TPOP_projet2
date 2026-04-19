import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import signal
import os
import shutil
from natsort import natsorted
import colour
from matplotlib.ticker import MultipleLocator

# --- 1. Paramètres à adapter ---
DOSSIER_FICHIERS = "Spectro/fibre_100um/d=26_5mm_prise2" 
DELIMITEUR = "\t" 

# Coupez les valeurs d'intensité en dessous de ce seuil pour éliminer le bruit du capteur.
# À ajuster selon l'intensité moyenne de votre "noir" dans vos fichiers bruts (ex: 0.05, 10, 50...)
SEUIL_DE_BRUIT = 0.0


#Constantes pour la conversion d,incrément à angle spatial
dV = 0.005                              # V/ incréments
conv_V_to_angle_galvos = 0.5            # V/°galvos
conv_theta = 0.4244683686               # °spatial/°galvos

# Calcul déphasage pour chaque incrémentation 
d_theta =  dV / conv_V_to_angle_galvos * conv_theta *60    # ' (minute d'arc)/ incréments   


def configure_article_style():
    latex_is_available = shutil.which("latex") is not None

    plt.rcParams.update(
        {
            "figure.dpi": 160,
            "savefig.dpi": 300,
            "axes.linewidth": 1.2,
            "axes.labelsize": 18,
            "axes.titlesize": 18,
            "xtick.labelsize": 15,
            "ytick.labelsize": 15,
            "legend.fontsize": 14,
            "lines.linewidth": 2.0,
            "lines.markersize": 4.5,
            "font.family": "serif",
            "mathtext.fontset": "cm",
            "text.usetex": latex_is_available,
        }
    )

    if not latex_is_available:
        plt.rcParams["font.serif"] = ["STIX Two Text", "Times New Roman", "DejaVu Serif"]


configure_article_style()


output_dir = "figure"
os.makedirs(output_dir, exist_ok=True)
figure_prefix = os.path.basename(os.path.normpath(DOSSIER_FICHIERS))






# --- 2. Récupération et tri des fichiers ---
# Toujours s'assurer que le tri alphanumérique correspond à l'ordre des pixels
fichiers = natsorted([f for f in os.listdir(DOSSIER_FICHIERS) if not f.startswith('.')])

if not fichiers:
    print("Erreur : Aucun fichier trouvé.")
    exit()

# Liste pour stocker l'énergie brute avant conversion
ligne_XYZ_brut = []

print(f"Assemblage whiskbroom de {len(fichiers)} pixels en cours...")


# Chargement des données de référence CIE (Fonctions colorimétriques)
# On utilise l'observateur standard de 1931 (2 degrés)
cmfs = colour.MSDS_CMFS['CIE 1931 2 Degree Standard Observer']
# Illuminant D65 (lumière du jour standard, utile pour la conversion spectrale)
illuminant = colour.SDS_ILLUMINANTS['D65']
donnees_spectrale = []

nb_max = 0

# --- 3. Traitement pixel par pixel (fichier par fichier) ---
for fichier in fichiers:
    # Chargement du spectre du pixel
    # Si le fichier contient 2 colonnes (ex: Longueur d'onde | Intensité), 
    # vous devrez peut-être adapter : donnees_pixel = np.loadtxt(...)[1]
    path = os.path.join(DOSSIER_FICHIERS, fichier)
    data = pd.read_csv(path, sep=DELIMITEUR, decimal=",", header=None, skiprows=14)
    longueurs_onde = data[0].astype(float).values
    intensites = data[1].astype(float).values


    donnees_spectrale.append([longueurs_onde, intensites])   

    max_local = max(intensites) 
    nb_max = max(nb_max, max_local)

    
    # Élimination du bruit de fond (tout ce qui est sous le seuil devient 0)
    intensites = np.maximum(intensites - SEUIL_DE_BRUIT, 0)


    # Création d'un objet Distribution Spectrale compréhensible par la librairie
    spectre = colour.SpectralDistribution(intensites, longueurs_onde)

    # On crée une "forme" standard : de 360 nm à 830 nm (le visible) avec un pas exact de 1 nm.
    # La fonction .interpolate() va lisser vos données pour les adapter à cette grille.
    forme_standard = colour.SpectralShape(360, 830, 1)
    spectre.interpolate(forme_standard)
    # -----------------------------

    
    # Étape A : Calcul de l'intégrale pour obtenir les valeurs CIE XYZ
    # La fonction gère l'interpolation et l'intégration pour vous
    XYZ = colour.sd_to_XYZ(spectre, cmfs, illuminant)
    ligne_XYZ_brut.append(XYZ)


    """
    # Étape B : Conversion XYZ vers sRGB (inclut la conversion matricielle)
    # Les valeurs XYZ sortent généralement sur une échelle de 0 à 100, 
    # la conversion RGB s'attend à une échelle normalisée.
    RGB_lineaire = colour.XYZ_to_sRGB(XYZ / 100.0)
    
    # Sécurité : on s'assure que les valeurs restent entre 0 et 1
    # (Des pics spectraux extrêmes peuvent parfois donner des valeurs hors limites)
    RGB = np.clip(RGB_lineaire, 0.0, 1.0)
    
    ligne_pixels_rgb.append(RGB)"""






# Conversion de la liste en tableau mathématique Numpy pour la suite
ligne_XYZ_brut = np.array(ligne_XYZ_brut)

# --- 3. Normalisation GLOBALE de la luminosité ---
# Dans l'espace CIE XYZ, le canal 'Y' correspond exactement à la luminance (luminosité perçue).
# On cherche le pixel ayant la plus forte luminance sur toute la ligne :
luminosite_max = np.max(ligne_XYZ_brut[:, 1]) 

print(f"Luminosité maximale détectée : {luminosite_max:.2f}")

# On met à l'échelle tout le tableau : le pixel le plus brillant aura une luminance de 1.0,
# et un pixel sans lumière aura 0.0.
if luminosite_max > 0:
    ligne_XYZ_normalisee = ligne_XYZ_brut / luminosite_max
else:
    ligne_XYZ_normalisee = ligne_XYZ_brut # Sécurité si l'image est 100% noire

# --- 4. Conversion massive vers sRGB ---
# La fonction colour.XYZ_to_sRGB est capable de traiter tout le tableau d'un seul coup
RGB_lineaire = colour.XYZ_to_sRGB(ligne_XYZ_normalisee)

# On s'assure qu'aucun artefact mathématique ne dépasse la limite 0-1
RGB_final = np.clip(RGB_lineaire, 0.0, 1.0)



# --- 3. Création de l'image 1D ---
# Format : (1, Nombre_de_pixels, 3)
image_1d = np.array([RGB_final])


# Note : Plus besoin de normalisation manuelle "min/max" ou de gamma ici ! 
# La fonction colour.XYZ_to_sRGB applique déjà le bon gamma sRGB d'affichage.
n = len(RGB_final)
limitation = [-n/2*d_theta, n/2*d_theta, -1, 1]


# --- 4. Affichage et Sauvegarde ---
fig_line, ax_line = plt.subplots(figsize=(10, 2.5))
ax_line.imshow(image_1d, aspect='auto', extent= limitation) 
#plt.title(f"Ligne Hyperspectrale ({len(fichiers)} pixels)")
ax_line.set_yticks([])
ax_line.set_xticks([-50,-40,-30,-20,-10,0,10,20,30,40,50])
ax_line.set_xlabel(r"Angle d'incidence ($\alpha_x$) [']")
fig_line.tight_layout()

line_pdf_path = os.path.join(output_dir, f"{figure_prefix}_ligne_rgb.pdf")
line_png_path = os.path.join(output_dir, f"{figure_prefix}_ligne_rgb.png")
# fig_line.savefig(line_pdf_path, format="pdf", bbox_inches="tight")
# fig_line.savefig(line_png_path, format="png", bbox_inches="tight")
print(f"Figure ligne RGB enregistrée dans : {os.path.abspath(line_pdf_path)}")
print(f"Figure ligne RGB PNG enregistrée dans : {os.path.abspath(line_png_path)}")

# plt.imsave(os.path.join(output_dir, f"{figure_prefix}_true_color_strip.png"), image_1d[0])
print("Image True Color générée avec succès !")
plt.show()


# Création de la figure

fig = plt.figure(constrained_layout = True, figsize=[10, 6])
gspec = fig.add_gridspec(nrows=2, ncols=2, height_ratios=[1, 2])

ax0 = fig.add_subplot(gspec[0,:])
ax1 = fig.add_subplot(gspec[1, 0])
ax2 = fig.add_subplot(gspec[1, 1])

# Création des titres de la figure
ax0.set_xlabel(r"Angle d'incidence ($\alpha_x$) [']")
ax1.set_xlabel(r"$\lambda$ [nm]")
ax1.set_ylabel("Intensité normalisée")
ax2.set_xlabel(r"$\lambda$ [nm]")
ax2.set_ylabel("Intensité normalisée")


ax0.imshow(image_1d, aspect='auto', extent = limitation)
ax0.get_yaxis().set_visible(False)
ax0.xaxis.set_major_locator(MultipleLocator(10))
ax0.tick_params(axis='x', which='both', direction='in')
ax1.plot(donnees_spectrale[125][0], donnees_spectrale[125][1]/nb_max)
ax2.plot(donnees_spectrale[276][0], donnees_spectrale[276][1]/nb_max)
ax1.tick_params(axis='both', which='both', direction='in')
ax2.tick_params(axis='both', which='both', direction='in')

composite_pdf_path = os.path.join(output_dir, f"{figure_prefix}_spectres_rgb.pdf")
composite_png_path = os.path.join(output_dir, f"{figure_prefix}_spectres_rgb.png")
# fig.savefig(composite_pdf_path, format="pdf", bbox_inches="tight")
# fig.savefig(composite_png_path, format="png", bbox_inches="tight")
print(f"Figure composite enregistrée dans : {os.path.abspath(composite_pdf_path)}")
print(f"Figure composite PNG enregistrée dans : {os.path.abspath(composite_png_path)}")

plt.show()
