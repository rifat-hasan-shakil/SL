import psutil
import time
import logging
import argparse # Kept for potential future CLI integration or default settings
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import threading # For running monitoring in a separate thread

# --- Configuration (Defaults for GUI) ---
DEFAULT_LOG_FILE = "system_monitor_gui.log"
DEFAULT_INTERVAL = 5  # seconds
DEFAULT_DURATION = 60  # seconds (0 for indefinite)
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# --- Font Definitions ---
BASE_FONT_FAMILY = "Segoe UI"
BASE_FONT_SIZE = 10
LABEL_FONT = (BASE_FONT_FAMILY, BASE_FONT_SIZE)
STATS_FONT = (BASE_FONT_FAMILY, 12, "bold")
LOG_FONT = (BASE_FONT_FAMILY, 9)
STATUS_FONT = (BASE_FONT_FAMILY, 9)
ENTRY_FONT = (BASE_FONT_FAMILY, BASE_FONT_SIZE)


# --- Monitoring Functions (can be outside the class or methods) ---
def get_cpu_usage():
    """Returns the current system-wide CPU utilization as a percentage."""
    return psutil.cpu_percent(interval=0.5) # Shorter interval for GUI responsiveness

def get_memory_usage():
    """Returns a dictionary containing memory usage statistics."""
    mem = psutil.virtual_memory()
    return {
        "total_mb": round(mem.total / (1024 * 1024), 2),
        "available_mb": round(mem.available / (1024 * 1024), 2),
        "percent_used": mem.percent,
        "used_mb": round(mem.used / (1024 * 1024), 2),
    }

# --- Custom Logging Handler for Tkinter Text Widget ---
class TextHandler(logging.Handler):
    """This class allows you to log to a Tkinter Text or ScrolledText widget."""
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        # Formatter for the GUI log display (always standard, not CSV)
        self.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

    def emit(self, record):
        msg = self.format(record)
        self.text_widget.configure(state='normal')
        self.text_widget.insert(tk.END, msg + '\n')
        self.text_widget.configure(state='disabled')
        self.text_widget.see(tk.END) # Scroll to the end

