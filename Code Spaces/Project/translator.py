import customtkinter as ctk
import pandas as pd
from tkinter import filedialog
from deep_translator import GoogleTranslator
from concurrent.futures import ThreadPoolExecutor
import threading
import time
import os

BATCH_SIZE = 50
df = None  # Global DataFrame
header_vars = {}

def translate_batch(text_list, target_lang="bn"):
    try:
        return GoogleTranslator(source='auto', target=target_lang).translate_batch(text_list)
    except Exception as e:
        print(f"Batch error: {e}")
        return text_list

def translate_column(column, progress_callback, col_index, total_cols):
    text_list = column.fillna("").astype(str).tolist()
    translated = []
    for i in range(0, len(text_list), BATCH_SIZE):
        batch = text_list[i:i + BATCH_SIZE]
        translated.extend(translate_batch(batch))
        progress_callback(col_index, i + BATCH_SIZE, len(text_list), total_cols)
    return translated

def start_translation_thread(selected_columns, file_path, output_label, progress_bar, timer_label, progress_percent_label):
    threading.Thread(
        target=translate_and_save,
        args=(selected_columns, file_path, output_label, progress_bar, timer_label, progress_percent_label),
        daemon=True
    ).start()

def translate_and_save(selected_columns, file_path, output_label, progress_bar, timer_label, progress_percent_label):
    global df
    start_time = time.time()
    num_columns = len(selected_columns)
    progress_bar.set(0)
    progress_percent_label.configure(text="0%")

    def progress_callback(col_index, batch_end, total_rows, total_cols):
        batch_progress = min(batch_end / total_rows, 1.0)
        overall = ((col_index + batch_progress) / total_cols)
        progress_bar.set(overall)
        progress_percent_label.configure(text=f"{int(overall * 100)}%")
        elapsed = time.time() - start_time
        timer_label.configure(text=f"⏱️ Elapsed: {elapsed:.1f} sec")
        app.update_idletasks()

    translated_data = {}
    with ThreadPoolExecutor() as executor:
        results = executor.map(
            lambda i_col: translate_column(df[i_col], progress_callback, selected_columns.index(i_col), num_columns),
            selected_columns
        )
    for col_name, translated_column in zip(selected_columns, results):
        translated_data[col_name] = translated_column

    for col in translated_data:
        df[col] = translated_data[col]

    output_path = os.path.join(os.path.dirname(file_path), "translated_output.xlsx")
    df.to_excel(output_path, index=False)

    elapsed = time.time() - start_time
    output_label.configure(text=f"✅ Done in {elapsed:.1f} sec\nSaved to:\n{output_path}")
    progress_bar.set(1.0)
    progress_percent_label.configure(text="100%")
    timer_label.configure(text=f"⏱️ Total Time: {elapsed:.1f} sec")

def load_file_and_show_checkboxes(output_label, checkbox_frame, progress_bar, timer_label, progress_percent_label):
    global df, header_vars
    file_path = filedialog.askopenfilename(filetypes=[("Excel or CSV files", "*.xls *.xlsx *.csv")])
    if not file_path:
        return

    ext = os.path.splitext(file_path)[1].lower()
    df = pd.read_csv(file_path, dtype=str) if ext == '.csv' else pd.read_excel(file_path, dtype=str)

    for widget in checkbox_frame.winfo_children():
        widget.destroy()

    header_vars.clear()

    for header in df.columns:
        var = ctk.BooleanVar(value=True)
        checkbox = ctk.CTkCheckBox(checkbox_frame, text=header, variable=var)
        checkbox.pack(anchor="w", pady=2, padx=10)
        header_vars[header] = var

    ctk.CTkButton(app, text="🚀 Start Translation",
                  command=lambda: start_translation_thread(
                      [col for col in header_vars if header_vars[col].get()],
                      file_path,
                      output_label,
                      progress_bar,
                      timer_label,
                      progress_percent_label
                  )).pack(pady=10)

# ==== UI SETUP ====
ctk.set_appearance_mode("system")  # 'dark', 'light', or 'system'
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("Bangla Data Translator")
app.geometry("600x630")
app.resizable(False, False)

ctk.CTkLabel(app, text="Bangla Data Translator", font=ctk.CTkFont("Segoe UI", 24, "bold")).pack(pady=(20, 10))
ctk.CTkLabel(app, text="Select a CSV/Excel file, choose which columns to translate into Bangla.", wraplength=560).pack(pady=(0, 15))

ctk.CTkButton(app, text="📂 Load File", command=lambda: load_file_and_show_checkboxes(output_label, checkbox_frame, progress_bar, timer_label, progress_percent_label)).pack(pady=10)

checkbox_frame = ctk.CTkScrollableFrame(app, width=550, height=160)
checkbox_frame.pack(pady=5)

# Progress + Percentage
progress_frame = ctk.CTkFrame(app, fg_color="transparent")
progress_frame.pack(pady=(10, 0))

progress_bar = ctk.CTkProgressBar(progress_frame, width=460, height=18)
progress_bar.set(0)
progress_bar.pack(side="left", padx=(10, 5))

progress_percent_label = ctk.CTkLabel(progress_frame, text="0%", width=40, anchor="w")
progress_percent_label.pack(side="left")

timer_label = ctk.CTkLabel(app, text="", font=ctk.CTkFont(size=12))
timer_label.pack(pady=(5, 10))

output_label = ctk.CTkLabel(app, text="", wraplength=550, justify="center")
output_label.pack(pady=10)

app.mainloop()
