ALEAPP Data Timeline Automation (Masters Project)

This project automates the processing of Android forensic data using ALEAPP (Android Logs, Events, and App Parser Program).
It runs ALEAPP on a chosen input, extracts the generated timeline database, filters events by timestamp, and produces both CSV and interactive HTML timeline visualisations

Requirements

+ Python 3.9 or above
+ Important: Install ALEAPP Before Running

  This project does not include ALEAPP.

  You must download ALEAPP from the official repository, then place its contents into the provided ALEAPP/ folder in this project.
  https://github.com/abrignoni/ALEAPP

  - Download ZIP
  - Click Code → Download ZIP on the ALEAPP GitHub page.
  - Extract the ZIP.
  - Open the extracted folder.
  - Copy all its contents (e.g., aleapp.py, modules/, etc.).
  - Paste them into the existing ALEAPP/ folder in this project (located next to masters.py).

  If you prefer using Git, you can clone the ALEAPP repository directly into your project

+ Dependencies
  - pip install -r requirements.txt
  
How to run the program: 

Navigate to the project folder
Command:
cd Aleappdata2025

Run the script (default mode)

By default, the program automatically uses this folder:
Aleappdata2025/Input/
Place your Android extraction archive(s) into this folder.
The program will detect the most recently added file and process it automatically.
All ALEAPP reports and generated timeline data are saved to:
Aleappdata2025/Output/
Timeline results and charts will be generated in the same directory.

Without arguments, the script will: 
- Look inside the Input/ folder for extraction archives.
- Store all outputs in the Output/ folder.
Command:
python masters.py  --start "YYYY-MM-DD HH:MM:SS" --end "YYYY-MM-DD HH:MM:SS"

Optional: Provide a Custom Input Path or Output path

You can also specify a custom file or folder directly when running the script:

python masters.py --input /path/to/your/extraction.zip --output /path/to/your/output --start "YYYY-MM-DD HH:MM:SS" --end "YYYY-MM-DD HH:MM:SS"








