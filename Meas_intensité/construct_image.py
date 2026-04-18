from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


# Remplace simplement ce chemin par le dossier créé par le scan image 2D.
SCAN_FOLDER = Path("/Users/arthurcare/TPOP_projet2/image_gray_area/fibre400/2026-04-17_18-03-55")

# Décommente et ajuste cette ligne si tu veux forcer le noir complet sous un seuil donné.
# BLACK_LEVEL = 250

# Décommente et ajuste cette liste si tu veux ignorer certaines lignes CSV.
# Exemple : line_017.csv et line_019.csv -> OMIT_LINE_NUMBERS = [17, 19]
# OMIT_LINE_NUMBERS = [00, 19]

# Mets True si tu veux sauvegarder automatiquement l'image reconstruite.
SAVE_PNG = True
OUTPUT_NAME = "reconstructed_image.png"


def load_scan_folder(scan_folder):
    if not scan_folder.exists():
        raise FileNotFoundError(f"Dossier introuvable : {scan_folder}")
    if not scan_folder.is_dir():
        raise NotADirectoryError(f"Le chemin indiqué n'est pas un dossier : {scan_folder}")

    line_files = sorted(scan_folder.glob("line_*.csv"))
    if not line_files:
        raise FileNotFoundError(f"Aucun fichier line_*.csv trouvé dans : {scan_folder}")

    omitted_line_numbers = get_omitted_line_numbers()
    if omitted_line_numbers:
        filtered_line_files = []
        skipped_files = []
        for line_file in line_files:
            line_number = extract_line_number(line_file)
            if line_number in omitted_line_numbers:
                skipped_files.append(line_file.name)
                continue
            filtered_line_files.append(line_file)

        line_files = filtered_line_files
        if skipped_files:
            print("Lignes omises :", ", ".join(skipped_files))
        if not line_files:
            raise ValueError("Toutes les lignes ont ete omises. Ajuste OMIT_LINE_NUMBERS.")

    frames = []
    required_columns = {
        "row_index",
        "column_index",
        "acquisition_index",
        "scan_direction",
        "x_voltage",
        "y_voltage",
        "intensity",
    }

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
    data["acquisition_index"] = pd.to_numeric(data["acquisition_index"], errors="raise").astype(int)
    data["x_voltage"] = pd.to_numeric(data["x_voltage"], errors="coerce")
    data["y_voltage"] = pd.to_numeric(data["y_voltage"], errors="coerce")
    data["intensity"] = pd.to_numeric(data["intensity"], errors="coerce")
    return data


def get_black_level():
    black_level = globals().get("BLACK_LEVEL", None)
    if black_level is None:
        return None

    try:
        return float(black_level)
    except (TypeError, ValueError) as exc:
        raise ValueError("BLACK_LEVEL doit être un nombre si tu l'utilises.") from exc


def extract_line_number(line_file):
    stem = line_file.stem
    if "_" not in stem:
        raise ValueError(f"Nom de fichier inattendu : {line_file.name}")

    try:
        return int(stem.split("_")[-1])
    except ValueError as exc:
        raise ValueError(f"Impossible d'extraire le numero de ligne depuis {line_file.name}") from exc


def get_omitted_line_numbers():
    omitted_line_numbers = globals().get("OMIT_LINE_NUMBERS", None)
    if omitted_line_numbers is None:
        return set()

    if not isinstance(omitted_line_numbers, (list, tuple, set)):
        raise ValueError("OMIT_LINE_NUMBERS doit etre une liste, un tuple ou un set de numeros de lignes.")

    normalized_numbers = set()
    for value in omitted_line_numbers:
        try:
            line_number = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("Chaque entree de OMIT_LINE_NUMBERS doit etre un entier.") from exc

        if line_number < 0:
            raise ValueError("Les numeros dans OMIT_LINE_NUMBERS doivent etre positifs ou nuls.")
        normalized_numbers.add(line_number)

    return normalized_numbers


def build_image_matrix(data):
    matrix = data.pivot_table(
        index="row_index",
        columns="column_index",
        values="intensity",
        aggfunc="mean",
    )

    ordered_rows = data.groupby("row_index")["y_voltage"].mean().sort_values().index.tolist()
    ordered_cols = data.groupby("column_index")["x_voltage"].mean().sort_values().index.tolist()
    matrix = matrix.reindex(index=ordered_rows, columns=ordered_cols)

    valid_values = pd.Series(matrix.to_numpy().ravel()).dropna()
    if valid_values.empty:
        raise ValueError("Aucune intensité exploitable n'a été trouvée dans les CSV.")

    black_level = get_black_level()
    fill_value = black_level if black_level is not None else float(valid_values.min())
    matrix = matrix.fillna(fill_value)
    return matrix, fill_value


def build_voltage_extent(data):
    x_positions = data.groupby("column_index")["x_voltage"].mean().sort_index()
    y_positions = data.groupby("row_index")["y_voltage"].mean().sort_index()
    return [
        float(x_positions.min()),
        float(x_positions.max()),
        float(y_positions.min()),
        float(y_positions.max()),
    ]


def plot_image(matrix, extent, scan_folder, display_min):
    figure, axis = plt.subplots(figsize=(8, 8))
    image = axis.imshow(
        matrix.to_numpy(),
        cmap="gray",
        origin="lower",
        interpolation="nearest",
        aspect="equal",
        extent=extent,
        vmin=display_min,
    )

    axis.set_title("Image reconstruite")
    axis.set_xlabel("Tension X (V)")
    axis.set_ylabel("Tension Y (V)")
    figure.colorbar(image, ax=axis, label="Intensité")
    figure.tight_layout()

    if SAVE_PNG:
        output_path = scan_folder / OUTPUT_NAME
        figure.savefig(output_path, dpi=200, bbox_inches="tight")
        print(f"Image sauvegardée dans : {output_path}")

    plt.show()


def main():
    scan_folder = SCAN_FOLDER.expanduser().resolve()
    print(f"Lecture du dossier : {scan_folder}")
    data = load_scan_folder(scan_folder)
    matrix, display_min = build_image_matrix(data)
    extent = build_voltage_extent(data)
    plot_image(matrix, extent, scan_folder, display_min)


if __name__ == "__main__":
    main()
