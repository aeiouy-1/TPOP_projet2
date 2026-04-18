import csv
import math
import os
import time
from datetime import datetime

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
import serial
import serial.tools.list_ports
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from galvos import RedPitayaGalvos


class ScannerApp:
    BG = '#1e1e2e'
    BG2 = '#181825'
    BLUE = '#89b4fa'
    RED = '#f38ba8'
    GRN = '#a6e3a1'
    YLW = '#f9e2af'
    FG = '#cdd6f4'

    def __init__(self, root):
        self.root = root
        self.root.title("Contrôle Galvos & Acquisition Intensité")
        self.root.configure(bg=self.BG)
        self.root.minsize(1100, 780)

        # Contrôleurs
        self.galvos = RedPitayaGalvos()
        self.ser = None

        # Paramètres généraux
        self.voltage_min = -1.0
        self.voltage_max = 1.0
        self.line_voltage_step = 0.005
        self.image_voltage_step = 0.02
        self.image_point_delay_ms = 100
        self.image_y_start = self.voltage_min
        self.image_y_end = self.voltage_max

        # États de scan
        self.is_scanning = False
        self.scan_mode = "line_1d"
        self.scan_with_measurement = True
        self.active_scan_label = "Scan + mesure"
        self.scan_axis = tk.StringVar(value="X")
        self.current_scan_voltage = self.voltage_min
        self.current_point_x = self.voltage_min
        self.current_point_y = self.voltage_min

        # Données 1D / aperçu de la ligne courante
        self.v_data = []
        self.sig_data = []

        # Valeurs fixes pendant le scan 1D
        self.fixed_scan_x = 0.0
        self.fixed_scan_y = 0.0

        # Progression
        self.total_scan_points = 0
        self.completed_scan_points = 0
        self.scan_progress_var = tk.DoubleVar(value=0.0)
        self.scan_progress_text = tk.StringVar(value="Progression : en attente")

        # Scan image 2D
        self.image_total_rows = 0
        self.image_total_cols = 0
        self.image_row_index = 0
        self.image_col_index = 0
        self.image_direction = 1
        self.image_x_positions = []
        self.image_y_positions = []
        self.image_line_records = []
        self.image_output_dir = None
        self.image_folder_text = tk.StringVar(value="Dossier image 2D : aucun")

        self._build_ui()

    def _build_ui(self):
        style = ttk.Style(self.root)
        style.configure(
            'Scan.Horizontal.TProgressbar',
            troughcolor=self.BG2,
            background=self.BLUE,
            bordercolor=self.BG2,
            lightcolor=self.BLUE,
            darkcolor=self.BLUE
        )

        top_frame = tk.Frame(self.root, bg=self.BG2, pady=10)
        top_frame.pack(fill='x')

        tk.Label(
            top_frame,
            text="Red Pitaya (Galvos):",
            bg=self.BG2,
            fg=self.BLUE,
            font=('', 10, 'bold')
        ).grid(row=0, column=0, padx=10)
        self.lbl_rp_stat = tk.Label(top_frame, text="Déconnecté", bg=self.BG2, fg=self.RED)
        self.lbl_rp_stat.grid(row=0, column=1)
        self.btn_conn_rp = tk.Button(top_frame, text="Connecter RP", command=self.connect_rp)
        self.btn_conn_rp.grid(row=0, column=2, padx=10)

        tk.Label(
            top_frame,
            text="Arduino (Détecteur):",
            bg=self.BG2,
            fg=self.BLUE,
            font=('', 10, 'bold')
        ).grid(row=0, column=3, padx=10)
        self.cbPort = ttk.Combobox(top_frame, width=10, state='readonly')
        self.cbPort.grid(row=0, column=4)
        ttk.Button(top_frame, text="↻", width=3, command=self._refresh_ports).grid(row=0, column=5)

        self.lbl_ard_stat = tk.Label(top_frame, text="Déconnecté", bg=self.BG2, fg=self.RED)
        self.lbl_ard_stat.grid(row=0, column=6, padx=10)
        self.btn_conn_ard = tk.Button(top_frame, text="Connecter Arduino", command=self.connect_arduino)
        self.btn_conn_ard.grid(row=0, column=7)

        self._refresh_ports()

        ctrl_frame = tk.Frame(self.root, bg=self.BG, pady=10)
        ctrl_frame.pack(fill='x', padx=10)

        frame_manuel = tk.LabelFrame(
            ctrl_frame,
            text=" Contrôle Manuel ",
            bg=self.BG,
            fg=self.FG,
            font=('', 11, 'bold')
        )
        frame_manuel.pack(side='left', fill='both', expand=True, padx=(0, 5))

        self.scale_x = tk.Scale(
            frame_manuel,
            from_=self.voltage_min,
            to=self.voltage_max,
            resolution=0.01,
            orient=tk.HORIZONTAL,
            label="Position X (Volts)",
            bg=self.BG,
            fg=self.FG,
            highlightthickness=0,
            command=self.update_manual_position
        )
        self.scale_x.pack(fill='x', padx=10, pady=5)

        self.scale_y = tk.Scale(
            frame_manuel,
            from_=self.voltage_min,
            to=self.voltage_max,
            resolution=0.01,
            orient=tk.HORIZONTAL,
            label="Position Y (Volts)",
            bg=self.BG,
            fg=self.FG,
            highlightthickness=0,
            command=self.update_manual_position
        )
        self.scale_y.pack(fill='x', padx=10, pady=5)

        self.btn_zero = tk.Button(frame_manuel, text="Remettre à Zéro", bg='salmon', command=self.reset_galvos)
        self.btn_zero.pack(pady=5)

        frame_scan = tk.LabelFrame(
            ctrl_frame,
            text=" Balayages ",
            bg=self.BG,
            fg=self.FG,
            font=('', 11, 'bold')
        )
        frame_scan.pack(side='left', fill='both', expand=True, padx=(5, 0))

        self.rb_scan_x = tk.Radiobutton(
            frame_scan,
            text="Scan 1D sur l'axe X (Y maintenu fixe)",
            variable=self.scan_axis,
            value="X",
            bg=self.BG,
            fg=self.FG,
            selectcolor=self.BG2
        )
        self.rb_scan_x.pack(anchor='w', padx=10, pady=2)

        self.rb_scan_y = tk.Radiobutton(
            frame_scan,
            text="Scan 1D sur l'axe Y (X maintenu fixe)",
            variable=self.scan_axis,
            value="Y",
            bg=self.BG,
            fg=self.FG,
            selectcolor=self.BG2
        )
        self.rb_scan_y.pack(anchor='w', padx=10, pady=2)

        frame_param = tk.Frame(frame_scan, bg=self.BG)
        frame_param.pack(anchor='w', padx=10, pady=5)
        tk.Label(frame_param, text="Temps par point 1D (s) :", bg=self.BG, fg=self.FG).pack(side='left')
        self.spin_delay = ttk.Spinbox(frame_param, from_=0.1, to=5.0, increment=0.1, width=8)
        self.spin_delay.set(0.5)
        self.spin_delay.pack(side='left', padx=5)

        frame_fixed = tk.Frame(frame_scan, bg=self.BG)
        frame_fixed.pack(anchor='w', padx=10, pady=5)

        tk.Label(frame_fixed, text="Y fixe pendant scan X (V) :", bg=self.BG, fg=self.FG).grid(row=0, column=0, sticky='w', pady=2)
        self.spin_fixed_y = ttk.Spinbox(frame_fixed, from_=self.voltage_min, to=self.voltage_max, increment=0.01, width=8)
        self.spin_fixed_y.set("0.00")
        self.spin_fixed_y.grid(row=0, column=1, padx=(8, 0), pady=2)

        tk.Label(frame_fixed, text="X fixe pendant scan Y (V) :", bg=self.BG, fg=self.FG).grid(row=1, column=0, sticky='w', pady=2)
        self.spin_fixed_x = ttk.Spinbox(frame_fixed, from_=self.voltage_min, to=self.voltage_max, increment=0.01, width=8)
        self.spin_fixed_x.set("0.00")
        self.spin_fixed_x.grid(row=1, column=1, padx=(8, 0), pady=2)

        frame_image_info = tk.Frame(frame_scan, bg=self.BG)
        frame_image_info.pack(fill='x', padx=10, pady=(8, 4))
        tk.Label(
            frame_image_info,
            text=(
                f"Scan image 2D : X reste balayé de {self.voltage_min:.2f} V à {self.voltage_max:.2f} V. "
                f"Choisis ci-dessous le début/fin en Y et le pas pixel commun X/Y. "
                f"Acquisition toutes les {self.image_point_delay_ms / 1000:.1f} s."
            ),
            bg=self.BG,
            fg=self.FG,
            justify='left',
            wraplength=430
        ).pack(anchor='w')

        frame_image_param = tk.Frame(frame_scan, bg=self.BG)
        frame_image_param.pack(anchor='w', padx=10, pady=5)

        tk.Label(frame_image_param, text="Y début scan 2D (V) :", bg=self.BG, fg=self.FG).grid(row=0, column=0, sticky='w', pady=2)
        self.spin_image_y_start = ttk.Spinbox(frame_image_param, from_=self.voltage_min, to=self.voltage_max, increment=0.01, width=8)
        self.spin_image_y_start.set(f"{self.image_y_start:.2f}")
        self.spin_image_y_start.grid(row=0, column=1, padx=(8, 0), pady=2)

        tk.Label(frame_image_param, text="Y fin scan 2D (V) :", bg=self.BG, fg=self.FG).grid(row=1, column=0, sticky='w', pady=2)
        self.spin_image_y_end = ttk.Spinbox(frame_image_param, from_=self.voltage_min, to=self.voltage_max, increment=0.01, width=8)
        self.spin_image_y_end.set(f"{self.image_y_end:.2f}")
        self.spin_image_y_end.grid(row=1, column=1, padx=(8, 0), pady=2)

        tk.Label(frame_image_param, text="Pas pixel scan 2D (V) :", bg=self.BG, fg=self.FG).grid(row=2, column=0, sticky='w', pady=2)
        self.spin_image_step = ttk.Spinbox(frame_image_param, from_=0.001, to=1.0, increment=0.001, width=8)
        self.spin_image_step.set(f"{self.image_voltage_step:.3f}")
        self.spin_image_step.grid(row=2, column=1, padx=(8, 0), pady=2)

        buttons_frame = tk.Frame(frame_scan, bg=self.BG)
        buttons_frame.pack(pady=10)

        self.btn_start_scan = tk.Button(
            buttons_frame,
            text="▶ Scan 1D + mesure",
            bg=self.GRN,
            font=('', 10, 'bold'),
            command=self.start_scan
        )
        self.btn_start_scan.grid(row=0, column=0, padx=5)

        self.btn_manual_scan = tk.Button(
            buttons_frame,
            text="↻ Scan 1D manuel",
            bg=self.YLW,
            font=('', 10, 'bold'),
            command=self.start_manual_scan
        )
        self.btn_manual_scan.grid(row=0, column=1, padx=5)

        self.btn_image_scan = tk.Button(
            buttons_frame,
            text="🖼 Scan image 2D",
            bg=self.BLUE,
            font=('', 10, 'bold'),
            command=self.start_image_scan
        )
        self.btn_image_scan.grid(row=0, column=2, padx=5)

        self.btn_stop_scan = tk.Button(
            buttons_frame,
            text="⏹ Stopper",
            bg=self.RED,
            font=('', 10, 'bold'),
            command=self.stop_scan
        )
        self.btn_stop_scan.grid(row=0, column=3, padx=5)

        self.btn_save = tk.Button(
            buttons_frame,
            text="💾 Exporter CSV 1D",
            bg=self.BLUE,
            font=('', 10, 'bold'),
            command=self._save_data
        )
        self.btn_save.grid(row=0, column=4, padx=5)

        progress_frame = tk.Frame(frame_scan, bg=self.BG)
        progress_frame.pack(fill='x', padx=10, pady=(0, 10))

        tk.Label(progress_frame, textvariable=self.scan_progress_text, bg=self.BG, fg=self.FG).pack(anchor='w')
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            orient=tk.HORIZONTAL,
            mode='determinate',
            maximum=100,
            variable=self.scan_progress_var,
            style='Scan.Horizontal.TProgressbar'
        )
        self.progress_bar.pack(fill='x', pady=(4, 4))
        tk.Label(progress_frame, textvariable=self.image_folder_text, bg=self.BG, fg=self.FG, wraplength=450, justify='left').pack(anchor='w')

        self.fig, self.ax = plt.subplots(figsize=(8, 4), facecolor=self.BG)
        self._configure_plot(scan_mode="line_1d", axe="X", with_measurement=True)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(fill='both', expand=True, padx=10, pady=10)

    # --- Connexions ---
    def connect_rp(self):
        success, msg = self.galvos.connect()
        if success:
            self.lbl_rp_stat.config(text="Connecté", fg=self.GRN)
            self.btn_conn_rp.config(state=tk.DISABLED)
        else:
            messagebox.showerror("Erreur Galvos", msg)

    def _refresh_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.cbPort['values'] = ports
        self.cbPort.set(ports[0] if ports else "")

    def connect_arduino(self):
        if self.ser is None or not self.ser.is_open:
            try:
                port = self.cbPort.get().strip()
                if not port:
                    messagebox.showwarning("Arduino", "Sélectionnez un port série avant de connecter l'Arduino.")
                    return

                self.ser = serial.Serial(port, 115200, timeout=1.0)
                time.sleep(2)
                self.lbl_ard_stat.config(text="Connecté", fg=self.GRN)
                self.btn_conn_ard.config(text="Déconnecter")
            except Exception as exc:
                messagebox.showerror("Erreur Arduino", str(exc))
        else:
            self.ser.close()
            self.ser = None
            self.lbl_ard_stat.config(text="Déconnecté", fg=self.RED)
            self.btn_conn_ard.config(text="Connecter Arduino")

    # --- Contrôle manuel ---
    def update_manual_position(self, event=None):
        if self.galvos.connected and not self.is_scanning:
            self.galvos.set_position(self.scale_x.get(), self.scale_y.get())

    def reset_galvos(self):
        self.scale_x.set(0)
        self.scale_y.set(0)
        if self.galvos.connected and not self.is_scanning:
            self.galvos.set_position(0.0, 0.0)

    # --- Aides scan ---
    def _compute_total_points(self, step):
        if step <= 0:
            return 0
        return int(round((self.voltage_max - self.voltage_min) / step)) + 1

    def _update_scan_progress(self, state="en cours"):
        if self.total_scan_points <= 0:
            self.scan_progress_var.set(0.0)
            self.scan_progress_text.set("Progression : en attente")
            return

        self.completed_scan_points = min(self.completed_scan_points, self.total_scan_points)
        percent = (self.completed_scan_points / self.total_scan_points) * 100
        extra = ""
        if self.scan_mode == "image_2d" and self.image_total_rows > 0:
            current_line = min(self.image_row_index + 1, self.image_total_rows)
            extra = f" | ligne {current_line}/{self.image_total_rows}"

        self.scan_progress_var.set(percent)
        self.scan_progress_text.set(
            f"{self.active_scan_label} {state} : {self.completed_scan_points}/{self.total_scan_points} points ({percent:.1f}%){extra}"
        )

    def _read_voltage_input(self, raw_value, axis_name):
        try:
            value = float(raw_value.replace(',', '.'))
        except ValueError as exc:
            raise ValueError(f"La valeur fixe pour l'axe {axis_name} doit être un nombre valide.") from exc

        if not self.voltage_min <= value <= self.voltage_max:
            raise ValueError(
                f"La valeur fixe pour l'axe {axis_name} doit être comprise entre {self.voltage_min:.2f} V et {self.voltage_max:.2f} V."
            )
        return value

    def _load_scan_fixed_values(self):
        try:
            self.fixed_scan_y = self._read_voltage_input(self.spin_fixed_y.get().strip(), "Y")
            self.fixed_scan_x = self._read_voltage_input(self.spin_fixed_x.get().strip(), "X")
        except ValueError as exc:
            messagebox.showwarning("Valeur fixe invalide", str(exc))
            return False
        return True

    def _read_positive_step_input(self, raw_value, field_name):
        try:
            value = float(raw_value.replace(',', '.'))
        except ValueError as exc:
            raise ValueError(f"La valeur pour {field_name} doit être un nombre valide.") from exc

        if value <= 0:
            raise ValueError(f"La valeur pour {field_name} doit être strictement positive.")
        return value

    def _build_scan_positions(self, start, end, step, axis_name):
        distance = abs(end - start)
        if math.isclose(distance, 0.0, abs_tol=1e-9):
            return [round(start, 10)]

        interval_count = distance / step
        rounded_interval_count = round(interval_count)
        if not math.isclose(interval_count, rounded_interval_count, rel_tol=1e-9, abs_tol=1e-6):
            raise ValueError(
                f"L'intervalle de l'axe {axis_name} doit être un multiple exact du pas pixel pour conserver une grille reguliere."
            )

        direction = 1 if end >= start else -1
        positions = [round(start + (direction * index * step), 10) for index in range(int(rounded_interval_count) + 1)]
        positions[-1] = round(end, 10)
        return positions

    def _load_image_scan_settings(self):
        try:
            self.image_y_start = self._read_voltage_input(self.spin_image_y_start.get().strip(), "Y debut 2D")
            self.image_y_end = self._read_voltage_input(self.spin_image_y_end.get().strip(), "Y fin 2D")
            self.image_voltage_step = self._read_positive_step_input(self.spin_image_step.get().strip(), "le pas pixel 2D")
            self.image_x_positions = self._build_scan_positions(self.voltage_min, self.voltage_max, self.image_voltage_step, "X")
            self.image_y_positions = self._build_scan_positions(self.image_y_start, self.image_y_end, self.image_voltage_step, "Y")
        except ValueError as exc:
            messagebox.showwarning("Parametres 2D invalides", str(exc))
            return False
        return True

    def _get_line_delay_ms(self):
        try:
            return int(float(self.spin_delay.get().replace(',', '.')) * 1000)
        except ValueError:
            return 500

    def _get_remaining_delay_ms(self, overhead_ms, target_total_ms):
        delay_ms = target_total_ms - overhead_ms
        return 10 if delay_ms < 10 else delay_ms

    def _set_scan_controls_state(self, scanning):
        normal_state = tk.DISABLED if scanning else tk.NORMAL
        self.btn_start_scan.config(state=normal_state)
        self.btn_manual_scan.config(state=normal_state)
        self.btn_image_scan.config(state=normal_state)
        self.scale_x.config(state=normal_state)
        self.scale_y.config(state=normal_state)
        self.spin_delay.config(state=normal_state)
        self.spin_fixed_x.config(state=normal_state)
        self.spin_fixed_y.config(state=normal_state)
        self.spin_image_y_start.config(state=normal_state)
        self.spin_image_y_end.config(state=normal_state)
        self.spin_image_step.config(state=normal_state)
        self.rb_scan_x.config(state=normal_state)
        self.rb_scan_y.config(state=normal_state)

    def _refresh_plot(self):
        self.ln.set_data(self.v_data, self.sig_data)
        if self.v_data and any(not math.isnan(value) for value in self.sig_data):
            self.ax.relim()
            self.ax.autoscale_view()
        self.canvas.draw_idle()

    def _clear_plot_data(self):
        self.v_data.clear()
        self.sig_data.clear()
        self.ln.set_data([], [])
        self.canvas.draw_idle()

    def _configure_plot(self, scan_mode="line_1d", axe="X", with_measurement=True):
        self.ax.clear()
        self.ax.set_facecolor(self.BG2)
        self.ax.tick_params(colors='white')
        self.ax.grid(True, color='#313244', ls='--')

        if scan_mode == "image_2d":
            self.ax.set_xlabel('Tension Axe X (Volts)', color='white')
            self.ax.set_ylabel('Intensité (ADC)', color='white')
            self.ax.set_title('Scan image 2D - ligne courante', color='white')
            self.ax.set_xlim(self.voltage_min, self.voltage_max)
        else:
            self.ax.set_xlabel(f'Tension Axe {axe} (Volts)', color='white')
            if with_measurement:
                self.ax.set_ylabel('Intensité (ADC)', color='white')
                self.ax.set_title('Scan 1D avec acquisition', color='white')
            else:
                self.ax.set_ylabel('Aucune mesure', color='white')
                self.ax.set_title('Scan 1D manuel', color='white')

        self.ln, = self.ax.plot([], [], color=self.RED, lw=1.5, marker='o', markersize=3)

    def _prepare_measurement_scan(self):
        if self.ser is None or not self.ser.is_open:
            messagebox.showwarning("Attention", "Connectez l'Arduino pour lancer ce scan.")
            return False
        return True

    def _create_image_output_dir(self):
        base_dir = os.path.join(os.getcwd(), "image_gray_area")
        os.makedirs(base_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        folder = os.path.join(base_dir, timestamp)
        suffix = 1
        while os.path.exists(folder):
            folder = os.path.join(base_dir, f"{timestamp}_{suffix:02d}")
            suffix += 1

        os.makedirs(folder, exist_ok=False)
        return folder

    def _write_image_metadata(self):
        if not self.image_output_dir:
            return

        metadata_path = os.path.join(self.image_output_dir, "scan_metadata.csv")
        with open(metadata_path, 'w', newline='') as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "created_at",
                    "scan_type",
                    "x_start",
                    "x_end",
                    "y_start",
                    "y_end",
                    "step_voltage",
                    "point_delay_s",
                    "x_points",
                    "y_points",
                    "scan_pattern",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                    "scan_type": "image_gray_area",
                    "x_start": f"{self.image_x_positions[0]:.3f}",
                    "x_end": f"{self.image_x_positions[-1]:.3f}",
                    "y_start": f"{self.image_y_positions[0]:.3f}",
                    "y_end": f"{self.image_y_positions[-1]:.3f}",
                    "step_voltage": f"{self.image_voltage_step:.3f}",
                    "point_delay_s": f"{self.image_point_delay_ms / 1000:.3f}",
                    "x_points": self.image_total_cols,
                    "y_points": self.image_total_rows,
                    "scan_pattern": "serpentine",
                }
            )

    def _save_current_image_line(self):
        if not self.image_output_dir or not self.image_line_records:
            return

        path = os.path.join(self.image_output_dir, f"line_{self.image_row_index:03d}.csv")
        with open(path, 'w', newline='') as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "row_index",
                    "column_index",
                    "acquisition_index",
                    "scan_direction",
                    "x_voltage",
                    "y_voltage",
                    "intensity",
                ],
            )
            writer.writeheader()
            writer.writerows(self.image_line_records)

    def _get_current_line_position(self):
        if self.scan_axis.get() == "X":
            return self.current_scan_voltage, self.fixed_scan_y
        return self.fixed_scan_x, self.current_scan_voltage

    def _get_current_image_position(self):
        if self.image_direction == 1:
            x_voltage = self.image_x_positions[self.image_col_index]
        else:
            x_voltage = self.image_x_positions[-1 - self.image_col_index]

        y_voltage = self.image_y_positions[self.image_row_index]
        return x_voltage, y_voltage

    # --- Démarrage des scans ---
    def start_scan(self):
        self._start_line_scan(with_measurement=True)

    def start_manual_scan(self):
        self._start_line_scan(with_measurement=False)

    def start_image_scan(self):
        if not self.galvos.connected:
            messagebox.showwarning("Attention", "Connectez le Red Pitaya avant de lancer un scan image 2D.")
            return

        if not self._prepare_measurement_scan():
            return

        if not self._load_image_scan_settings():
            return

        self.scan_mode = "image_2d"
        self.scan_with_measurement = True
        self.active_scan_label = "Scan image 2D"
        self.total_scan_points = len(self.image_x_positions) * len(self.image_y_positions)
        self.completed_scan_points = 0
        self.image_total_cols = len(self.image_x_positions)
        self.image_total_rows = len(self.image_y_positions)
        self.image_row_index = 0
        self.image_col_index = 0
        self.image_direction = 1
        self.image_line_records = []
        self.image_output_dir = self._create_image_output_dir()
        self.image_folder_text.set(f"Dossier image 2D : {self.image_output_dir}")
        self._write_image_metadata()

        self.is_scanning = True
        self.current_point_x = self.image_x_positions[0]
        self.current_point_y = self.image_y_positions[0]
        self.scale_x.set(self.current_point_x)
        self.scale_y.set(self.current_point_y)
        self._clear_plot_data()
        self._configure_plot(scan_mode="image_2d")
        self._update_scan_progress(state="en cours")
        self._set_scan_controls_state(scanning=True)
        self.scan_step()

    def _start_line_scan(self, with_measurement):
        if not self.galvos.connected:
            messagebox.showwarning("Attention", "Connectez le Red Pitaya avant de lancer un scan.")
            return

        if with_measurement and not self._prepare_measurement_scan():
            return

        if not self._load_scan_fixed_values():
            return

        self.scan_mode = "line_1d"
        self.scan_with_measurement = with_measurement
        self.active_scan_label = "Scan 1D + mesure" if with_measurement else "Scan 1D manuel"
        self.current_scan_voltage = self.voltage_min
        self.total_scan_points = self._compute_total_points(self.line_voltage_step)
        self.completed_scan_points = 0
        self.is_scanning = True

        self._clear_plot_data()

        axe = self.scan_axis.get()
        if axe == "X":
            self.scale_y.set(self.fixed_scan_y)
        else:
            self.scale_x.set(self.fixed_scan_x)

        self._configure_plot(scan_mode="line_1d", axe=axe, with_measurement=with_measurement)
        self._update_scan_progress(state="en cours")
        self._set_scan_controls_state(scanning=True)
        self.scan_step()

    # --- Boucle de scan ---
    def scan_step(self):
        if not self.is_scanning:
            return

        if self.scan_mode == "image_2d":
            self.current_point_x, self.current_point_y = self._get_current_image_position()
        else:
            self.current_point_x, self.current_point_y = self._get_current_line_position()

        self.scale_x.set(self.current_point_x)
        self.scale_y.set(self.current_point_y)
        self.galvos.set_position(self.current_point_x, self.current_point_y)

        if self.scan_mode == "line_1d" and not self.scan_with_measurement:
            self.root.after(50, self.finish_manual_step)
        else:
            self.root.after(50, self.read_intensity)

    def read_intensity(self):
        if not self.is_scanning:
            return

        if self.ser is None or not self.ser.is_open:
            self.stop_scan(interrupted=True)
            messagebox.showwarning("Arduino", "La connexion Arduino a été perdue pendant le scan.")
            return

        try:
            self.ser.reset_input_buffer()
            self.ser.write(b'M')
        except serial.SerialException as exc:
            self.stop_scan(interrupted=True)
            messagebox.showwarning("Arduino", f"Erreur de communication Arduino : {exc}")
            return

        self.root.after(20, self.process_serial_and_loop)

    def process_serial_and_loop(self):
        if not self.is_scanning:
            return

        if self.ser is None or not self.ser.is_open:
            self.stop_scan(interrupted=True)
            messagebox.showwarning("Arduino", "La connexion Arduino a été perdue pendant le scan.")
            return

        measured_value = None
        try:
            has_data = self.ser.in_waiting > 0
        except serial.SerialException as exc:
            self.stop_scan(interrupted=True)
            messagebox.showwarning("Arduino", f"Erreur de communication Arduino : {exc}")
            return

        if has_data:
            try:
                measured_value = float(self.ser.readline().decode('utf-8').strip())
            except ValueError:
                measured_value = math.nan if self.scan_mode == "image_2d" else None
        elif self.scan_mode == "image_2d":
            measured_value = math.nan

        if self.scan_mode == "image_2d":
            self._finish_image_scan_point(measured_value, overhead_ms=70)
        else:
            self._finish_line_scan_point(measured_value, overhead_ms=70)

    def finish_manual_step(self):
        if not self.is_scanning or self.scan_mode != "line_1d":
            return

        self._finish_line_scan_point(overhead_ms=50)

    def _finish_line_scan_point(self, measured_value=None, overhead_ms=0):
        if measured_value is not None:
            self.v_data.append(self.current_scan_voltage)
            self.sig_data.append(measured_value)
            self._refresh_plot()

        self.completed_scan_points = min(self.completed_scan_points + 1, self.total_scan_points)
        self._update_scan_progress(state="en cours")
        self.current_scan_voltage = self.voltage_min + (self.completed_scan_points * self.line_voltage_step)

        if self.completed_scan_points < self.total_scan_points:
            delay_ms = self._get_remaining_delay_ms(overhead_ms, self._get_line_delay_ms())
            self.root.after(delay_ms, self.scan_step)
            return

        self.stop_scan(finished=True)
        mode = "avec mesure" if self.scan_with_measurement else "manuel"
        messagebox.showinfo("Fini", f"Le balayage 1D {mode} est terminé.")

    def _finish_image_scan_point(self, measured_value, overhead_ms=0):
        if measured_value is None:
            measured_value = math.nan

        acquisition_index = self.image_col_index
        if self.image_direction == 1:
            column_index = acquisition_index
            direction = "forward"
        else:
            column_index = self.image_total_cols - 1 - acquisition_index
            direction = "reverse"

        self.image_line_records.append(
            {
                "row_index": self.image_row_index,
                "column_index": column_index,
                "acquisition_index": acquisition_index,
                "scan_direction": direction,
                "x_voltage": f"{self.current_point_x:.3f}",
                "y_voltage": f"{self.current_point_y:.3f}",
                "intensity": measured_value,
            }
        )

        self.v_data.append(self.current_point_x)
        self.sig_data.append(measured_value)
        self._refresh_plot()

        self.completed_scan_points = min(self.completed_scan_points + 1, self.total_scan_points)
        self._update_scan_progress(state="en cours")
        self.image_col_index += 1

        if self.image_col_index < self.image_total_cols:
            delay_ms = self._get_remaining_delay_ms(overhead_ms, self.image_point_delay_ms)
            self.root.after(delay_ms, self.scan_step)
            return

        self._save_current_image_line()

        if self.image_row_index + 1 < self.image_total_rows:
            self.image_row_index += 1
            self.image_col_index = 0
            self.image_direction *= -1
            self.image_line_records = []
            self._clear_plot_data()
            delay_ms = self._get_remaining_delay_ms(overhead_ms, self.image_point_delay_ms)
            self.root.after(delay_ms, self.scan_step)
            return

        self.stop_scan(finished=True)
        messagebox.showinfo(
            "Fini",
            f"Le scan image 2D est terminé.\nLes lignes CSV sont enregistrées dans :\n{self.image_output_dir}",
        )

    def stop_scan(self, finished=False, interrupted=False):
        was_scanning = self.is_scanning
        self.is_scanning = False
        self._set_scan_controls_state(scanning=False)
        self.update_manual_position()

        if self.total_scan_points > 0:
            if finished:
                self.completed_scan_points = self.total_scan_points
                self._update_scan_progress(state="terminé")
            elif interrupted:
                self._update_scan_progress(state="interrompu")
            elif was_scanning:
                self._update_scan_progress(state="arrêté")

    # --- Sauvegarde 1D ---
    def _save_data(self):
        if self.scan_mode == "image_2d":
            if self.image_output_dir:
                messagebox.showinfo(
                    "Scan image 2D",
                    f"Le scan image 2D s'enregistre automatiquement ligne par ligne dans :\n{self.image_output_dir}",
                )
            else:
                messagebox.showinfo("Scan image 2D", "Aucun dossier de scan image 2D n'est disponible pour le moment.")
            return

        if not self.v_data:
            messagebox.showinfo("Vide", "Aucune donnée 1D à sauvegarder.")
            return

        filename = simpledialog.askstring("Sauvegarde", "Nom du fichier CSV (ex: profil_spatial) :")
        if not filename:
            return
        if not filename.endswith('.csv'):
            filename += '.csv'

        folder = "donnees_scan"
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, filename)

        try:
            with open(path, 'w', newline='') as handle:
                writer = csv.writer(handle)
                axe = self.scan_axis.get()
                writer.writerow([f"Tension_{axe}(V)", "Intensite"])
                for voltage, intensity in zip(self.v_data, self.sig_data):
                    writer.writerow([f"{voltage:.3f}", intensity])
            messagebox.showinfo("Succès", f"Fichier enregistré dans {path}")
        except Exception as exc:
            messagebox.showerror("Erreur", f"Échec de l'enregistrement : {exc}")


if __name__ == "__main__":
    root = tk.Tk()
    app = ScannerApp(root)
    root.mainloop()
