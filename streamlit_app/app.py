import streamlit as st
import sys
import os
import logging

# --- NUCLEAR MONKEYPATCH (START) ---
# We are going to trick diyepw into thinking it successfully created its log folder.
# This code MUST run before "import diyepw".

# 1. Define a fake "FileHandler" that accepts any arguments but does nothing.
class NullFileHandler(logging.Handler):
    def __init__(self, *args, **kwargs):
        super().__init__()
    def emit(self, record):
        pass

# 2. Define a fake "mkdir" that accepts any path but does nothing.
def fake_mkdir(path, mode=0o777, *, dir_fd=None):
    return # Just pretend we did it

# 3. Save the real functions so we can restore them later.
real_mkdir = os.mkdir
real_file_handler = logging.FileHandler

# 4. Apply the fake functions.
os.mkdir = fake_mkdir
logging.FileHandler = NullFileHandler

try:
    # 5. Import the library. It will try to use our fake functions and succeed.
    import diyepw
except Exception as e:
    st.error(f"Critical Import Error: {e}")

# 6. RESTORE the real functions immediately.
# This ensures the rest of your app (and Streamlit) works normally.
os.mkdir = real_mkdir
logging.FileHandler = real_file_handler
# --- NUCLEAR MONKEYPATCH (END) ---

import tempfile
from pathlib import Path
from datetime import datetime

# --- APP CONFIG ---
st.set_page_config(page_title="AMY EPW Generator", page_icon="🌤️")

# --- CORE FUNCTION ---
def generate_epw_safe(wmo, year, output_dir):
    try:
        diyepw.create_amy_epw_files_for_years_and_wmos(
            [int(year)],
            [int(wmo)],
            max_records_to_interpolate=100,
            max_records_to_impute=50,
            max_missing_amy_rows=50,
            allow_downloads=True,
            amy_epw_dir=output_dir,
        )
        return True
    except Exception as e:
        return str(e)

# --- UI LAYOUT ---
st.title("🌤️ AMY EPW Weather Generator")
st.markdown("Generates Actual Meteorological Year (AMY) files for EnergyPlus using NOAA data.")

with st.form("main_form"):
    col1, col2 = st.columns(2)
    with col1:
        wmo_input = st.text_input("WMO Station Number", value="722950")
    with col2:
        year_input = st.number_input("Year", min_value=1990, max_value=2025, value=2023)
    
    submitted = st.form_submit_button("Generate File")

if submitted:
    # We use a TemporaryDirectory so we don't need write permissions to the system
    with tempfile.TemporaryDirectory() as temp_dir:
        with st.status("Downloading data from NOAA...", expanded=True) as status:
            
            result = generate_epw_safe(wmo_input, year_input, temp_dir)
            
            if result is True:
                # Find the generated EPW file
                generated_files = list(Path(temp_dir).glob("*.epw"))
                
                if generated_files:
                    status.update(label="Complete!", state="complete", expanded=False)
                    target_file = generated_files[0]
                    
                    # Read file into memory for download
                    with open(target_file, "rb") as f:
                        file_data = f.read()
                        
                    st.success(f"Generated: {target_file.name}")
                    st.download_button(
                        label="📥 Download EPW",
                        data=file_data,
                        file_name=target_file.name,
                        mime="text/plain"
                    )
                else:
                    status.update(label="Error: No file created.", state="error")
                    st.error("The generator finished but no file was found. The NOAA data might be missing for this year.")
            else:
                status.update(label="Error during generation.", state="error")
                st.error(f"Error details: {result}")