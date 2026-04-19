from pathlib import Path
import shutil

import colour
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
from natsort import natsorted
import numpy as np
import pandas as pd


# User settings: mainly change these two paths.
PROFILE_CSV_PATH = Path("image_gray_area/fibre_100/0to1V/line_015.csv")
SPECTRUM_FOLDER = Path("Spectro/fibre_100um/d=26_5mm_prise2")


DELIMITER = "\t"
NOISE_THRESHOLD = 0.0
DV = 0.005
CONV_V_TO_ANGLE_GALVOS = 0.5
CONV_THETA = 0.4244683686
ARC_MIN_PER_VOLT = (1 / CONV_V_TO_ANGLE_GALVOS) * CONV_THETA * 60
ARC_MIN_PER_INCREMENT = DV / CONV_V_TO_ANGLE_GALVOS * CONV_THETA * 60


def configure_plot_style():
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
            "lines.linewidth": 2.2,
            "lines.markersize": 4.5,
            "font.family": "serif",
            "mathtext.fontset": "cm",
            "text.usetex": latex_is_available,
        }
    )

    if not latex_is_available:
        plt.rcParams["font.serif"] = ["STIX Two Text", "Times New Roman", "DejaVu Serif"]


def select_profile_columns(data):
    lower_map = {column.lower(): column for column in data.columns}

    if "x_voltage" in lower_map and "intensity" in lower_map:
        return lower_map["x_voltage"], lower_map["intensity"]

    if "tension_x(v)" in lower_map and "intensite" in lower_map:
        return lower_map["tension_x(v)"], lower_map["intensite"]

    if "tension_y(v)" in lower_map and "intensite" in lower_map:
        return lower_map["tension_y(v)"], lower_map["intensite"]

    return data.columns[0], data.columns[1]


def build_profile_axis_label(x_column):
    upper_name = x_column.upper()
    if "X" in upper_name:
        return r"Angle d'incidence ($\alpha_x$) [']"
    if "Y" in upper_name:
        return r"Angle d'incidence ($\alpha_y$) [']"
    return r"Angle d'incidence [']"


def load_profile(profile_csv_path):
    data = pd.read_csv(profile_csv_path)
    if data.shape[1] < 2:
        raise ValueError("Le fichier de profil doit contenir au moins deux colonnes.")

    x_column, intensity_column = select_profile_columns(data)
    data[x_column] = pd.to_numeric(data[x_column], errors="coerce")
    data[intensity_column] = pd.to_numeric(data[intensity_column], errors="coerce")
    data = data.dropna(subset=[x_column, intensity_column]).copy()

    if data.empty:
        raise ValueError("Aucune donnee exploitable n'a ete trouvee dans le profil.")

    x_values = data[x_column] * ARC_MIN_PER_VOLT
    intensity = data[intensity_column]
    intensity = intensity - intensity.min()
    if intensity.max() > 0:
        intensity = intensity / intensity.max()

    return x_values, intensity, build_profile_axis_label(x_column)


def load_rgb_strip(spectrum_folder):
    spectral_files = natsorted([path for path in spectrum_folder.iterdir() if path.is_file() and not path.name.startswith(".")])
    if not spectral_files:
        raise FileNotFoundError(f"Aucun fichier spectral trouve dans : {spectrum_folder}")

    cmfs = colour.MSDS_CMFS["CIE 1931 2 Degree Standard Observer"]
    illuminant = colour.SDS_ILLUMINANTS["D65"]
    xyz_values = []

    for spectral_file in spectral_files:
        data = pd.read_csv(spectral_file, sep=DELIMITER, decimal=",", header=None, skiprows=14)
        wavelengths = data[0].astype(float).to_numpy()
        intensities = data[1].astype(float).to_numpy()
        intensities = np.maximum(intensities - NOISE_THRESHOLD, 0)

        spectrum = colour.SpectralDistribution(intensities, wavelengths)
        spectrum.interpolate(colour.SpectralShape(360, 830, 1))
        xyz_values.append(colour.sd_to_XYZ(spectrum, cmfs, illuminant))

    xyz_values = np.asarray(xyz_values)
    luminance_max = np.max(xyz_values[:, 1])
    if luminance_max > 0:
        xyz_values = xyz_values / luminance_max

    rgb_values = colour.XYZ_to_sRGB(xyz_values)
    rgb_values = np.clip(rgb_values, 0.0, 1.0)
    rgb_strip = np.array([rgb_values])

    number_of_pixels = len(rgb_values)
    extent = [-number_of_pixels / 2 * ARC_MIN_PER_INCREMENT, number_of_pixels / 2 * ARC_MIN_PER_INCREMENT, -1, 1]
    return rgb_strip, extent


