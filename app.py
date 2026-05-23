import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from pdf_engine import generate_coupon_layout, analyze_pdf_v2

APP_NAME = "CG Kupon Generator V2"

class KuponGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("780x680")
        self.root.resizable(False, False)

        self.input_pdf = tk.StringVar()
        self.output_folder = tk.StringVar(value=str(Path.home() / "Downloads" / "CG_Kupon_Output"))
        self.page_width_mm = tk.DoubleVar(value=325)
        self.page_height_mm = tk.DoubleVar(value=485)
        self.cols = tk.IntVar(value=3)
        self.rows = tk.IntVar(value=11)
        self.crop_mark_extra_mm = tk.DoubleVar(value=5)
        self.kupon_per_file = tk.IntVar(value=500)
        self.use_cropmark = tk.BooleanVar(value=True)
        self.auto_rotate = tk.BooleanVar(value=True)
        self.status = tk.StringVar(value="Siap digunakan.")
        self.analysis_text = tk.StringVar(value="Belum dianalisis.")
        self.progress = tk.DoubleVar(value=0)
        self.build_ui()

    def build_ui(self):
        container = ttk.Frame(self.root, padding=20)
        container.pack(fill="both", expand=True)

        ttk.Label(container, text=APP_NAME, font=("Arial", 20, "bold")).pack(anchor="w")
        ttk.Label(container, text="Auto Layout Engine V2: cari layout paling banyak isi, termasuk opsi rotasi kupon.", foreground="#555").pack(anchor="w", pady=(4, 18))

        file_frame = ttk.LabelFrame(container, text="1. Pilih File PDF", padding=14)
        file_frame.pack(fill="x", pady=(0, 12))
        ttk.Entry(file_frame, textvariable=self.input_pdf, width=78).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(file_frame, text="Browse PDF", command=self.browse_pdf).grid(row=0, column=1)

        out_frame = ttk.LabelFrame(container, text="2. Folder Output", padding=14)
        out_frame.pack(fill="x", pady=(0, 12))
        ttk.Entry(out_frame, textvariable=self.output_folder, width=78).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(out_frame, text="Browse Folder", command=self.browse_output).grid(row=0, column=1)

        setting_frame = ttk.LabelFrame(container, text="3. Setting Layout", padding=14)
        setting_frame.pack(fill="x", pady=(0, 12))
        self.add_input(setting_frame, "Lebar Kertas (mm)", self.page_width_mm, 0, 0)
        self.add_input(setting_frame, "Tinggi Kertas (mm)", self.page_height_mm, 0, 2)
        self.add_input(setting_frame, "Kolom", self.cols, 1, 0)
        self.add_input(setting_frame, "Baris", self.rows, 1, 2)
        self.add_input(setting_frame, "Panjang Cropmark (mm)", self.crop_mark_extra_mm, 2, 0)
        self.add_input(setting_frame, "Kupon per File", self.kupon_per_file, 2, 2)
        ttk.Checkbutton(setting_frame, text="Pakai Cropmark", variable=self.use_cropmark).grid(row=3, column=0, sticky="w", pady=(10, 0))
        ttk.Checkbutton(setting_frame, text="Auto Rotate Optimization", variable=self.auto_rotate).grid(row=3, column=2, sticky="w", pady=(10, 0))

        action_frame = ttk.Frame(container)
        action_frame.pack(fill="x", pady=(6, 12))
        ttk.Button(action_frame, text="Analyze Auto Layout V2", command=self.analyze).pack(side="left")
        ttk.Button(action_frame, text="Generate PDF", command=self.generate).pack(side="left", padx=10)

        analysis_frame = ttk.LabelFrame(container, text="Hasil Analyze", padding=14)
        analysis_frame.pack(fill="x", pady=(0, 12))
        ttk.Label(analysis_frame, textvariable=self.analysis_text, wraplength=720, justify="left").pack(anchor="w")

        progress_frame = ttk.LabelFrame(container, text="Status", padding=14)
        progress_frame.pack(fill="x", pady=(0, 12))
        ttk.Label(progress_frame, textvariable=self.status).pack(anchor="w", pady=(0, 8))
        ttk.Progressbar(progress_frame, variable=self.progress, maximum=100).pack(fill="x")

        ttk.Label(container, text="© CG Digital Print — Local Desktop Generator", foreground="#777").pack(anchor="center", pady=(8, 0))

    def add_input(self, parent, label, variable, row, col):
        ttk.Label(parent, text=label).grid(row=row, column=col, sticky="w", pady=6)
        ttk.Entry(parent, textvariable=variable, width=16).grid(row=row, column=col + 1, sticky="w", padx=(8, 24), pady=6)

    def browse_pdf(self):
        path = filedialog.askopenfilename(title="Pilih File PDF", filetypes=[("PDF Files", "*.pdf")])
        if path:
            self.input_pdf.set(path)

    def browse_output(self):
        path = filedialog.askdirectory(title="Pilih Folder Output")
        if path:
            self.output_folder.set(path)

    def analyze(self):
        input_pdf = self.input_pdf.get().strip()
        if not input_pdf:
            messagebox.showwarning(APP_NAME, "Pilih file PDF dulu bro.")
            return
        try:
            data = analyze_pdf_v2(
                input_pdf=input_pdf,
                page_width_mm=self.page_width_mm.get(),
                page_height_mm=self.page_height_mm.get(),
                crop_mark_extra_mm=self.crop_mark_extra_mm.get(),
                outer_gap_mm=3,
                allow_rotate=self.auto_rotate.get(),
            )
            self.cols.set(data["best"]["cols"])
            self.rows.set(data["best"]["rows"])
            self.analysis_text.set(
                f"Ukuran kupon asli: {data['kupon_width_mm']} x {data['kupon_height_mm']} mm\n"
                f"Best layout: {data['best']['cols']} x {data['best']['rows']} = {data['best']['total']} pcs/page\n"
                f"Orientasi: {data['best']['orientation_label']}\n"
                f"Efficiency: {data['best']['efficiency_percent']}%\n"
                f"Normal: {data['normal']['cols']} x {data['normal']['rows']} = {data['normal']['total']} pcs/page\n"
                f"Rotated: {data['rotated']['cols']} x {data['rotated']['rows']} = {data['rotated']['total']} pcs/page"
            )
            self.status.set("Analyze V2 berhasil. Kolom/baris sudah diisi otomatis.")
        except Exception as exc:
            messagebox.showerror(APP_NAME, str(exc))
            self.status.set("Analyze gagal.")

    def generate(self):
        if not self.input_pdf.get().strip():
            messagebox.showwarning(APP_NAME, "Pilih file PDF dulu bro.")
            return
        thread = threading.Thread(target=self._generate_worker, daemon=True)
        thread.start()

    def _generate_worker(self):
        try:
            self.progress.set(10)
            self.status.set("Generating... jangan tutup aplikasi.")
            result = generate_coupon_layout(
                input_pdf=self.input_pdf.get().strip(),
                output_folder=self.output_folder.get().strip(),
                page_width_mm=self.page_width_mm.get(),
                page_height_mm=self.page_height_mm.get(),
                cols=self.cols.get(),
                rows=self.rows.get(),
                crop_mark_extra_mm=self.crop_mark_extra_mm.get(),
                kupon_per_file=self.kupon_per_file.get(),
                use_cropmark=self.use_cropmark.get(),
            )
            self.progress.set(100)
            self.status.set(f"Selesai. {len(result['generated_files'])} file berhasil dibuat.")
            messagebox.showinfo(APP_NAME, f"Selesai bro!\n\nOutput folder:\n{self.output_folder.get().strip()}")
        except Exception as exc:
            self.progress.set(0)
            self.status.set("Generate gagal.")
            messagebox.showerror(APP_NAME, str(exc))

if __name__ == "__main__":
    root = tk.Tk()
    app = KuponGeneratorApp(root)
    root.mainloop()
