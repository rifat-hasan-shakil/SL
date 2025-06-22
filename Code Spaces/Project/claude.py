import pandas as pd
import re
from googletrans import Translator
import time
import logging
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
from pathlib import Path

class EnglishToBengaliTranslator:
    def __init__(self):
        self.translator = Translator()
        
        # Common translations for frequently used terms
        self.common_translations = {
            # Gender/Sex
            'male': 'পুরুষ',
            'female': 'মহিলা', 
            'man': 'পুরুষ',
            'woman': 'মহিলা',
            'boy': 'ছেলে',
            'girl': 'মেয়ে',
            'mr': 'জনাব',
            'mrs': 'বেগম',
            'ms': 'মিস',
            
            # Marital Status
            'married': 'বিবাহিত',
            'unmarried': 'অবিবাহিত',
            'single': 'অবিবাহিত',
            'divorced': 'তালাকপ্রাপ্ত',
            'widowed': 'বিধবা/বিপত্নীক',
            
            # Education
            'primary': 'প্রাথমিক',
            'secondary': 'মাধ্যমিক',
            'higher secondary': 'উচ্চ মাধ্যমিক',
            'bachelor': 'স্নাতক',
            'master': 'স্নাতকোত্তর',
            'phd': 'পিএইচডি',
            
            # Occupation
            'teacher': 'শিক্ষক',
            'doctor': 'চিকিৎসক',
            'engineer': 'প্রকৌশলী',
            'farmer': 'কৃষক',
            'student': 'ছাত্র/ছাত্রী',
            'businessman': 'ব্যবসায়ী',
            'housewife': 'গৃহিণী',
            
            # Relationships
            'father': 'পিতা',
            'mother': 'মাতা',
            'son': 'পুত্র',
            'daughter': 'কন্যা',
            'husband': 'স্বামী',
            'wife': 'স্ত্রী',
            'brother': 'ভাই',
            'sister': 'বোন',
            
            # Common titles
            'mr.': 'জনাব',
            'mrs.': 'বেগম',
            'dr.': 'ডাঃ',
            'prof.': 'অধ্যাপক',
        }
        
        # Bengali number mapping
        self.bengali_numbers = {
            '0': '০', '1': '১', '2': '২', '3': '৩', '4': '৪',
            '5': '৫', '6': '৬', '7': '৭', '8': '৮', '9': '৯'
        }
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    def is_id_number(self, text):
        """Check if text is likely an ID number (NID, passport, etc.)"""
        if pd.isna(text):
            return False
        text_str = str(text).strip()
        return bool(re.match(r'^[0-9\-\s]+$', text_str) and len(text_str) >= 4)
    
    def is_phone_number(self, text):
        """Check if text is a phone number"""
        if pd.isna(text):
            return False
        text_str = str(text).strip()
        return bool(re.match(r'^[\+]?[0-9\-\s\(\)]+$', text_str) and len(text_str) >= 7)
    
    def convert_numbers_to_bengali(self, text):
        """Convert English numbers to Bengali numbers"""
        if pd.isna(text):
            return text
        
        text_str = str(text)
        for eng, ben in self.bengali_numbers.items():
            text_str = text_str.replace(eng, ben)
        return text_str
    
    def translate_text(self, text, preserve_numbers=False):
        """Translate text from English to Bengali"""
        if pd.isna(text) or text == '':
            return text
            
        text_str = str(text).strip().lower()
        
        # Check if it's a number-only field (ID, phone, etc.)
        if self.is_id_number(text) or self.is_phone_number(text):
            if preserve_numbers:
                return self.convert_numbers_to_bengali(text)
            else:
                return str(text)
        
        # Check common translations first
        if text_str in self.common_translations:
            return self.common_translations[text_str]
        
        # Handle names and other text
        if re.match(r'^[a-zA-Z\s\.]+$', text_str):
            try:
                for attempt in range(3):
                    try:
                        result = self.translator.translate(str(text), src='en', dest='bn')
                        if result and result.text:
                            return result.text
                        time.sleep(1)
                    except Exception as e:
                        if attempt < 2:
                            time.sleep(2)
                        else:
                            return str(text)
            except Exception as e:
                return str(text)
        
        # For other text, try translation
        try:
            result = self.translator.translate(str(text), src='en', dest='bn')
            return result.text if result and result.text else str(text)
        except Exception as e:
            return str(text)
    
    def process_dataframe(self, df, columns_to_translate, preserve_numbers_in, progress_callback=None):
        """Process DataFrame and translate specified columns"""
        df_copy = df.copy()
        total_cells = sum(len([cell for cell in df_copy[col] if pd.notna(cell)]) for col in columns_to_translate)
        processed_cells = 0
        
        for col in columns_to_translate:
            if col in df_copy.columns:
                preserve_nums = col in preserve_numbers_in
                
                for idx, value in enumerate(df_copy[col]):
                    if pd.notna(value):
                        df_copy.loc[idx, col] = self.translate_text(value, preserve_numbers=preserve_nums)
                        processed_cells += 1
                        
                        if progress_callback:
                            progress = (processed_cells / total_cells) * 100
                            progress_callback(progress, f"Translating {col}: row {idx + 1}")
                        
                        if processed_cells % 5 == 0:
                            time.sleep(0.1)
        
        return df_copy


class TranslatorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("English to Bengali Data Translator")
        self.root.geometry("800x700")
        self.root.configure(bg='#f0f0f0')
        
        # Initialize translator
        self.translator = EnglishToBengaliTranslator()
        self.df = None
        self.file_path = None
        
        self.setup_gui()
        
    def setup_gui(self):
        # Title
        title_frame = tk.Frame(self.root, bg='#2c3e50', height=60)
        title_frame.pack(fill='x', padx=5, pady=5)
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(title_frame, text="English to Bengali Data Translator", 
                              font=('Arial', 16, 'bold'), fg='white', bg='#2c3e50')
        title_label.pack(expand=True)
        
        # Main container
        main_frame = tk.Frame(self.root, bg='#f0f0f0')
        main_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # File selection section
        file_frame = tk.LabelFrame(main_frame, text="File Selection", font=('Arial', 10, 'bold'),
                                  bg='#f0f0f0', fg='#2c3e50', padx=10, pady=10)
        file_frame.pack(fill='x', pady=(0, 10))
        
        self.file_path_var = tk.StringVar()
        file_path_frame = tk.Frame(file_frame, bg='#f0f0f0')
        file_path_frame.pack(fill='x', pady=5)
        
        tk.Label(file_path_frame, text="Selected File:", font=('Arial', 9), 
                bg='#f0f0f0').pack(anchor='w')
        self.file_path_label = tk.Label(file_path_frame, textvariable=self.file_path_var,
                                       font=('Arial', 9), bg='white', relief='sunken',
                                       anchor='w', padx=5, pady=2)
        self.file_path_label.pack(fill='x', pady=(2, 5))
        
        btn_frame = tk.Frame(file_frame, bg='#f0f0f0')
        btn_frame.pack(fill='x')
        
        self.select_btn = tk.Button(btn_frame, text="📁 Select File", command=self.select_file,
                                   font=('Arial', 10), bg='#3498db', fg='white',
                                   padx=20, pady=5, cursor='hand2')
        self.select_btn.pack(side='left', padx=5)
        
        self.preview_btn = tk.Button(btn_frame, text="👁 Preview Data", command=self.preview_data,
                                    font=('Arial', 10), bg='#95a5a6', fg='white',
                                    padx=20, pady=5, cursor='hand2', state='disabled')
        self.preview_btn.pack(side='left', padx=5)
        
        # Column selection section
        column_frame = tk.LabelFrame(main_frame, text="Column Selection", font=('Arial', 10, 'bold'),
                                    bg='#f0f0f0', fg='#2c3e50', padx=10, pady=10)
        column_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        # Create two columns for checkboxes
        checkbox_main_frame = tk.Frame(column_frame, bg='#f0f0f0')
        checkbox_main_frame.pack(fill='both', expand=True)
        
        # Left frame for translation columns
        left_frame = tk.Frame(checkbox_main_frame, bg='#f0f0f0')
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        tk.Label(left_frame, text="Columns to Translate:", font=('Arial', 9, 'bold'),
                bg='#f0f0f0', fg='#2c3e50').pack(anchor='w', pady=(0, 5))
        
        self.translate_frame = tk.Frame(left_frame, bg='#f0f0f0')
        self.translate_frame.pack(fill='both', expand=True)
        
        # Right frame for number conversion columns
        right_frame = tk.Frame(checkbox_main_frame, bg='#f0f0f0')
        right_frame.pack(side='right', fill='both', expand=True, padx=(10, 0))
        
        tk.Label(right_frame, text="Convert Numbers to Bengali:", font=('Arial', 9, 'bold'),
                bg='#f0f0f0', fg='#2c3e50').pack(anchor='w', pady=(0, 5))
        
        self.numbers_frame = tk.Frame(right_frame, bg='#f0f0f0')
        self.numbers_frame.pack(fill='both', expand=True)
        
        # Translation section
        translate_frame = tk.LabelFrame(main_frame, text="Translation", font=('Arial', 10, 'bold'),
                                       bg='#f0f0f0', fg='#2c3e50', padx=10, pady=10)
        translate_frame.pack(fill='x', pady=(0, 10))
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(translate_frame, variable=self.progress_var,
                                           maximum=100, length=400)
        self.progress_bar.pack(pady=5)
        
        self.progress_label = tk.Label(translate_frame, text="Ready to translate",
                                      font=('Arial', 9), bg='#f0f0f0')
        self.progress_label.pack(pady=2)
        
        # Translate button
        self.translate_btn = tk.Button(translate_frame, text="🔄 Start Translation",
                                      command=self.start_translation, font=('Arial', 12, 'bold'),
                                      bg='#27ae60', fg='white', padx=30, pady=8,
                                      cursor='hand2', state='disabled')
        self.translate_btn.pack(pady=10)
        
        # Log section
        log_frame = tk.LabelFrame(main_frame, text="Translation Log", font=('Arial', 10, 'bold'),
                                 bg='#f0f0f0', fg='#2c3e50', padx=10, pady=10)
        log_frame.pack(fill='x')
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=6, font=('Consolas', 9),
                                                 bg='#2c3e50', fg='#ecf0f1', insertbackground='white')
        self.log_text.pack(fill='x', pady=5)
        
        # Initialize column checkboxes storage
        self.translate_checkboxes = {}
        self.numbers_checkboxes = {}
        
    def log_message(self, message):
        """Add message to log display"""
        self.log_text.insert('end', f"{message}\n")
        self.log_text.see('end')
        self.root.update_idletasks()
        
    def select_file(self):
        """Open file dialog to select Excel or CSV file"""
        file_types = [
            ('Excel files', '*.xlsx *.xls'),
            ('CSV files', '*.csv'),
            ('All supported', '*.xlsx *.xls *.csv')
        ]
        
        file_path = filedialog.askopenfilename(
            title="Select Excel or CSV file",
            filetypes=file_types
        )
        
        if file_path:
            self.file_path = file_path
            self.file_path_var.set(os.path.basename(file_path))
            self.log_message(f"File selected: {os.path.basename(file_path)}")
            
            try:
                # Load the file
                if file_path.endswith('.csv'):
                    self.df = pd.read_csv(file_path, encoding='utf-8')
                else:
                    self.df = pd.read_excel(file_path)
                
                self.log_message(f"File loaded: {len(self.df)} rows, {len(self.df.columns)} columns")
                self.setup_column_checkboxes()
                self.preview_btn.config(state='normal')
                self.translate_btn.config(state='normal')
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file: {str(e)}")
                self.log_message(f"Error loading file: {str(e)}")
    
    def setup_column_checkboxes(self):
        """Create checkboxes for each column"""
        # Clear existing checkboxes
        for widget in self.translate_frame.winfo_children():
            widget.destroy()
        for widget in self.numbers_frame.winfo_children():
            widget.destroy()
            
        self.translate_checkboxes.clear()
        self.numbers_checkboxes.clear()
        
        # Auto-detect columns likely to need translation
        likely_translate_columns = []
        likely_number_columns = []
        
        for col in self.df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ['name', 'sex', 'gender', 'occupation', 
                                                      'education', 'marital', 'relation', 'address']):
                likely_translate_columns.append(col)
            elif any(keyword in col_lower for keyword in ['age', 'phone', 'mobile', 'number']):
                likely_number_columns.append(col)
        
        # Create translation checkboxes
        for i, col in enumerate(self.df.columns):
            var = tk.BooleanVar(value=col in likely_translate_columns)
            self.translate_checkboxes[col] = var
            
            cb = tk.Checkbutton(self.translate_frame, text=col, variable=var,
                               font=('Arial', 9), bg='#f0f0f0', anchor='w')
            cb.pack(fill='x', padx=5, pady=1)
        
        # Create number conversion checkboxes
        for i, col in enumerate(self.df.columns):
            var = tk.BooleanVar(value=col in likely_number_columns)
            self.numbers_checkboxes[col] = var
            
            cb = tk.Checkbutton(self.numbers_frame, text=col, variable=var,
                               font=('Arial', 9), bg='#f0f0f0', anchor='w')
            cb.pack(fill='x', padx=5, pady=1)
    
    def preview_data(self):
        """Show preview of the data"""
        if self.df is not None:
            preview_window = tk.Toplevel(self.root)
            preview_window.title("Data Preview")
            preview_window.geometry("800x400")
            
            # Create treeview for data display
            tree = ttk.Treeview(preview_window)
            tree.pack(fill='both', expand=True, padx=10, pady=10)
            
            # Configure columns
            tree['columns'] = list(self.df.columns)
            tree['show'] = 'headings'
            
            for col in self.df.columns:
                tree.heading(col, text=col)
                tree.column(col, width=100)
            
            # Insert data (first 50 rows)
            for i, row in self.df.head(50).iterrows():
                tree.insert('', 'end', values=list(row))
            
            # Add scrollbars
            v_scrollbar = ttk.Scrollbar(preview_window, orient='vertical', command=tree.yview)
            h_scrollbar = ttk.Scrollbar(preview_window, orient='horizontal', command=tree.xview)
            tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
            
            v_scrollbar.pack(side='right', fill='y')
            h_scrollbar.pack(side='bottom', fill='x')
    
    def update_progress(self, progress, message):
        """Update progress bar and message"""
        self.progress_var.set(progress)
        self.progress_label.config(text=message)
        self.log_message(message)
        self.root.update_idletasks()
    
    def start_translation(self):
        """Start the translation process in a separate thread"""
        # Get selected columns
        columns_to_translate = [col for col, var in self.translate_checkboxes.items() if var.get()]
        preserve_numbers_in = [col for col, var in self.numbers_checkboxes.items() if var.get()]
        
        if not columns_to_translate:
            messagebox.showwarning("No Columns Selected", "Please select at least one column to translate.")
            return
        
        # Disable UI during translation
        self.translate_btn.config(state='disabled', text="Translating...")
        self.select_btn.config(state='disabled')
        
        # Start translation in separate thread
        thread = threading.Thread(target=self.perform_translation, 
                                args=(columns_to_translate, preserve_numbers_in))
        thread.daemon = True
        thread.start()
    
    def perform_translation(self, columns_to_translate, preserve_numbers_in):
        """Perform the actual translation"""
        try:
            self.log_message("Starting translation process...")
            self.log_message(f"Translating columns: {', '.join(columns_to_translate)}")
            
            # Process the dataframe
            translated_df = self.translator.process_dataframe(
                self.df, columns_to_translate, preserve_numbers_in, 
                progress_callback=self.update_progress
            )
            
            # Save the file
            base_name = Path(self.file_path).stem
            extension = Path(self.file_path).suffix
            output_path = Path(self.file_path).parent / f"{base_name}_bengali{extension}"
            
            if extension.lower() == '.csv':
                translated_df.to_csv(output_path, index=False, encoding='utf-8-sig')
            else:
                translated_df.to_excel(output_path, index=False)
            
            self.log_message(f"Translation completed successfully!")
            self.log_message(f"Output saved as: {output_path.name}")
            
            # Show completion message
            self.root.after(0, lambda: messagebox.showinfo(
                "Translation Complete", 
                f"Translation completed successfully!\nOutput saved as: {output_path.name}"
            ))
            
        except Exception as e:
            error_msg = f"Translation failed: {str(e)}"
            self.log_message(error_msg)
            self.root.after(0, lambda: messagebox.showerror("Translation Error", error_msg))
        
        finally:
            # Re-enable UI
            self.root.after(0, self.reset_ui)
    
    def reset_ui(self):
        """Reset UI after translation"""
        self.translate_btn.config(state='normal', text="🔄 Start Translation")
        self.select_btn.config(state='normal')
        self.progress_var.set(0)
        self.progress_label.config(text="Ready to translate")


def main():
    # Create and run the GUI
    root = tk.Tk()
    app = TranslatorGUI(root)
    
    # Center the window
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")
    
    root.mainloop()

if __name__ == "__main__":
    main()