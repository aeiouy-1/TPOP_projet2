import os
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import csv
import serial
import serial.tools.list_ports
import time

import matplotlib
matplotlib.use('TkAgg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from galvos import RedPitayaGalvos

class ScannerApp:
    BG = '#1e1e2e'; BG2 = '#181825'; BLUE = '#89b4fa'; RED = '#f38ba8'; GRN = '#a6e3a1'; YLW = '#f9e2af'; FG = '#cdd6f4'

    def __init__(self, root):
        self.root = root
        self.root.title("Contrôle Galvos & Acquisition Intensité")
        self.root.configure(bg=self.BG)
        self.root.minsize(1000, 750)

        # Contrôleurs
        self.galvos = RedPitayaGalvos()
        self.ser = None
        
        # Variables d'état du Scan
        self.is_scanning = False
        self.scan_with_measurement = True
        self.current_scan_voltage = -1.0
        self.voltage_step = 0.005  
        self.voltage_max = 1.0 
        self.scan_axis = tk.StringVar(value="X") 
        
        # Données
        self.v_data = []
        self.sig_data = []

        self._build_ui()

    def _build_ui(self):
        # --- PANNEAU SUPÉRIEUR : CONNEXIONS ---
        top_frame = tk.Frame(self.root, bg=self.BG2, pady=10)
        top_frame.pack(fill='x')

        tk.Label(top_frame, text="Red Pitaya (Galvos):", bg=self.BG2, fg=self.BLUE, font=('', 10, 'bold')).grid(row=0, column=0, padx=10)
        self.lbl_rp_stat = tk.Label(top_frame, text="Déconnecté", bg=self.BG2, fg=self.RED)
        self.lbl_rp_stat.grid(row=0, column=1)
        self.btn_conn_rp = tk.Button(top_frame, text="Connecter RP", command=self.connect_rp)
        self.btn_conn_rp.grid(row=0, column=2, padx=10)

        tk.Label(top_frame, text="Arduino (Détecteur optionnel):", bg=self.BG2, fg=self.BLUE, font=('', 10, 'bold')).grid(row=0, column=3, padx=10)
        self.cbPort = ttk.Combobox(top_frame, width=10, state='readonly')
        self.cbPort.grid(row=0, column=4)
        ttk.Button(top_frame, text="↻", width=3, command=self._refresh_ports).grid(row=0, column=5)
        
        self.lbl_ard_stat = tk.Label(top_frame, text="Déconnecté", bg=self.BG2, fg=self.RED)
        self.lbl_ard_stat.grid(row=0, column=6, padx=10)
        self.btn_conn_ard = tk.Button(top_frame, text="Connecter Arduino", command=self.connect_arduino)
        self.btn_conn_ard.grid(row=0, column=7)

        self._refresh_ports()

        # --- PANNEAU CENTRAL : CONTRÔLES ---
        ctrl_frame = tk.Frame(self.root, bg=self.BG, pady=10)
        ctrl_frame.pack(fill='x', padx=10)

        # 1. Contrôle Manuel (Gauche)
        frame_manuel = tk.LabelFrame(ctrl_frame, text=" Contrôle Manuel ", bg=self.BG, fg=self.FG, font=('', 11, 'bold'))
        frame_manuel.pack(side='left', fill='both', expand=True, padx=(0, 5))

        self.scale_x = tk.Scale(frame_manuel, from_=-1.0, to=1.0, resolution=0.01, orient=tk.HORIZONTAL, label="Position X (Volts)", bg=self.BG, fg=self.FG, highlightthickness=0, command=self.update_manual_position)
        self.scale_x.pack(fill='x', padx=10, pady=5)

        self.scale_y = tk.Scale(frame_manuel, from_=-1.0, to=1.0, resolution=0.01, orient=tk.HORIZONTAL, label="Position Y (Volts)", bg=self.BG, fg=self.FG, highlightthickness=0, command=self.update_manual_position)
        self.scale_y.pack(fill='x', padx=10, pady=5)

        self.btn_zero = tk.Button(frame_manuel, text="Remettre à Zéro", bg='salmon', command=self.reset_galvos)
        self.btn_zero.pack(pady=5)

        # 2. Balayage Automatique (Droite)
        frame_scan = tk.LabelFrame(ctrl_frame, text=" Balayage Automatique ", bg=self.BG, fg=self.FG, font=('', 11, 'bold'))
        frame_scan.pack(side='left', fill='both', expand=True, padx=(5, 0))

        # Radio boutons pour l'axe
        tk.Radiobutton(frame_scan, text="Scanner l'Axe X (Y maintenu fixe)", variable=self.scan_axis, value="X", bg=self.BG, fg=self.FG, selectcolor=self.BG2).pack(anchor='w', padx=10, pady=2)
        tk.Radiobutton(frame_scan, text="Scanner l'Axe Y (X maintenu fixe)", variable=self.scan_axis, value="Y", bg=self.BG, fg=self.FG, selectcolor=self.BG2).pack(anchor='w', padx=10, pady=2)

        # Ajout : Champ de saisie pour le temps d'acquisition
        frame_param = tk.Frame(frame_scan, bg=self.BG)
        frame_param.pack(anchor='w', padx=10, pady=5)
        tk.Label(frame_param, text="Temps par point (s) :", bg=self.BG, fg=self.FG).pack(side='left')
        self.spin_delay = ttk.Spinbox(frame_param, from_=0.1, to=5.0, increment=0.1, width=8)
        self.spin_delay.set(0.5) # Valeur par défaut de 0.5 seconde
        self.spin_delay.pack(side='left', padx=5)

        # Boutons de contrôle
        buttons_frame = tk.Frame(frame_scan, bg=self.BG)
        buttons_frame.pack(pady=10)

        self.btn_start_scan = tk.Button(buttons_frame, text="▶ Scan + mesure", bg=self.GRN, font=('', 10, 'bold'), command=self.start_scan)
        self.btn_start_scan.grid(row=0, column=0, padx=5)

        self.btn_manual_scan = tk.Button(buttons_frame, text="↻ Scan manuel", bg=self.YLW, font=('', 10, 'bold'), command=self.start_manual_scan)
        self.btn_manual_scan.grid(row=0, column=1, padx=5)

        self.btn_stop_scan = tk.Button(buttons_frame, text="⏹ Stopper", bg=self.RED, font=('', 10, 'bold'), command=self.stop_scan)
        self.btn_stop_scan.grid(row=0, column=2, padx=5)

        self.btn_save = tk.Button(buttons_frame, text="💾 Exporter CSV", bg=self.BLUE, font=('', 10, 'bold'), command=self._save_data)
        self.btn_save.grid(row=0, column=3, padx=5)

        # --- ZONE GRAPHIQUE ---
        self.fig, self.ax = plt.subplots(figsize=(8, 4), facecolor=self.BG)
        self._configure_plot()
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(fill='both', expand=True, padx=10, pady=10)

    # --- METHODES DE CONNEXION ---
    def connect_rp(self):
        success, msg = self.galvos.connect()
        if success:
            self.lbl_rp_stat.config(text="Connecté", fg=self.GRN)
            self.btn_conn_rp.config(state=tk.DISABLED)
        else:
            messagebox.showerror("Erreur Galvos", msg)

    def _refresh_ports(self):
        pts = [p.device for p in serial.tools.list_ports.comports()]
        self.cbPort['values'] = pts
        if pts:
            self.cbPort.set(pts[0])
        else:
            self.cbPort.set("")

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
            except Exception as e:
                messagebox.showerror("Erreur Arduino", str(e))
        else:
            self.ser.close()
            self.ser = None
            self.lbl_ard_stat.config(text="Déconnecté", fg=self.RED)
            self.btn_conn_ard.config(text="Connecter Arduino")

    # --- CONTROLE MANUEL ---
    def update_manual_position(self, event=None):
        if self.galvos.connected and not self.is_scanning:
            vx = self.scale_x.get()
            vy = self.scale_y.get()
            self.galvos.set_position(vx, vy)

    def reset_galvos(self):
        self.scale_x.set(0)
        self.scale_y.set(0)
        if self.galvos.connected and not self.is_scanning:
            self.galvos.set_position(0.0, 0.0)

    # --- LOGIQUE DE SCAN ---
    def start_scan(self):
        self._start_scan(with_measurement=True)

    def start_manual_scan(self):
        self._start_scan(with_measurement=False)

    def _start_scan(self, with_measurement):
        if not self.galvos.connected:
            messagebox.showwarning("Attention", "Connectez le Red Pitaya avant de lancer un scan.")
            return

        if with_measurement and (self.ser is None or not self.ser.is_open):
            messagebox.showwarning("Attention", "Connectez l'Arduino pour lancer un scan avec mesure.")
            return

        self.scan_with_measurement = with_measurement
        self.is_scanning = True
        self.current_scan_voltage = -1.0  
        self.v_data.clear()
        self.sig_data.clear()
        
        axe = self.scan_axis.get()
        self._configure_plot(axe=axe, with_measurement=with_measurement)
        self.canvas.draw_idle()

        # On désactive les contrôles pour éviter les interférences
        self.btn_start_scan.config(state=tk.DISABLED)
        self.btn_manual_scan.config(state=tk.DISABLED)
        self.scale_x.config(state=tk.DISABLED)
        self.scale_y.config(state=tk.DISABLED)
        self.spin_delay.config(state=tk.DISABLED)
        
        self.scan_step()

    def scan_step(self):
        if not self.is_scanning: return

        axe = self.scan_axis.get()
        if axe == "X":
            vx = self.current_scan_voltage
            vy = self.scale_y.get()
        else:
            vx = self.scale_x.get()
            vy = self.current_scan_voltage

        self.galvos.set_position(vx, vy)

        if self.scan_with_measurement:
            self.root.after(50, self.read_intensity)
        else:
            self.root.after(50, self.finish_manual_step)

    def read_intensity(self):
        if not self.is_scanning: return

        if self.ser is None or not self.ser.is_open:
            self.stop_scan()
            messagebox.showwarning("Arduino", "La connexion Arduino a été perdue pendant le scan.")
            return

        try:
            self.ser.reset_input_buffer()
            self.ser.write(b'M')
        except serial.SerialException as e:
            self.stop_scan()
            messagebox.showwarning("Arduino", f"Erreur de communication Arduino : {e}")
            return
        
        self.root.after(20, self.process_serial_and_loop)

    def process_serial_and_loop(self):
        if not self.is_scanning: return

        if self.ser is None or not self.ser.is_open:
            self.stop_scan()
            messagebox.showwarning("Arduino", "La connexion Arduino a été perdue pendant le scan.")
            return

        measured_value = None
        try:
            has_data = self.ser.in_waiting > 0
        except serial.SerialException as e:
            self.stop_scan()
            messagebox.showwarning("Arduino", f"Erreur de communication Arduino : {e}")
            return

        if has_data:
            try:
                line = self.ser.readline().decode('utf-8').strip()
                measured_value = float(line)
            except ValueError:
                pass

        self._finish_scan_point(measured_value=measured_value, overhead_ms=70)

    def finish_manual_step(self):
        if not self.is_scanning:
            return

        self._finish_scan_point(overhead_ms=50)

    def _finish_scan_point(self, measured_value=None, overhead_ms=0):
        if measured_value is not None:
            self.v_data.append(self.current_scan_voltage)
            self.sig_data.append(measured_value)

            self.ln.set_data(self.v_data, self.sig_data)
            self.ax.relim()
            self.ax.autoscale_view()
            self.canvas.draw_idle()

        self.current_scan_voltage += self.voltage_step
        
        if self.current_scan_voltage <= self.voltage_max:
            delay_ms = self._get_remaining_delay_ms(overhead_ms)
            self.root.after(delay_ms, self.scan_step)
        else:
            self.stop_scan()
            mode = "avec mesure" if self.scan_with_measurement else "manuel"
            messagebox.showinfo("Fini", f"Le balayage {mode} est terminé !")

    def _get_remaining_delay_ms(self, overhead_ms):
        try:
            total_time_ms = int(float(self.spin_delay.get().replace(',', '.')) * 1000)
        except ValueError:
            total_time_ms = 500

        delay_ms = total_time_ms - overhead_ms
        if delay_ms < 10:
            delay_ms = 10
        return delay_ms

    def stop_scan(self):
        self.is_scanning = False
        self.btn_start_scan.config(state=tk.NORMAL)
        self.btn_manual_scan.config(state=tk.NORMAL)
        self.scale_x.config(state=tk.NORMAL)
        self.scale_y.config(state=tk.NORMAL)
        self.spin_delay.config(state=tk.NORMAL)
        
        self.update_manual_position()

    def _configure_plot(self, axe="X", with_measurement=True):
        self.ax.clear()
        self.ax.set_facecolor(self.BG2)
        self.ax.tick_params(colors='white')
        self.ax.set_xlabel(f'Tension Axe {axe} (Volts)', color='white')
        if with_measurement:
            self.ax.set_ylabel('Intensité (ADC)', color='white')
            self.ax.set_title('Scan avec acquisition', color='white')
        else:
            self.ax.set_ylabel('Aucune mesure', color='white')
            self.ax.set_title('Scan manuel des galvos', color='white')
        self.ax.grid(True, color='#313244', ls='--')
        self.ln, = self.ax.plot([], [], color=self.RED, lw=1.5, marker='o', markersize=3)

    # --- SAUVEGARDE ---
    def _save_data(self):
        if not self.v_data:
            messagebox.showinfo("Vide", "Aucune donnée à sauvegarder.")
            return

        filename = simpledialog.askstring("Sauvegarde", "Nom du fichier CSV (ex: profil_spatial) :")
        if not filename: return
        if not filename.endswith('.csv'): filename += '.csv'
        
        folder = "donnees_scan"
        if not os.path.exists(folder): os.makedirs(folder)
        path = os.path.join(folder, filename)

        try:
            with open(path, 'w', newline='') as f:
                writer = csv.writer(f)
                axe = self.scan_axis.get()
                writer.writerow([f"Tension_{axe}(V)", "Intensite"])
                for i in range(len(self.v_data)):
                    writer.writerow([f"{self.v_data[i]:.3f}", f"{self.sig_data[i]:.1f}"])
            messagebox.showinfo("Succès", f"Fichier enregistré dans {path}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Échec de l'enregistrement : {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ScannerApp(root)
    root.mainloop()