# --- Main Application Class ---
class SystemMonitorApp:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("System Performance Monitor")
        self.root.geometry("780x620") # Slightly adjusted size for font changes

        # --- Styling ---
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            print("Clam theme not available, using default.")
        
        style.configure('.', font=LABEL_FONT)
        style.configure('TLabel', font=LABEL_FONT)
        style.configure('TButton', font=LABEL_FONT)
        style.configure('TCheckbutton', font=LABEL_FONT)
        style.configure('TEntry', font=ENTRY_FONT) 
        style.configure('TLabelframe.Label', font=(BASE_FONT_FAMILY, BASE_FONT_SIZE, "bold"))


        # --- Variables ---
        self.log_file_var = tk.StringVar(value=DEFAULT_LOG_FILE)
        self.interval_var = tk.IntVar(value=DEFAULT_INTERVAL)
        self.duration_var = tk.IntVar(value=DEFAULT_DURATION)
        self.csv_format_var = tk.BooleanVar(value=False)

        self.cpu_usage_var = tk.StringVar(value="CPU: --.- %")
        self.mem_usage_var = tk.StringVar(value="Memory: --.- % (--.- MB / --.- MB)")
        self.status_var = tk.StringVar(value="Ready.")

        self.monitoring_active = False
        self.monitoring_thread = None
        self.logger = None 

        # --- UI Setup ---
        self.create_widgets()
        self.update_status("Application loaded. Configure settings and start monitoring.")

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        controls_frame = ttk.LabelFrame(main_frame, text="Controls", padding="10")
        controls_frame.pack(fill=tk.X, pady=(0,5)) 
        controls_frame.columnconfigure(1, weight=1) 

        ttk.Label(controls_frame, text="Log File:", font=LABEL_FONT).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.log_file_entry = ttk.Entry(controls_frame, textvariable=self.log_file_var, width=40, font=ENTRY_FONT)
        self.log_file_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        self.browse_button = ttk.Button(controls_frame, text="Browse...", command=self.browse_log_file)
        self.browse_button.grid(row=0, column=2, padx=5, pady=5)

        ttk.Label(controls_frame, text="Interval (s):", font=LABEL_FONT).grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.interval_entry = ttk.Entry(controls_frame, textvariable=self.interval_var, width=10, font=ENTRY_FONT)
        self.interval_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        ttk.Label(controls_frame, text="Duration (s, 0=inf):", font=LABEL_FONT).grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.duration_entry = ttk.Entry(controls_frame, textvariable=self.duration_var, width=10, font=ENTRY_FONT)
        self.duration_entry.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)

        self.csv_checkbox = ttk.Checkbutton(controls_frame, text="Log in CSV format", variable=self.csv_format_var)
        self.csv_checkbox.grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky=tk.W)

        button_frame = ttk.Frame(controls_frame)
        button_frame.grid(row=4, column=0, columnspan=3, pady=10)

        self.start_button = ttk.Button(button_frame, text="Start Monitoring", command=self.start_monitoring) 
        self.start_button.pack(side=tk.LEFT, padx=5)
        self.stop_button = ttk.Button(button_frame, text="Stop Monitoring", command=self.stop_monitoring, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)

        stats_frame = ttk.LabelFrame(main_frame, text="Current Usage", padding="10")
        stats_frame.pack(fill=tk.X, pady=5)

        ttk.Label(stats_frame, textvariable=self.cpu_usage_var, font=STATS_FONT).pack(side=tk.LEFT, padx=10, pady=5)
        ttk.Label(stats_frame, textvariable=self.mem_usage_var, font=STATS_FONT).pack(side=tk.LEFT, padx=10, pady=5)

        log_display_frame = ttk.LabelFrame(main_frame, text="Live Log", padding="10")
        log_display_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.log_text_area = scrolledtext.ScrolledText(log_display_frame, wrap=tk.WORD, state=tk.DISABLED, height=10, font=LOG_FONT)
        self.log_text_area.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        
        self.clear_log_button = ttk.Button(log_display_frame, text="Clear GUI Log", command=self.clear_gui_log) # Defined as self.clear_log_button
        self.clear_log_button.pack(side=tk.RIGHT, pady=(5,0))


        self.status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding="2 5", font=STATUS_FONT)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def update_status(self, message):
        self.status_var.set(message)

    def clear_gui_log(self):
        self.log_text_area.configure(state='normal')
        self.log_text_area.delete(1.0, tk.END)
        self.log_text_area.configure(state='disabled')
        self.update_status("GUI log cleared.")

    def browse_log_file(self):
        file_path = filedialog.asksaveasfilename(
            initialfile=self.log_file_var.get(), 
            defaultextension=".log",
            filetypes=[("Log files", "*.log"), ("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if file_path:
            self.log_file_var.set(file_path)
            self.update_status(f"Log file set to: {file_path}")

    def set_controls_state(self, new_state):
        for widget in [self.log_file_entry, self.browse_button, 
                       self.interval_entry, self.duration_entry, self.csv_checkbox]:
            widget.config(state=new_state)


    def setup_logger(self):
        self.logger = logging.getLogger("GUISystemMonitor")
        self.logger.handlers = [] 
        self.logger.setLevel(logging.INFO)

        try:
            log_file_path = self.log_file_var.get()
            if not log_file_path: 
                messagebox.showerror("Error", "Log file path cannot be empty.")
                self.update_status("Error: Log file path empty.")
                return False

            file_handler = logging.FileHandler(log_file_path, mode='a') 
            if self.csv_format_var.get():
                csv_formatter = logging.Formatter("%(message)s") 
                file_handler.setFormatter(csv_formatter)
            else:
                std_formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
                file_handler.setFormatter(std_formatter)
            self.logger.addHandler(file_handler)
        except IOError as e:
            messagebox.showerror("Logging Error", f"Could not open log file for writing: {log_file_path}\n{e}")
            self.update_status(f"Error: Could not write to log file.")
            return False

        gui_log_handler = TextHandler(self.log_text_area) 
        self.logger.addHandler(gui_log_handler)
        return True


    def start_monitoring(self):
        if self.monitoring_active:
            messagebox.showwarning("Monitor Active", "Monitoring is already active.")
            return

        try:
            interval = self.interval_var.get()
            duration = self.duration_var.get()
            if interval <= 0:
                messagebox.showerror("Error", "Interval must be a positive number.")
                self.update_status("Error: Invalid interval.")
                return
            if duration < 0: 
                messagebox.showerror("Error", "Duration cannot be negative.")
                self.update_status("Error: Invalid duration.")
                return
        except tk.TclError: 
            messagebox.showerror("Error", "Invalid interval or duration value. Please enter numbers.")
            self.update_status("Error: Non-numeric interval/duration.")
            return

        if not self.setup_logger(): 
            self.update_status("Monitoring not started due to logger setup issue.")
            return

        self.monitoring_active = True
        self.set_controls_state('disabled') 
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.clear_log_button.config(state=tk.DISABLED) # Corrected: Changed to self.clear_log_button

        self.log_text_area.configure(state='normal')
        self.log_text_area.delete(1.0, tk.END)
        self.log_text_area.configure(state='disabled')

        if self.csv_format_var.get():
            header = "timestamp,cpu_percent,memory_percent_used,memory_used_mb,memory_total_mb,memory_available_mb"
            if self.logger and self.logger.handlers:
                file_h = next((h for h in self.logger.handlers if isinstance(h, logging.FileHandler)), None)
                if file_h:
                    try:
                        with open(self.log_file_var.get(), 'r+') as f: 
                            first_line = f.readline().strip()
                            if first_line != header: 
                                f.seek(0, 2) 
                                if f.tell() == 0 : 
                                     f.write(header + '\n')
                    except FileNotFoundError:
                         with open(self.log_file_var.get(), 'w') as f: 
                            f.write(header + '\n')
                    except Exception as e:
                        print(f"Error checking/writing CSV header: {e}")


            self.logger.info(f"Starting CSV monitoring. Data logged to: {self.log_file_var.get()}")
            self.update_status(f"CSV Monitoring started. Logging to {self.log_file_var.get()}")

        else:
            duration_text = f"{duration}s" if duration > 0 else "Indefinite"
            self.logger.info(f"Starting system monitoring. Interval: {interval}s, Duration: {duration_text}")
            self.update_status(f"Monitoring started. Interval: {interval}s. Duration: {duration_text}.")


        self.monitoring_thread = threading.Thread(target=self.monitoring_loop, args=(interval, duration), daemon=True)
        self.monitoring_thread.start()

    def stop_monitoring(self, from_duration_end=False):
        if not self.monitoring_active:
            return

        self.monitoring_active = False 
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.set_controls_state('normal') 
        self.clear_log_button.config(state=tk.NORMAL) # Corrected: Changed to self.clear_log_button


        if not from_duration_end: 
            if self.logger: self.logger.info("Monitoring stopped by user.")
            self.update_status("Monitoring stopped by user.")
        else:
            self.update_status("Monitoring finished (duration reached).")


    def monitoring_loop(self, interval, duration):
        start_loop_time = time.time()

        try:
            while self.monitoring_active:
                cpu = get_cpu_usage()
                mem_info = get_memory_usage()
                now_time = datetime.now()
                timestamp_str = now_time.strftime(DATE_FORMAT)

                if self.csv_format_var.get():
                    log_entry_msg = (
                        f"{timestamp_str},"
                        f"{cpu:.2f},"
                        f"{mem_info['percent_used']:.2f},"
                        f"{mem_info['used_mb']:.2f},"
                        f"{mem_info['total_mb']:.2f},"
                        f"{mem_info['available_mb']:.2f}"
                    )
                else: 
                    log_entry_msg = ( 
                        f"CPU Usage: {cpu:.2f}% | "
                        f"Memory Usage: {mem_info['percent_used']:.2f}% "
                        f"({mem_info['used_mb']:.2f}MB Used / {mem_info['total_mb']:.2f}MB Total)"
                    )
                
                self.root.after(0, self.update_gui_and_log, cpu, mem_info, log_entry_msg)

                if duration > 0:
                    elapsed_time = time.time() - start_loop_time
                    if elapsed_time >= duration:
                        if self.logger: self.logger.info("Monitoring duration reached. Stopping.")
                        self.root.after(0, self.stop_monitoring, True) 
                        break

                for _ in range(int(interval * 10)): 
                    if not self.monitoring_active: break
                    time.sleep(0.1)
                if not self.monitoring_active: break
        except Exception as e:
            if self.logger: self.logger.error(f"Error in monitoring loop: {e}", exc_info=True)
            self.root.after(0, lambda: messagebox.showerror("Monitoring Error", f"An error occurred in monitoring: {e}"))
            self.root.after(0, self.update_status, f"Error during monitoring: {e}")
        finally:
            self.root.after(0, self.update_gui_on_stop_from_thread)


    def update_gui_and_log(self, cpu, mem_info, log_entry_msg_for_file):
        if not self.root.winfo_exists(): return

        self.cpu_usage_var.set(f"CPU: {cpu:.1f} %")
        self.mem_usage_var.set(
            f"Memory: {mem_info['percent_used']:.1f} % "
            f"({mem_info['used_mb']:.1f}MB / {mem_info['total_mb']:.1f}MB)"
        )
        if self.logger:
            self.logger.info(log_entry_msg_for_file)

    def update_gui_on_stop_from_thread(self):
        if not self.root.winfo_exists(): return
        
        if self.monitoring_active: 
             self.monitoring_active = False 

        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.set_controls_state('normal')
        self.clear_log_button.config(state=tk.NORMAL) # Corrected: Changed to self.clear_log_button


    def on_closing(self):
        if self.monitoring_active:
            if messagebox.askokcancel("Quit", "Monitoring is active. Stop monitoring and quit?"):
                self.stop_monitoring() 
                self.root.after(200, self.root.destroy) 
            else:
                return 
        else:
            self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = SystemMonitorApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing) 
    root.mainloop()
