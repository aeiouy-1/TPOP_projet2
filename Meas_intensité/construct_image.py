from pathlib import Path
import shutil

import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
import pandas as pd


# Change only these three paths.
SCAN_FOLDER_1 = Path("image_gray_area/fibre_100/0to1V")
SCAN_FOLDER_2 = Path("image_gray_area/fibre400/2026-04-17_18-03-55")
SCAN_FOLDER_3 = Path("image_gray_area/fibre_600")


# Only the Y range between 0 V and 1 V is kept, even if the scan folder covers a larger range.
Y_MIN_V = 0.0
Y_MAX_V = 1.0


# Optional shared black threshold for the three scans.
# Comment this line out to use the minimum intensity found across all three scans.
BLACK_LEVEL = 300

SAVE_PNG = True
SAVE_PDF = True
OUTPUT_STEM = Path("figure/construct_image_comparison")


# Same spatial conversion used in profil_intensité.py and Spectre_to_RGB.py
CONV_V_TO_ANGLE_GALVOS = 0.5          # V / degree galvo
CONV_THETA = 0.4244683686             # degree spatial / degree galvo
ARC_MIN_PER_VOLT = (1 / CONV_V_TO_ANGLE_GALVOS) * CONV_THETA * 60


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
            "font.family": "serif",
            "mathtext.fontset": "cm",
            "text.usetex": latex_is_available,
        }
    )

    if not latex_is_available:
        plt.rcParams["font.serif"] = ["STIX Two Text", "Times New Roman", "DejaVu Serif"]


def get_scan_folders():
    scan_folders = [SCAN_FOLDER_1, SCAN_FOLDER_2, SCAN_FOLDER_3]
    resolved_folders = [Path(folder).expanduser().resolve() for folder in scan_folders]

    if len(resolved_folders) != 3:
        raise ValueError("Le script attend exactement trois chemins de scan.")

    return resolved_folders


def get_black_level():
    black_level = globals().get("BLACK_LEVEL", None)
    if black_level is None:
        return None

    try:
        return float(black_level)
    except (TypeError, ValueError) as exc:
        raise ValueError("BLACK_LEVEL doit etre un nombre si tu l'utilises.") from exc


def resolve_scan_folder(scan_folder):
    if not scan_folder.exists():
        raise FileNotFoundError(f"Dossier introuvable : {scan_folder}")
    if not scan_folder.is_dir():
        raise NotADirectoryError(f"Le chemin indique n'est pas un dossier : {scan_folder}")

    if any(scan_folder.glob("line_*.csv")):
        return scan_folder

    child_scan_folders = sorted(
        path for path in scan_folder.iterdir() if path.is_dir() and any(path.glob("line_*.csv"))
    )
    if len(child_scan_folders) == 1:
        return child_scan_folders[0]
    if len(child_scan_folders) > 1:
        raise ValueError(
            f"Plusieurs sous-dossiers de scan ont ete trouves dans {scan_folder}. "
            "Indique directement le bon dossier."
        )

    raise FileNotFoundError(f"Aucun fichier line_*.csv trouve dans : {scan_folder}")


def load_scan_folder(scan_folder):
    resolved_scan_folder = resolve_scan_folder(scan_folder)
    line_files = sorted(resolved_scan_folder.glob("line_*.csv"))

    required_columns = {"row_index", "column_index", "x_voltage", "y_voltage", "intensity"}
    frames = []

    for line_file in line_files:
        frame = pd.read_csv(line_file)
        missing_columns = required_columns.difference(frame.columns)
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"Colonnes manquantes dans {line_file.name} : {missing}")
        frames.append(frame)

    data = pd.concat(frames, ignore_index=True)
    data["row_index"] = pd.to_numeric(data["row_index"], errors="raise").astype(int)
    data["column_index"] = pd.to_numeric(data["column_index"], errors="raise").astype(int)
    data["x_voltage"] = pd.to_numeric(data["x_voltage"], errors="coerce")
    data["y_voltage"] = pd.to_numeric(data["y_voltage"], errors="coerce")
    data["intensity"] = pd.to_numeric(data["intensity"], errors="coerce")
    data = data.dropna(subset=["x_voltage", "y_voltage", "intensity"]).copy()

    filtered_data = filter_y_window(data, resolved_scan_folder)
    return resolved_scan_folder, filtered_data


def filter_y_window(data, scan_folder):
    voltage_tolerance = 1e-9
    y_mask = data["y_voltage"].between(Y_MIN_V - voltage_tolerance, Y_MAX_V + voltage_tolerance)
    filtered_data = data.loc[y_mask].copy()

    if filtered_data.empty:
        raise ValueError(
            f"Aucune ligne comprise entre {Y_MIN_V:.3f} V et {Y_MAX_V:.3f} V dans {scan_folder}."
        )

    return filtered_data


