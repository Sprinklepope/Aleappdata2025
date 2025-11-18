ALEAPP Data Timeline Automation (Masters Project)

This project automates the processing of Android forensic data using ALEAPP (Android Logs, Events, and App Parser Program).
It runs ALEAPP on a chosen input, extracts the generated timeline database, filters events by timestamp, and produces both CSV and interactive HTML timeline visualisations

Structure

Aleappdata2025/
│
├── masters.py           # Main automation script
├── ALEAPP/              # You must place ALEAPP here
│   ├── aleapp.py
│   ├── modules/
│   └── other ALEAPP files...
├── Input/               # Place your input data here (folder, zip, tar, gz)
├── Output/              # Script-generated ALEAPP reports + timelines
├── requirements.txt
└── README.md

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

Once ALEAPP is installed into the ALEAPP/ folder and your Input/ folder contains at least one extraction archive, you can run the program from the terminal.

1. Navigate to the project folder
cd Aleappdata2025

2. Run the main script
python masters.py

- Input Folder
By default, the program automatically uses this folder:
Aleappdata2025/Input/
Place your Android extraction archive(s) into this folder.
The program will detect the most recently added file and process it automatically.

Output Folder
All ALEAPP reports and generated timeline data are saved to:
Aleappdata2025/Output/
Timeline results and charts will be generated in the same directory.

Optional: Provide a Custom Input Path

You can also specify a custom file or folder directly when running the script:

python masters.py --input /path/to/your/extraction.zip --starttime --endtime

If no --input argument is supplied, the script defaults to scanning the Input/ folder.






