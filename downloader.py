import os
import re
import threading
import tkinter as tk
from tkinter import filedialog, ttk
import pdfplumber
import requests

class DownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Mettle Video Downloader")
        self.root.geometry("700x550")
        self.root.configure(padx=20, pady=20)

        # Style configuration
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except tk.TclError:
            pass
            
        style.configure('TButton', font=('Segoe UI', 10), padding=5)
        style.configure('TLabel', font=('Segoe UI', 10))
        style.configure('Header.TLabel', font=('Segoe UI', 16, 'bold'))

        # Header
        header = ttk.Label(self.root, text="Mettle Report Video Downloader", style='Header.TLabel')
        header.grid(row=0, column=0, columnspan=3, pady=(0, 20), sticky="w")

        # Variables
        self.input_dir = tk.StringVar(value=os.path.join(os.getcwd(), "PDF_Reports"))
        self.output_dir = tk.StringVar(value=os.path.join(os.getcwd(), "Organized_Videos"))

        # Input Directory Selection
        ttk.Label(self.root, text="PDF Reports Folder:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Entry(self.root, textvariable=self.input_dir, width=55, font=('Segoe UI', 10)).grid(row=1, column=1, padx=10, pady=5, sticky="we")
        ttk.Button(self.root, text="Browse...", command=self.browse_input).grid(row=1, column=2, pady=5)

        # Output Directory Selection
        ttk.Label(self.root, text="Output Videos Folder:").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Entry(self.root, textvariable=self.output_dir, width=55, font=('Segoe UI', 10)).grid(row=2, column=1, padx=10, pady=5, sticky="we")
        ttk.Button(self.root, text="Browse...", command=self.browse_output).grid(row=2, column=2, pady=5)

        # Start Button
        self.start_button = ttk.Button(self.root, text="Start Download", command=self.start_download_thread)
        self.start_button.grid(row=3, column=0, columnspan=3, pady=15, sticky="we")

        # Logs Frame
        log_frame = ttk.Frame(self.root)
        log_frame.grid(row=4, column=0, columnspan=3, sticky="nsew")
        self.root.rowconfigure(4, weight=1)
        self.root.columnconfigure(1, weight=1)

        ttk.Label(log_frame, text="Process Logs:").pack(anchor="w", pady=(0, 5))
        
        # Log Text Area (Dark Theme for Logs)
        self.log_text = tk.Text(log_frame, height=15, state=tk.DISABLED, font=('Consolas', 10), bg="#1e1e1e", fg="#d4d4d4", wrap="word", borderwidth=0, padx=10, pady=10)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=scrollbar.set)

    def log(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def browse_input(self):
        dir_path = filedialog.askdirectory(initialdir=self.input_dir.get(), title="Select PDF Reports Directory")
        if dir_path:
            self.input_dir.set(dir_path)

    def browse_output(self):
        dir_path = filedialog.askdirectory(initialdir=self.output_dir.get(), title="Select Output Video Directory")
        if dir_path:
            self.output_dir.set(dir_path)

    def start_download_thread(self):
        self.start_button.config(state=tk.DISABLED, text="Downloading...")
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        thread = threading.Thread(target=self.run_automation, daemon=True)
        thread.start()

    def run_automation(self):
        input_d = self.input_dir.get()
        output_d = self.output_dir.get()

        if not os.path.exists(input_d):
            self.log(f"❌ Error: Input directory does not exist: {input_d}")
            self.finish_download()
            return

        if not os.path.exists(output_d):
            try:
                os.makedirs(output_d)
                self.log(f"📁 Created output directory: {output_d}")
            except Exception as e:
                self.log(f"❌ Error creating output directory: {e}")
                self.finish_download()
                return

        pdf_files = [f for f in os.listdir(input_d) if f.lower().endswith('.pdf')]
        self.log(f"📄 Total PDFs detected: {len(pdf_files)}")
        self.log("-" * 60)

        for file_name in pdf_files:
            path = os.path.join(input_d, file_name)
            self.log(f"⚙️ Processing: {file_name}")
            
            try:
                with pdfplumber.open(path) as pdf:
                    first_page_text = pdf.pages[0].extract_text()
                    if not first_page_text:
                        self.log(f"  -> ⚠️ Could not extract text from {file_name}")
                        continue

                    lines = first_page_text.split('\n')
                    candidate_name = "Unknown"
                    for line in lines:
                        if "|" in line:
                            candidate_name = line.split('|')[0].strip()
                            break
                    
                    candidate_name = re.sub(r'[\\/*?:"<>|]', "", candidate_name).strip()
                    
                    email_match = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', first_page_text)
                    email_id = email_match.group(0).strip().lower() if email_match else candidate_name.lower()
                    
                    person_folder = os.path.join(output_d, email_id)
                    
                    if not os.path.exists(person_folder):
                        os.makedirs(person_folder)

                    found_links = []
                    for page in pdf.pages:
                        if page.hyperlinks:
                            for link in page.hyperlinks:
                                uri = link.get('uri')
                                if uri and any(k in uri.lower() for k in ["video", "mettl", "s3"]):
                                    found_links.append(uri)

                    if not found_links:
                        self.log("  -> ⚠️ No matching video links found.")

                    for i, url in enumerate(found_links[:3], 1):
                        save_filename = f"{email_id}_video_{i}.mp4"
                        save_path = os.path.join(person_folder, save_filename)
                        
                        if os.path.exists(save_path):
                            self.log(f"  -> ⏭️ {save_filename} already exist. Skipping...")
                            continue
                        
                        self.log(f"  -> ⬇️ Downloading {save_filename}...")
                        try:
                            r = requests.get(url, stream=True, timeout=60)
                            if r.status_code == 200:
                                with open(save_path, 'wb') as f:
                                    for chunk in r.iter_content(chunk_size=1024*1024):
                                        f.write(chunk)
                                self.log(f"     ✅ Success")
                            else:
                                self.log(f"     ❌ Error: HTTP {r.status_code}")
                        except Exception as e:
                            self.log(f"     ❌ Error: {e}")

            except Exception as e:
                self.log(f"❌ Error processing {file_name}: {e}")
            self.log("-" * 60)

        self.log("🎉 Batch processing finished!")
        self.finish_download()

    def finish_download(self):
        self.root.after(0, lambda: self.start_button.config(state=tk.NORMAL, text="Start Download"))

if __name__ == "__main__":
    root = tk.Tk()
    app = DownloaderApp(root)
    root.mainloop()