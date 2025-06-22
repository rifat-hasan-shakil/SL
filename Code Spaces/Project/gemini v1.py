import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue
from googletrans import Translator as GoogletransTranslator # Renamed for clarity
from deep_translator import GoogleTranslator, MicrosoftTranslator, MyMemoryTranslator # MicrosoftTranslator is imported but not used
import os
from datetime import datetime
import json
import re
import traceback # For detailed error reporting in main

class TranslatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Excel/CSV English to Bangla Translator")
        self.root.geometry("900x700")

        # Variables
        self.df = None
        self.translated_df = None
        self.file_path = ""
        self.selected_columns = []
        self.translation_queue = queue.Queue()
        self.start_time = None
        self.cache_hits = 0
        self.api_calls = 0

        # Initialize translators
        # The program will try these in order, or distribute work among them.
        # This is the "automatic selection" mechanism.
        self.translators = [
            GoogleTranslator(source='en', target='bn'), # deep_translator's GoogleTranslator
            GoogletransTranslator(), # googletrans library's Translator
            MyMemoryTranslator(source='en', target='bn') # Consider: email='your_email@example.com' for better MyMemory rates
        ]
        if not self.translators:
            self.log_message("Warning: No translators configured. Translation will likely fail.", level="error")


        # Initialize common translations dictionary (local cache)
        self.common_translations = self.load_common_translations()
        # This will store API-fetched translations for the current session before saving
        self.translation_cache = {}

        self.setup_ui()
        self.log_message("Application initialized. Load a file to begin.")

    def load_common_translations(self):
        """Load common English to Bangla translations and custom saved translations."""
        # Default common translations (can be extensive)
        common_translations = {
            # Personal Information
            "name": "নাম", "first name": "প্রথম নাম", "last name": "শেষ নাম", "full name": "পূর্ণ নাম",
            "father name": "পিতার নাম", "mother name": "মাতার নাম", "father's name": "পিতার নাম",
            "mother's name": "মাতার নাম", "age": "বয়স", "sex": "লিঙ্গ", "gender": "লিঙ্গ",
            "male": "পুরুষ", "female": "নারী", "address": "ঠিকানা", "phone": "ফোন", "mobile": "মোবাইল",
            "email": "ইমেইল", "id": "আইডি", "id number": "আইডি নম্বর", "nid": "জাতীয় পরিচয়পত্র",
            "national id": "জাতীয় পরিচয়পত্র", "passport": "পাসপোর্ট", "birth certificate": "জন্ম নিবন্ধন",
            "date of birth": "জন্ম তারিখ", "birth date": "জন্ম তারিখ", "religion": "ধর্ম",
            "nationality": "জাতীয়তা", "occupation": "পেশা", "profession": "পেশা", "job": "চাকরি",
            "work": "কাজ", "salary": "বেতন", "income": "আয়", "marital status": "বৈবাহিক অবস্থা",
            "married": "বিবাহিত", "unmarried": "অবিবাহিত", "single": "অবিবাহিত",
            "divorced": "তালাকপ্রাপ্ত", "widow": "বিধবা", "widower": "বিপত্নীক",

            # Educational Information
            "education": "শিক্ষা", "qualification": "যোগ্যতা", "degree": "ডিগ্রি", "school": "স্কুল",
            "college": "কলেজ", "university": "বিশ্ববিদ্যালয়", "institute": "প্রতিষ্ঠান",
            "student": "শিক্ষার্থী", "teacher": "শিক্ষক", "class": "শ্রেণী", "grade": "গ্রেড",
            "result": "ফলাফল", "marks": "নম্বর", "percentage": "শতাংশ", "cgpa": "সিজিপিএ",
            "gpa": "জিপিএ", "subject": "বিষয়", "course": "কোর্স", "semester": "সেমিস্টার",
            "year": "বছর", "batch": "ব্যাচ", "roll": "রোল", "roll number": "রোল নম্বর",
            "registration": "নিবন্ধন", "admission": "ভর্তি",

            # Address and Location
            "district": "জেলা", "division": "বিভাগ", "upazila": "উপজেলা", "thana": "থানা",
            "village": "গ্রাম", "union": "ইউনিয়ন", "ward": "ওয়ার্ড", "city": "শহর", "town": "শহর",
            "area": "এলাকা", "road": "রাস্তা", "street": "রাস্তা", "house": "বাড়ি", "flat": "ফ্ল্যাট",
            "building": "ভবন", "postal code": "পোস্টাল কোড", "zip code": "জিপ কোড",
            "pin code": "পিন কোড", "country": "দেশ", "bangladesh": "বাংলাদেশ", "dhaka": "ঢাকা",
            "chittagong": "চট্টগ্রাম", "sylhet": "সিলেট", "rajshahi": "রাজশাহী", "khulna": "খুলনা",
            "barisal": "বরিশাল", "rangpur": "রংপুর", "mymensingh": "ময়মনসিংহ",

            # Common Words and Phrases
            "yes": "হ্যাঁ", "no": "না", "true": "সত্য", "false": "মিথ্যা", "good": "ভাল", "bad": "খারাপ",
            "new": "নতুন", "old": "পুরানো", "total": "মোট", "amount": "পরিমাণ", "date": "তারিখ",
            "time": "সময়", "present": "উপস্থিত", "absent": "অনুপস্থিত",

            # Status and Conditions
            "active": "সক্রিয়", "inactive": "নিষ্ক্রিয়", "valid": "বৈধ", "invalid": "অবৈধ",
            "approved": "অনুমোদিত", "rejected": "প্রত্যাখ্যাত", "pending": "অপেক্ষমাণ",
            "complete": "সম্পূর্ণ", "incomplete": "অসম্পূর্ণ"
            # Add more common translations as needed
        }
        # Load custom translations from file, potentially overriding defaults or adding new ones
        custom_file_path = 'custom_translations.json'
        try:
            if os.path.exists(custom_file_path):
                with open(custom_file_path, 'r', encoding='utf-8') as f:
                    custom_dict = json.load(f)
                    common_translations.update(custom_dict)
                    if hasattr(self, 'log_text'): # Check if logger is ready
                        self.log_message(f"Loaded {len(custom_dict)} custom translations from {custom_file_path}.")
                    else:
                        print(f"Loaded {len(custom_dict)} custom translations from {custom_file_path}.")
        except json.JSONDecodeError:
            msg = f"Warning: Could not decode {custom_file_path}. File might be corrupted. Using defaults."
            if hasattr(self, 'log_text'): self.log_message(msg, "warning")
            else: print(msg)
        except Exception as e:
            msg = f"Error loading custom translations from {custom_file_path}: {e}"
            if hasattr(self, 'log_text'): self.log_message(msg, "error")
            else: print(msg)
        return common_translations

    def save_custom_translations(self):
        """Save newly learned API translations by merging them with existing custom translations."""
        custom_file_path = 'custom_translations.json'
        existing_custom = {}
        try:
            if os.path.exists(custom_file_path):
                with open(custom_file_path, 'r', encoding='utf-8') as f:
                    try:
                        existing_custom = json.load(f)
                    except json.JSONDecodeError:
                        self.log_message(f"Warning: {custom_file_path} was corrupted. Overwriting with current session's learned translations.", "warning")

            # Merge: new translations from self.translation_cache take precedence
            existing_custom.update(self.translation_cache)

            with open(custom_file_path, 'w', encoding='utf-8') as f:
                json.dump(existing_custom, f, ensure_ascii=False, indent=2)
            self.log_message(f"Custom dictionary saved to {custom_file_path} with {len(existing_custom)} total entries.")
            # Optionally, update self.common_translations with the newly saved combined set
            self.common_translations.update(existing_custom)

        except Exception as e:
            self.log_message(f"Error saving custom translations to {custom_file_path}: {e}", "error")

    def preprocess_text(self, text):
        if pd.isna(text) or text is None: # Added None check
            return ""
        text_str = str(text).strip().lower()
        text_str = re.sub(r'\s+', ' ', text_str)
        return text_str

    def get_cached_translation(self, text):
        if pd.isna(text) or str(text).strip() == "":
            return str(text) # Return original string form

        processed_text = self.preprocess_text(text)
        if not processed_text: # If after preprocessing it's empty
            return str(text)

        # Check common_translations (includes custom.json loaded at start)
        if processed_text in self.common_translations:
            self.cache_hits += 1
            return self.common_translations[processed_text]

        # Check translation_cache (API results from current session)
        if processed_text in self.translation_cache:
            self.cache_hits += 1
            return self.translation_cache[processed_text]

        # Partial matching was removed due to high risk of inaccuracy.
        # If re-implementing, use robust whole-word or phrase matching.
        return None

    def setup_ui(self):
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # File selection
        file_frame = ttk.LabelFrame(main_frame, text="File Selection", padding="10")
        file_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(0, weight=1)
        self.file_label = ttk.Label(file_frame, text="No file selected")
        self.file_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        ttk.Button(file_frame, text="Browse File", command=self.browse_file).grid(row=0, column=1, sticky=tk.E)

        # Column selection
        self.column_frame = ttk.LabelFrame(main_frame, text="Select Columns to Translate", padding="10")
        self.column_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        self.column_frame.columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(self.column_frame, height=150)
        self.scrollbar = ttk.Scrollbar(self.column_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # Translation controls
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=2, column=0, columnspan=2, pady=(0, 10), sticky=tk.W)
        self.translate_btn = ttk.Button(control_frame, text="Start Translation", command=self.start_translation, state="disabled")
        self.translate_btn.grid(row=0, column=0, padx=(0, 10))
        self.cancel_btn = ttk.Button(control_frame, text="Cancel", command=self.cancel_translation, state="disabled")
        self.cancel_btn.grid(row=0, column=1, padx=(0, 10))
        self.clear_cache_btn = ttk.Button(control_frame, text="Clear Session Cache", command=self.clear_session_cache)
        self.clear_cache_btn.grid(row=0, column=2, padx=(0, 10))
        self.save_cache_btn = ttk.Button(control_frame, text="Save Learned to Custom Dict", command=self.save_custom_translations)
        self.save_cache_btn.grid(row=0, column=3)

        # Progress section
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding="10")
        progress_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        progress_frame.columnconfigure(0, weight=1) # Make progress bar expand
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100) # Length removed for expansion
        self.progress_bar.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))
        self.status_label = ttk.Label(progress_frame, text="Ready")
        self.status_label.grid(row=1, column=0, sticky=tk.W)
        self.time_label = ttk.Label(progress_frame, text="Elapsed: 00:00:00")
        self.time_label.grid(row=1, column=1, sticky=tk.E)
        self.cache_label = ttk.Label(progress_frame, text="Cache: 0 hits, 0 API calls")
        self.cache_label.grid(row=2, column=0, columnspan=2, sticky=tk.W)

        # Save section
        save_frame = ttk.LabelFrame(main_frame, text="Save Translated File", padding="10")
        save_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        self.save_btn = ttk.Button(save_frame, text="Save As...", command=self.save_file, state="disabled")
        self.save_btn.grid(row=0, column=0)

        # Log section
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="10")
        log_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        main_frame.rowconfigure(5, weight=1) # Make log area expand vertically
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.log_text = tk.Text(log_frame, height=8, width=80, wrap=tk.WORD) # Reasonable default height
        log_scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set, state='disabled') # Start disabled, enable in log_message
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        main_frame.columnconfigure(0, weight=1)

        self.cancel_flag = False

    def log_message(self, message, level="info"): # Added level for potential styling/filtering
        if not hasattr(self, 'log_text') or not self.log_text: return # Guard if called too early
        self.log_text.config(state='normal') # Enable for writing
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] [{level.upper()}] {message}\n"
        self.log_text.insert(tk.END, formatted_message)
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled') # Disable again
        self.root.update_idletasks() # Ensure UI update

    def clear_session_cache(self):
        self.translation_cache.clear()
        self.log_message("In-session API translation cache (self.translation_cache) cleared.")
        # Reset only API related stats for this run if desired, or let them accumulate
        # For now, only clearing the dictionary. update_cache_stats will reflect current state.
        self.update_cache_stats()


    def update_cache_stats(self):
        total_lookups = self.cache_hits + self.api_calls
        cache_ratio = (self.cache_hits / total_lookups) * 100 if total_lookups > 0 else 0
        self.cache_label.config(
            text=f"Cache Hits: {self.cache_hits} ({cache_ratio:.1f}%), API Calls: {self.api_calls}"
        )

    def browse_file(self):
        filetypes = [("Excel files", "*.xlsx *.xls"), ("CSV files", "*.csv"), ("All files", "*.*")]
        new_file_path = filedialog.askopenfilename(title="Select Excel or CSV file", filetypes=filetypes)
        if new_file_path:
            self.file_path = new_file_path
            self.file_label.config(text=os.path.basename(self.file_path))
            self.log_message(f"Selected file: {self.file_path}")
            self.load_file()

    def load_file(self):
        if not self.file_path: return
        try:
            # keep_default_na=False treats empty strings as empty, not NaN
            # na_filter=False also helps ensure empty strings are read as such
            if self.file_path.lower().endswith('.csv'):
                self.df = pd.read_csv(self.file_path, encoding='utf-8', keep_default_na=False, na_filter=False, dtype=str)
            elif self.file_path.lower().endswith(('.xls', '.xlsx')):
                self.df = pd.read_excel(self.file_path, keep_default_na=False, na_filter=False, dtype=str)
            else:
                self.log_message(f"Unsupported file type: {self.file_path}", "error")
                messagebox.showerror("Unsupported File", "Please select an Excel (.xls, .xlsx) or CSV (.csv) file.")
                return

            # Ensure all data is string for consistency, as dtype=str should handle this.
            # self.df = self.df.astype(str) # Redundant if dtype=str worked

            self.log_message(f"File loaded: {len(self.df)} rows, {len(self.df.columns)} columns.")
            self.display_columns()
            self.save_btn.config(state="disabled")
            self.translated_df = None
            self.progress_var.set(0)
            self.status_label.config(text="File loaded. Select columns and start translation.")
        except Exception as e:
            self.log_message(f"Failed to load file '{self.file_path}': {e}", "error")
            messagebox.showerror("Error Loading File", f"Could not load file: {e}")

    def display_columns(self):
        for widget in self.scrollable_frame.winfo_children(): widget.destroy()
        self.column_vars = {}
        if self.df is None or self.df.empty:
            self.log_message("No data to display columns for.", "warning")
            self.translate_btn.config(state="disabled")
            return

        for i, column in enumerate(self.df.columns):
            var = tk.BooleanVar()
            # Ensure column name is a string for the checkbox text
            checkbox = ttk.Checkbutton(self.scrollable_frame, text=str(column), variable=var)
            checkbox.grid(row=i // 3, column=i % 3, sticky=tk.W, padx=5, pady=2) # 3 checkboxes per row
            self.column_vars[column] = var

        button_frame = ttk.Frame(self.scrollable_frame)
        # Place button frame after all checkbox rows
        button_frame.grid(row=(len(self.df.columns) + 2) // 3, column=0, columnspan=3, pady=10, sticky=tk.W)
        ttk.Button(button_frame, text="Select All", command=self.select_all_columns).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Deselect All", command=self.deselect_all_columns).pack(side=tk.LEFT, padx=5)

        self.translate_btn.config(state="normal")
        self.root.update_idletasks() # Ensure canvas updates for scrollregion
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def select_all_columns(self):
        for var in self.column_vars.values(): var.set(True)
    def deselect_all_columns(self):
        for var in self.column_vars.values(): var.set(False)
    def get_selected_columns(self):
        return [col for col, var in self.column_vars.items() if var.get()] if hasattr(self, 'column_vars') else []


    def translate_text(self, text, initial_translator_index=0):
        original_text_str = str(text) # Keep original for fallback
        if pd.isna(text) or not original_text_str.strip(): # Check if empty after stripping
            return original_text_str

        cached_result = self.get_cached_translation(original_text_str)
        if cached_result is not None:
            return cached_result

        # If not in cache, then it's an API call (or will be)
        self.api_calls += 1
        # No need to update queue here, batched in perform_translation

        text_to_translate = original_text_str.strip()
        processed_key_for_cache = self.preprocess_text(original_text_str)

        if not self.translators:
            self.log_message("No translators available to process text.", "error")
            return original_text_str # Return original if no translators

        for i in range(len(self.translators)):
            current_translator_idx = (initial_translator_index + i) % len(self.translators)
            translator = self.translators[current_translator_idx]
            translator_name = type(translator).__name__
            try:
                translated_text = ""
                if isinstance(translator, GoogletransTranslator):
                    result = translator.translate(text_to_translate, src='en', dest='bn')
                    translated_text = result.text
                # For deep_translator instances (GoogleTranslator, MyMemoryTranslator)
                elif hasattr(translator, 'translate') and callable(getattr(translator, 'translate')):
                    translated_text = translator.translate(text_to_translate)
                else:
                    self.log_message(f"Translator '{translator_name}' is not a recognized type.", "warning")
                    continue # Skip to next translator

                if translated_text and translated_text.strip():
                    self.translation_cache[processed_key_for_cache] = translated_text
                    return translated_text
                else:
                    self.log_message(f"Translator {translator_name} returned empty/None for: '{text_to_translate[:30]}...'", "info")
            except Exception as e:
                self.log_message(f"Translator {translator_name} failed for '{text_to_translate[:30]}...': {e}", "warning")
                if "rate limit" in str(e).lower() or "too many requests" in str(e).lower():
                    time.sleep(0.5) # Basic delay for rate limits before next translator
                # Continue to the next translator in the list
        
        self.log_message(f"All translators failed for: '{text_to_translate[:50]}...'. Returning original.", "warning")
        return original_text_str # Return original if all translators fail

    def translate_batch(self, batch_data, initial_translator_idx_for_batch):
        results = []
        for row_idx, col_name, text_content in batch_data:
            if self.cancel_flag: break
            translated = self.translate_text(text_content, initial_translator_idx_for_batch)
            results.append((row_idx, col_name, translated))
            # A very small sleep can sometimes help with rapid-fire API calls, but can also slow things down.
            # Adjust or remove based on observed API behavior.
            # time.sleep(0.01)
        return results

    def start_translation(self):
        self.selected_columns = self.get_selected_columns()
        if not self.selected_columns:
            messagebox.showwarning("No Columns Selected", "Please select at least one column to translate.")
            return
        if self.df is None or self.df.empty:
            messagebox.showwarning("No File Loaded", "Please load a file first.")
            return

        self.cancel_flag = False
        self.start_time = time.time()
        self.cache_hits = 0 # Reset for this run
        self.api_calls = 0  # Reset for this run
        self.update_cache_stats() # Initial display for this run

        self.translate_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        self.save_btn.config(state="disabled")
        self.log_text.config(state='normal')
        self.log_text.delete('1.0', tk.END) # Clear log for new session
        self.log_text.config(state='disabled')
        self.log_message("Translation process initiated...")

        self.translation_thread = threading.Thread(target=self.perform_translation, daemon=True)
        self.translation_thread.start()
        self.update_progress_loop() # Start the UI update loop

    def perform_translation(self):
        try:
            self.translated_df = self.df.copy()
            translation_data_to_process = []
            for col in self.selected_columns:
                for idx, value in enumerate(self.df[col]):
                    str_value = str(value) # Convert once
                    if pd.notna(value) and str_value.strip(): # Only non-empty, non-NA strings
                        translation_data_to_process.append((idx, col, str_value))
                    # else: # Empty/NA cells are kept as is from the copy

            total_items = len(translation_data_to_process)
            if total_items == 0:
                self.log_message("No non-empty text found in selected columns to translate.", "info")
                self.translation_queue.put(('complete', "No data to translate."))
                return

            self.log_message(f"Preparing to translate {total_items} text items.")
            self.log_message(f"Using {len(self.translators)} translator services configured.")
            self.log_message(f"Initial common dictionary size (incl. custom): {len(self.common_translations)} entries.")

            num_workers = len(self.translators) if self.translators else 1
            # Dynamic batch size: Aim for at least a few batches, but not too small
            batch_size = max(1, min(20, total_items // (num_workers * 2 if num_workers > 0 else 1)))
            if total_items < num_workers * 2 : batch_size = 1 # Smaller batches for very few items
            
            data_batches = [translation_data_to_process[i:i + batch_size] for i in range(0, total_items, batch_size)]
            self.log_message(f"Data split into {len(data_batches)} batches of up to {batch_size} items each.")

            processed_item_count = 0
            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                future_to_batch_details = {}
                for i, batch_content in enumerate(data_batches):
                    if self.cancel_flag: break
                    # Distribute initial attempts across translators
                    initial_translator_for_batch = i % num_workers if num_workers > 0 else 0
                    future = executor.submit(self.translate_batch, batch_content, initial_translator_for_batch)
                    future_to_batch_details[future] = len(batch_content) # Store num items for progress

                for future in as_completed(future_to_batch_details):
                    if self.cancel_flag: break
                    items_in_this_batch = future_to_batch_details[future]
                    try:
                        batch_results = future.result()
                        for row_idx, col_name, translated_text in batch_results:
                            self.translated_df.at[row_idx, col_name] = translated_text
                    except Exception as e_batch:
                        self.log_message(f"Error processing a translation batch: {e_batch}", "error")
                    
                    processed_item_count += items_in_this_batch
                    progress_percent = (processed_item_count / total_items) * 100
                    self.translation_queue.put(('progress', progress_percent))
                    
                    # Periodically update cache stats on UI
                    if processed_item_count % (batch_size * num_workers // 2 if num_workers > 0 else batch_size) == 0 or processed_item_count == total_items:
                        self.translation_queue.put(('cache_update', None))
            
            # Final wrap-up based on cancellation or completion
            if self.cancel_flag:
                self.translation_queue.put(('cancelled', "Translation was cancelled by the user."))
            else:
                self.translation_queue.put(('progress', 100.0)) # Ensure it hits 100%
                self.translation_queue.put(('cache_update', None)) # Final cache numbers
                self.translation_queue.put(('complete', "Translation finished successfully."))
                self.save_custom_translations() # Auto-save newly learned translations

        except Exception as e_main_translation:
            self.log_message(f"Critical error during translation process: {e_main_translation}", "error")
            self.translation_queue.put(('error', str(e_main_translation)))

    def update_progress_loop(self):
        """Periodically checks the queue and updates UI. Schedules itself."""
        active_process = True # Assume active unless explicitly stopped
        try:
            while True: # Process all messages currently in queue
                item_type, data = self.translation_queue.get_nowait()

                if item_type == 'progress':
                    self.progress_var.set(data)
                    self.status_label.config(text=f"Translating... {data:.1f}%")
                elif item_type == 'cache_update':
                    self.update_cache_stats()
                elif item_type == 'complete':
                    self.status_label.config(text=data if isinstance(data, str) else "Translation completed!")
                    self.progress_var.set(100) # Ensure 100%
                    self.translate_btn.config(state="normal")
                    self.cancel_btn.config(state="disabled")
                    self.save_btn.config(state="normal" if self.translated_df is not None else "disabled")
                    self.update_cache_stats() # Final stats update
                    active_process = False; break # Stop the loop
                elif item_type == 'cancelled':
                    self.status_label.config(text=data if isinstance(data, str) else "Translation cancelled.")
                    self.translate_btn.config(state="normal")
                    self.cancel_btn.config(state="disabled")
                    # Decide if save should be enabled for partially translated data
                    self.save_btn.config(state="normal" if self.translated_df is not None else "disabled")
                    self.update_cache_stats()
                    active_process = False; break # Stop the loop
                elif item_type == 'error':
                    self.status_label.config(text="Error occurred. Check log.")
                    messagebox.showerror("Translation Process Error", str(data))
                    self.translate_btn.config(state="normal")
                    self.cancel_btn.config(state="disabled")
                    self.save_btn.config(state="disabled")
                    self.update_cache_stats()
                    active_process = False; break # Stop the loop
            
        except queue.Empty: # No more messages for now
            pass
        except Exception as e_ui_update: # Catch other unexpected errors during UI update
            self.log_message(f"Error updating UI from queue: {e_ui_update}", "error")
            active_process = False # Stop loop on unexpected UI error
        
        # Update elapsed time if process is ongoing
        if active_process and self.start_time:
            elapsed = time.time() - self.start_time
            h, rem = divmod(elapsed, 3600)
            m, s = divmod(rem, 60)
            self.time_label.config(text=f"Elapsed: {int(h):02d}:{int(m):02d}:{int(s):02d}")

        if active_process: # If still running, schedule next check
            self.root.after(200, self.update_progress_loop) # Check queue periodically

    def cancel_translation(self):
        if not self.cancel_flag: # Prevent multiple cancel actions
            self.cancel_flag = True
            self.log_message("Cancellation request received. Finishing current items...", "info")
            self.status_label.config(text="Cancelling... Please wait.")
            self.cancel_btn.config(state="disabled") # Disable cancel button once clicked

    def save_file(self):
        if self.translated_df is None:
            messagebox.showwarning("No Data", "No translated data available to save.")
            return

        original_basename = os.path.basename(self.file_path if self.file_path else "Untitled")
        name, ext = os.path.splitext(original_basename)
        suggested_filename = f"{name}_translated{ext if ext.lower() in ['.xlsx', '.csv'] else '.xlsx'}"

        file_path_to_save = filedialog.asksaveasfilename(
            title="Save Translated File As",
            initialfile=suggested_filename,
            defaultextension=".xlsx", # Default if user types name without extension
            filetypes=[("Excel files", "*.xlsx"), ("CSV files (UTF-8)", "*.csv"), ("All files", "*.*")]
        )

        if file_path_to_save:
            try:
                save_ext = os.path.splitext(file_path_to_save)[1].lower()
                if save_ext == '.csv':
                    self.translated_df.to_csv(file_path_to_save, index=False, encoding='utf-8-sig') # BOM for Excel
                    self.log_message(f"Translated file saved as CSV: {file_path_to_save}")
                elif save_ext == '.xlsx':
                    self.translated_df.to_excel(file_path_to_save, index=False)
                    self.log_message(f"Translated file saved as Excel: {file_path_to_save}")
                else: # Default or unknown extension
                    self.translated_df.to_excel(file_path_to_save, index=False) # Assume Excel if not .csv
                    self.log_message(f"Translated file saved (assumed Excel format): {file_path_to_save}")
                
                messagebox.showinfo("Save Successful", f"Translated file saved to:\n{file_path_to_save}")
            except Exception as e:
                self.log_message(f"Error saving file '{file_path_to_save}': {e}", "error")
                messagebox.showerror("Save Error", f"Failed to save file: {e}")

def main():
    root = tk.Tk()
    try:
        app = TranslatorApp(root)
        root.mainloop()
    except Exception as e_global:
        error_details = f"An critical error occurred and the application must close.\n\n" \
                        f"Error Type: {type(e_global).__name__}\n" \
                        f"Message: {str(e_global)}\n\n" \
                        f"Traceback:\n{traceback.format_exc()}"
        print("--- FATAL APPLICATION ERROR ---")
        print(error_details)
        print("-------------------------------")
        try:
            # Attempt to show Tkinter error only if mainloop hasn't started or root is still valid
            if root.winfo_exists(): # Check if root window still exists
                 messagebox.showerror("Fatal Application Error",
                                     f"A critical error occurred: {type(e_global).__name__}: {str(e_global)}\n\n"
                                     "Please check the console for detailed traceback.")
        except tk.TclError: # If Tkinter itself is in a bad state
            pass # Already printed to console
        except Exception as e_msgbox:
             print(f"Error trying to show error messagebox: {e_msgbox}")


if __name__ == "__main__":
    main()