def build_image_matrix(data, fill_value):
    matrix = data.pivot_table(
        index="row_index",
        columns="column_index",
        values="intensity",
        aggfunc="mean",
    )

    ordered_rows = data.groupby("row_index")["y_voltage"].mean().sort_values().index.tolist()
    ordered_cols = data.groupby("column_index")["x_voltage"].mean().sort_values().index.tolist()
    matrix = matrix.reindex(index=ordered_rows, columns=ordered_cols)
    return matrix.fillna(fill_value)


def build_spatial_extent(data):
    x_positions = data.groupby("column_index")["x_voltage"].mean().sort_values()
    y_positions = data.groupby("row_index")["y_voltage"].mean().sort_values()

    return [
        float(x_positions.min() * ARC_MIN_PER_VOLT),
        float(x_positions.max() * ARC_MIN_PER_VOLT),
        float(y_positions.min() * ARC_MIN_PER_VOLT),
        float(y_positions.max() * ARC_MIN_PER_VOLT),
    ]


def compute_common_display_bounds(scan_payloads):
    all_intensities = pd.concat(
        [payload["data"]["intensity"] for payload in scan_payloads],
        ignore_index=True,
    )
    valid_values = pd.to_numeric(all_intensities, errors="coerce").dropna()
    if valid_values.empty:
        raise ValueError("Aucune intensite exploitable n'a ete trouvee dans les trois scans.")

    black_level = get_black_level()
    display_min = black_level if black_level is not None else float(valid_values.min())
    display_max = float(valid_values.max())

    if display_max <= display_min:
        display_max = display_min + 1.0

    return display_min, display_max


def build_scan_payloads():
    scan_payloads = []
    for scan_folder in get_scan_folders():
        resolved_scan_folder, data = load_scan_folder(scan_folder)
        scan_payloads.append(
            {
                "requested_folder": scan_folder,
                "scan_folder": resolved_scan_folder,
                "data": data,
            }
        )
    return scan_payloads


def build_output_paths(payload, index):
    output_stem = OUTPUT_STEM.expanduser()
    output_stem.parent.mkdir(parents=True, exist_ok=True)

    safe_scan_name = payload["scan_folder"].name.replace(" ", "_")
    figure_name = f"{output_stem.stem}_{index}_{safe_scan_name}"
    png_path = output_stem.parent / f"{figure_name}.png"
    pdf_path = output_stem.parent / f"{figure_name}.pdf"
    return png_path, pdf_path


def save_figure(figure, payload, index):
    png_path, pdf_path = build_output_paths(payload, index)

    if SAVE_PNG:
        figure.savefig(png_path, format="png", bbox_inches="tight")
        print(f"Figure PNG enregistree dans : {png_path.resolve()}")

    if SAVE_PDF:
        figure.savefig(pdf_path, format="pdf", bbox_inches="tight")
        print(f"Figure PDF enregistree dans : {pdf_path.resolve()}")


def plot_single_scan(payload, display_min, display_max):
    figure, axis = plt.subplots(
        1,
        1,
        figsize=(10.5, 5.4),
        constrained_layout=False,
    )
    figure.subplots_adjust(left=0.13, right=0.99, bottom=0.14, top=0.96)

    matrix = build_image_matrix(payload["data"], fill_value=display_min)
    extent = build_spatial_extent(payload["data"])

    axis.imshow(
        matrix.to_numpy(),
        cmap="gray",
        origin="lower",
        interpolation="nearest",
        aspect="equal",
        extent=extent,
        vmin=display_min,
        vmax=display_max,
    )

    axis.set_xlabel(r"Angle d'incidence ($\alpha_x$) [']")
    axis.set_ylabel(r"Angle d'incidence ($\alpha_y$) [']")
    axis.xaxis.set_major_locator(MultipleLocator(10))
    axis.yaxis.set_major_locator(MultipleLocator(10))
    axis.minorticks_on()
    axis.tick_params(axis="both", which="both", direction="in", pad=4)

    for spine in axis.spines.values():
        spine.set_linewidth(1.2)

    return figure


def main():
    configure_plot_style()

    scan_payloads = build_scan_payloads()
    for payload in scan_payloads:
        y_values = payload["data"]["y_voltage"]
        print(
            "Scan charge : "
            f"{payload['scan_folder']} | "
            f"lignes conservees entre {float(y_values.min()):.3f} V et {float(y_values.max()):.3f} V"
        )

    display_min, display_max = compute_common_display_bounds(scan_payloads)
    for index, payload in enumerate(scan_payloads, start=1):
        figure = plot_single_scan(payload, display_min, display_max)
        save_figure(figure, payload, index)
        plt.show()
        plt.close(figure)


if __name__ == "__main__":
    main()