def build_output_path(profile_csv_path, spectrum_folder):
    output_dir = Path("figure")
    output_dir.mkdir(exist_ok=True)
    return output_dir / f"{profile_csv_path.stem}__{spectrum_folder.name}.pdf"


def plot_combined_figure(profile_x, profile_y, profile_xlabel, rgb_strip, rgb_extent, output_path):
    annotation_fontsize = plt.rcParams["axes.labelsize"]
    figure, (ax_profile, ax_rgb) = plt.subplots(
        2,
        1,
        figsize=(10.0, 5.0),
        sharex=True,
        gridspec_kw={"height_ratios": [1.0, 1.0]},
        constrained_layout=False,
    )
    figure.subplots_adjust(left=0.12, right=0.98, top=0.97, bottom=0.16, hspace=0.08)

    ax_profile.plot(
        profile_x,
        profile_y,
        color="black",
        marker="o",
        markerfacecolor="white",
        markeredgewidth=1.1,
    )
    ax_profile.set_ylabel("Intensité normalisée")
    ax_profile.xaxis.set_major_locator(MultipleLocator(10))
    ax_profile.minorticks_on()
    ax_profile.tick_params(axis="both", which="both", direction="in")
    ax_profile.annotate(
        "(a)",
        xy=(0.02, 0.95),
        xycoords="axes fraction",
        ha="left",
        va="top",
        fontsize=annotation_fontsize,
        annotation_clip=False,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.9, "pad": 1.5},
    )

    ax_rgb.imshow(rgb_strip, aspect="auto", extent=rgb_extent)
    ax_rgb.set_xlabel(profile_xlabel)
    ax_rgb.set_yticks([])
    ax_rgb.xaxis.set_major_locator(MultipleLocator(10))
    ax_rgb.tick_params(axis="x", which="both", direction="out", top=False)
    ax_rgb.annotate(
        "(b)",
        xy=(0.02, 0.95),
        xycoords="axes fraction",
        ha="left",
        va="top",
        fontsize=annotation_fontsize,
        annotation_clip=False,
        bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.9, "pad": 1.5},
    )

    x_min = min(float(profile_x.min()), rgb_extent[0])
    x_max = max(float(profile_x.max()), rgb_extent[1])
    ax_profile.set_xlim(x_min, x_max)

    for axis in (ax_profile, ax_rgb):
        for spine in axis.spines.values():
            spine.set_linewidth(1.2)

    figure.savefig(output_path, format="pdf", bbox_inches="tight")
    print(f"Figure combinee enregistree dans : {output_path.resolve()}")
    plt.show()


def main():
    configure_plot_style()

    profile_csv_path = PROFILE_CSV_PATH.expanduser().resolve()
    spectrum_folder = SPECTRUM_FOLDER.expanduser().resolve()

    if not profile_csv_path.exists():
        raise FileNotFoundError(f"Fichier de profil introuvable : {profile_csv_path}")
    if not spectrum_folder.exists():
        raise FileNotFoundError(f"Dossier spectral introuvable : {spectrum_folder}")

    profile_x, profile_y, profile_xlabel = load_profile(profile_csv_path)
    rgb_strip, rgb_extent = load_rgb_strip(spectrum_folder)
    output_path = build_output_path(profile_csv_path, spectrum_folder)
    plot_combined_figure(profile_x, profile_y, profile_xlabel, rgb_strip, rgb_extent, output_path)


if __name__ == "__main__":
    main()
