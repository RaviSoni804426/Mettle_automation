import streamlit as st
import pdfplumber
import requests
import os
import re
import shutil
import tempfile
import logging

# Mute FontBBox errors from pdfminer
logging.getLogger("pdfminer").setLevel(logging.CRITICAL)

st.set_page_config(page_title="Mettle Video Downloader", page_icon="🎥", layout="centered")

# Custom UI styling to make it look premium
st.markdown("""
    <style>
    div.stButton > button:first-child {
        background-color: #2563eb;
        color: white;
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: 600;
        border: none;
        transition: all 0.2s;
        width: 100%;
    }
    div.stButton > button:first-child:hover {
        background-color: #1d4ed8;
        transform: translateY(-2px);
    }
    div.stDownloadButton > button:first-child {
        background-color: #10b981;
        color: white;
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: 600;
        border: none;
        width: 100%;
        transition: all 0.2s;
    }
    div.stDownloadButton > button:first-child:hover {
        background-color: #059669;
        transform: translateY(-2px);
    }
    </style>
""", unsafe_allow_html=True)

st.title("🎥 Mettle Video Downloader")
st.markdown("Upload multiple **PDF reports** to automatically extract and download candidate videos. Once processed, you can download all organized videos in a single ZIP file.")

# File uploader supports selecting multiple files (acts like selecting files inside a folder)
uploaded_files = st.file_uploader("Upload PDF Reports", type=["pdf"], accept_multiple_files=True)

if uploaded_files:
    if st.button("🚀 Start Processing & Download"):
        
        # Make a temporary directory hidden from users so it stays clean
        temp_dir = tempfile.mkdtemp()
        output_dir = os.path.join(temp_dir, "Organized_Videos")
        os.makedirs(output_dir, exist_ok=True)
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        log_container = st.container()
        
        total_files = len(uploaded_files)

        for i, uploaded_file in enumerate(uploaded_files):
            status_text.markdown(f"**Processing ({i+1}/{total_files}):** `{uploaded_file.name}`")
            
            try:
                # Open PDF from uploaded file
                with pdfplumber.open(uploaded_file) as pdf:
                    first_page_text = pdf.pages[0].extract_text()
                    if not first_page_text:
                        log_container.warning(f"⚠️ Could not extract text from {uploaded_file.name}")
                        continue
                        
                    # Try to get text from Page 2 (index 1), fallback to Page 1 (index 0)
                    try:
                        target_page_text = pdf.pages[1].extract_text()
                        if not target_page_text:
                            target_page_text = first_page_text
                    except IndexError:
                        target_page_text = first_page_text
                        
                    lines = target_page_text.split('\n')
                    candidate_name = "Unknown"
                    for line in lines:
                        if "@" in line:
                            # Clean up potential spaces from PDF extraction
                            clean_line = line.replace(" ", "")
                            match = re.search(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', clean_line)
                            if match:
                                candidate_name = match.group(0).lower()
                            else:
                                candidate_name = clean_line.lower()
                            break
                    
                    if candidate_name == "Unknown":
                        # If email still isn't found, try first page as another fallback
                        for line in first_page_text.split('\n'):
                            if "|" in line:
                                candidate_name = line.split('|')[0].strip()
                                break
                            
                    candidate_name = re.sub(r'[\\/*?:"<>|]', "", candidate_name).strip()
                    
                    # 2. Find Links
                    found_links = []
                    for page in pdf.pages:
                        if page.hyperlinks:
                            for link in page.hyperlinks:
                                uri = link.get('uri')
                                if uri and any(k in uri.lower() for k in ["video", "mettl", "s3"]):
                                    found_links.append(uri)
                                    
                    if not found_links:
                        log_container.info(f"ℹ️ No video links found in {uploaded_file.name}")
                        continue
                        
                    # 3. Download Videos to temp folder
                    for j, url in enumerate(found_links[:3], 1):
                        save_filename = f"{candidate_name.lower()}_video_{j}.mp4"
                        save_path = os.path.join(output_dir, save_filename)
                        
                        try:
                            with st.spinner(f"Downloading {save_filename}..."):
                                r = requests.get(url, stream=True, timeout=60)
                                if r.status_code == 200:
                                    with open(save_path, 'wb') as f:
                                        for chunk in r.iter_content(chunk_size=1024*1024):
                                            f.write(chunk)
                                else:
                                    log_container.error(f"❌ HTTP {r.status_code} error for {save_filename}")
                        except Exception as e:
                            log_container.error(f"❌ Error downloading {save_filename}: {e}")
                            
            except Exception as e:
                log_container.error(f"❌ Error reading {uploaded_file.name}: {e}")
                
            progress_bar.progress((i + 1) / total_files)
            
        status_text.success("✅ Processing complete! Zipping files for you to download...")
        
        # 4. Zip all processings and provide download link
        zip_path = os.path.join(temp_dir, "Mettle_Videos.zip")
        shutil.make_archive(zip_path.replace('.zip', ''), 'zip', output_dir)
        
        with open(zip_path, "rb") as fp:
            st.download_button(
                label="⬇️ Download All Videos (ZIP File)",
                data=fp,
                file_name="Mettle_Videos.zip",
                mime="application/zip",
                use_container_width=True
            )
            
        st.balloons()
