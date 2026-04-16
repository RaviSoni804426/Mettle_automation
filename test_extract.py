import pdfplumber
import re

with pdfplumber.open(r"d:\Mettle_automation\PDF_Reports\Vikhyat_Fast-Track Process (FTP-SOT).pdf") as pdf:
    first_page_text = pdf.pages[0].extract_text()
    
    print("--- FIRST PAGE TEXT ---")
    print(first_page_text)
    
    print("\n--- EMAIL MATCHES ---")
    matches = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', first_page_text)
    print(matches)
