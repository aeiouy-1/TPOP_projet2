from pathlib import Path
import shutil

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


# User settings: only change these two variables.
CSV_PATH = Path("image_gray_area/fibre_100/0to1V/line_015.csv")
VOLT = False


VOLTS_PER_DEGREE = 0.5


def configure_plot_style():
    latex_is_available = shutil.which("latex") is not None

    plt.rcParams.update(
        {
            "figure.dpi": 160,
            "savefig.dpi": 300,
            "figure.figsize": (7.0, 4.6),
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

    x_column = data.columns[4]
    y_column = data.columns[6] 

    data[x_column] = pd.to_numeric(data[x_column], errors="coerce")
    data[y_column] = pd.to_numeric(data[y_column], errors="coerce")
    data[y_column] = (data[y_column]-np.min(data[y_column]))/np.max(data[y_column]-np.min(data[y_column]))
    data = data.dropna(subset=[x_column, y_column]).copy()

    if data.empty:
        raise ValueError("Aucune donnee exploitable n'a ete trouvee dans le CSV.")

    return data, x_column, y_column


def build_axis_label(x_column):
    axis_name = "X" if "X" in x_column.upper() else "Y" if "Y" in x_column.upper() else ""
    axis_suffix = f" {axis_name}" if axis_name else ""

    if VOLT:
        return f"Tension{axis_suffix} (V)"
    return f"Angle{axis_suffix} ($^\\circ$)"


def convert_x_values(voltage_series):
    if VOLT:
        return voltage_series
    return voltage_series / VOLTS_PER_DEGREE


def build_title(csv_path):
    profile_name = csv_path.stem.replace("_", " ")
    return f"Profil d'intensite - {profile_name}"


def plot_profile(data, x_column, y_column, csv_path):
    x_values = convert_x_values(data[x_column])
    y_values = data[y_column]

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
    axis.set_ylabel("Intensite (u.a.)")
    axis.set_title(build_title(csv_path), pad=12)

    axis.grid(True, which="major", color="#d0d0d0", linestyle="--", linewidth=0.8, alpha=0.8)
    axis.minorticks_on()
    axis.grid(True, which="minor", color="#ececec", linestyle=":", linewidth=0.5, alpha=0.7)

    for spine in axis.spines.values():
        spine.set_linewidth(1.2)

    figure.tight_layout()
    plt.show()


def main():
    configure_plot_style()

    csv_path = Path(CSV_PATH).expanduser().resolve()
    if not csv_path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {csv_path}")

    data, x_column, y_column = load_profile(csv_path)
    plot_profile(data, x_column, y_column, csv_path)


if __name__ == "__main__":
    main()
