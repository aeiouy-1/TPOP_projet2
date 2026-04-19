from pathlib import Path
import shutil

import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
import pandas as pd


# User setting: only change this variable.
CSV_PATH = Path("image_gray_area/fibre_100/0to1V/line_015.csv")


# Same spatial conversion used in Spectre_to_RGB.py
CONV_V_TO_ANGLE_GALVOS = 0.5          # V / degre galvo
CONV_THETA = 0.4244683686             # degre spatial / degre galvo
ARC_MIN_PER_VOLT = (1 / CONV_V_TO_ANGLE_GALVOS) * CONV_THETA * 60


def configure_plot_style():
    latex_is_available = shutil.which("latex") is not None

    plt.rcParams.update(
        {
            "figure.dpi": 160,
            "savefig.dpi": 300,
            "figure.figsize": (10.0, 2.5),
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


def load_profile(csv_path):
    data = pd.read_csv(csv_path)
    if data.shape[1] < 2:
        raise ValueError("Le fichier CSV doit contenir au moins deux colonnes.")

    x_column, intensity_column = select_profile_columns(data)
    data[x_column] = pd.to_numeric(data[x_column], errors="coerce")
    data[intensity_column] = pd.to_numeric(data[intensity_column], errors="coerce")
    data = data.dropna(subset=[x_column, intensity_column]).copy()

    if data.empty:
        raise ValueError("Aucune donnee exploitable n'a ete trouvee dans le CSV.")

    return data, x_column, intensity_column


def select_profile_columns(data):
    lower_map = {column.lower(): column for column in data.columns}

    if "x_voltage" in lower_map and "intensity" in lower_map:
        return lower_map["x_voltage"], lower_map["intensity"]

    if "tension_x(v)" in lower_map and "intensite" in lower_map:
        return lower_map["tension_x(v)"], lower_map["intensite"]

    if "tension_y(v)" in lower_map and "intensite" in lower_map:
        return lower_map["tension_y(v)"], lower_map["intensite"]

    return data.columns[0], data.columns[1]


def build_axis_label(x_column):
    upper_name = x_column.upper()
    if "X" in upper_name:
        return r"Angle d'incidence ($\alpha_x$) [']"
    if "Y" in upper_name:
        return r"Angle d'incidence ($\alpha_y$) [']"
    return r"Angle d'incidence [']"


def convert_voltage_to_spatial_arcmin(voltage_series):
    return voltage_series * ARC_MIN_PER_VOLT


def normalize_intensity(intensity_series):
    minimum = intensity_series.min()
    shifted = intensity_series - minimum
    maximum = shifted.max()
    if maximum <= 0:
        return shifted
    return shifted / maximum


def plot_profile(data, x_column, intensity_column, csv_path):
    x_values = convert_voltage_to_spatial_arcmin(data[x_column])
    y_values = normalize_intensity(data[intensity_column])

    figure, axis = plt.subplots()
    axis.plot(
        x_values,
        y_values,
        color="black",
        marker="o",
        markerfacecolor="white",
        markeredgewidth=1.1,
    )

    axis.set_xlabel(build_axis_label(x_column))
    axis.set_ylabel("Intensité")

    axis.xaxis.set_major_locator(MultipleLocator(10))
    axis.minorticks_on()
    axis.tick_params(axis="both", which="both", direction="in")

    for spine in axis.spines.values():
        spine.set_linewidth(1.2)

    figure.tight_layout()
    output_dir = Path("figure")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / f"{csv_path.stem}.pdf"
    figure.savefig(output_path, format="pdf", bbox_inches="tight")
    print(f"Figure PDF enregistrée dans : {output_path.resolve()}")
    plt.show()


def main():
    configure_plot_style()

    csv_path = Path(CSV_PATH).expanduser().resolve()
    if not csv_path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {csv_path}")

    data, x_column, intensity_column = load_profile(csv_path)
    plot_profile(data, x_column, intensity_column, csv_path)


if __name__ == "__main__":
    main()
