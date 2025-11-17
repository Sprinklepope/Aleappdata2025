import sqlite3
import subprocess
import os
import argparse
import sys
import webbrowser
import re
import pandas as pd
import plotly.express as px
from datetime import datetime
import time  # For timestamped output files
import numpy as np

def detect_input_type(path):
    if os.path.isdir(path): #First we need to check if path is a folder (fs)
        return "fs"  #ALEAPP flag for file system directory input
    ext = os.path.splitext(path)[1].lower()  #splits tuple 0.1
    #checks if the extension is one ALEAPP supports
    if ext == '.zip':
        return 'zip'
    elif ext == '.tar':
        return 'tar'
    elif ext in ['.gz', '.tgz']:
        return 'gz'
    else:
        raise ValueError(f"Unsupported input type or archive extension: {ext}")

def run_aleapp(input_path, output_path): #defines the function to run ALEAPP -> Returns report path

    aleapp_dir = os.path.join(os.getcwd(), "ALEAPP") #sets the directory path to the ALEAPP folder inside the current working directory

    if not os.path.isdir(aleapp_dir):
        raise FileNotFoundError(f"The directory {aleapp_dir} does not exist.")

    inputtype = detect_input_type(input_path)
    original_dir = os.getcwd() #Saves current working directory and changes into ALEAPP directory -> important so we can go back to the original directory later
    os.chdir(aleapp_dir)        #This is necessary because ALEAPP is run via subprocess as 'python aleapp.py', which assumes we are inside the folder containing aleapp.py

    command = [
        "python", "aleapp.py",
        "-t", inputtype, #zip, tar, fs, gz
        "-o", output_path,
        "-i", input_path
    ]

    try:
        #runs ALEAPP as if you're typing a command in the terminal
        result = subprocess.run(command, text=True, capture_output=True, check=True)
        print("Command Output:", result.stdout) #prints ALEAPP's standard output
        #print("Command Error:", result.stderr) #and error logs      #debug

        #looks for the line in stdout containing 'Report location:'
        report_location_line = [line for line in result.stdout.splitlines() if "Report location:" in line]
        if report_location_line:
            report_location = report_location_line[0].split("Report location:")[1].strip()
            return report_location #extracts and returns actual report path
        else:
            print("Report location not found in output.")
    except subprocess.CalledProcessError as e:
        print(f"Command failed with exit code {e.returncode}")
        print("Command Output:", e.stdout)
        # print("Command Error:", e.stderr)
    finally:
        os.chdir(original_dir) #restore original directory (get out of ALEAPP folder) to avoid breaking any path references after we're done

def list_output_files(report_location): #list the report files, using the location we found by running ALEAPP
    if os.path.exists(report_location):
        files = os.listdir(report_location)
        print("Generated Report Files:")
        for file in files:
            print(file)
    else:
        print(f"The directory {report_location} does not exist.")

                            #report location + "/_Timeline/tl.db"
def extract_data_from_db(db_path, start_time, end_time):
    if not os.path.exists(db_path): #validate database exists
        print(f"The file {db_path} does not exist.")
        return pd.DataFrame()

    conn = sqlite3.connect(db_path) #open a connection and creates a cursor
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    if not tables:
        print("No tables found in database.")
        conn.close()
        return pd.DataFrame()

    table_name = tables[0][0] #Asssume the first table (there should only be one named 'data')

    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall() #each row is a tuple (key, activity, datalist)
    conn.close()

    if not rows:
        print(f"No rows found in table {table_name}.")
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=["key", "activity", "datalist"])
    df["raw_key"] = df["key"].astype(str)

    #Safely parse timestamps from "key" field
    def safe_parse(dt_str):
        try:
            #First try: direct ISO8601 / standard parsing with UTC
            return pd.to_datetime(dt_str, utc=True)
        except Exception:
            #If parsing fails, try stripping off "+timezone" info
            dt_clean = re.sub(r'\+.*$', '', dt_str)
            try:
                return pd.to_datetime(dt_clean, utc=True)
            except Exception:
                #Give up -> mark as Not-a-Time
                return pd.NaT

    #Apply timestamp parser to each row
    df["parsed_key"] = df["raw_key"].apply(safe_parse)

    #Filter rows by requested time window
    start_dt = pd.to_datetime(start_time, utc=True)
    end_dt = pd.to_datetime(end_time, utc=True)

    df_filtered = df[(df["parsed_key"] >= start_dt) & (df["parsed_key"] <= end_dt)].copy()

    #Reporting and return
    if df_filtered.empty:
        print("No data found for the specified time range, but returning all rows with raw timestamps.")
    else:
        print(f"Retrieved {len(df_filtered)} rows within the time range.")

    #Reset index before returning (tidy DataFrame)
    return df_filtered.reset_index(drop=True)


def read_device_info_html(report_location): #reads DeviceInfo.html so it can be embedded in the timeline
    device_info_path = os.path.join(report_location, "Script Logs", "DeviceInfo.html") #build path
    if os.path.exists(device_info_path):
        with open(device_info_path, "r", encoding="utf-8") as f: #reads entire file content into string
            return f.read()
    else:
        print(f"DeviceInfo.html not found at {device_info_path}")
        return "<p>Device info not available.</p>"

def create_timeline_from_dataframe(df, csv_output, html_output, device_info_html, report_location):
    if df.empty:
        print("The DataFrame is empty. No timeline to generate.")
        return

    #Use parsed_key for timeline
    df["key"] = df["parsed_key"]
    df = df.dropna(subset=["key"]).copy()
    df["key"] = df["key"].dt.strftime('%Y-%m-%d %H:%M:%S')

    #Clean datalist and preview
    df["datalist"] = df["datalist"].str.replace(r'\s+', ' ', regex=True).str.strip()
    # Create short preview (first 100 chars + "…")
    df["Preview"] = df["datalist"].str.slice(0, 100)
    df["Preview"] = df["Preview"].astype(str) + df["datalist"].apply(lambda x: "…" if len(str(x)) > 100 else "")
    # Escape < > to avoid HTML rendering issues
    df["Preview"] = df["Preview"].str.replace("<", "&lt;").str.replace(">", "&gt;")

    df["ActivityLabel"] = df["activity"].str.slice(0, 40)

    #Save CSV
    df.to_csv(csv_output, index=False)
    print(f"CSV timeline saved to: {csv_output}")

    #Dynamic chart height based on unique activities
    unique_activities = df["ActivityLabel"].nunique()
    chart_height = max(700, unique_activities * 20)  # 20px per activity, min 700px

    #Ensure all activities appear as categories
    df["ActivityLabel"] = pd.Categorical(df["ActivityLabel"], categories=df["ActivityLabel"].unique(), ordered=True)

    # --- Create Plotly scatter chart ---
    fig = px.scatter(
        df,
        x="key",
        y="ActivityLabel",
        opacity=0.75,
        color_discrete_sequence=["#007acc"],
        labels={"key": "Timestamp", "ActivityLabel": "Activity"},
        hover_data={"Preview": True}  # only show truncated preview
    )

    # Assign customdata for click-to-expand functionality
    fig.update_traces(
        marker=dict(size=8, symbol='circle'),
        customdata=df[["datalist"]].values,  # full datalist for click display
        hovertemplate="<b>%{y}</b><br>%{x}<br><b>Preview:</b> %{customdata[0]}<extra></extra>"
    )

    # ✅ FIX: use truncated Preview instead of full datalist in hover
    fig.update_traces(
        customdata=np.stack((df["datalist"], df["Preview"]), axis=-1),  # [0]=full, [1]=preview
        hovertemplate="<b>%{y}</b><br>%{x}<br><b>Preview:</b> %{customdata[1]}<extra></extra>"
    )

    fig.update_yaxes(
        autorange="reversed",
        categoryorder="array",
        categoryarray=df["ActivityLabel"].cat.categories  # all labels appear
    )

    html_core = fig.to_html(full_html=False, include_plotlyjs='cdn')

    # Build the full path to ALEAPP's index.html
    aleapp_index_path = os.path.join(report_location, "index.html")

    full_html = f"""
    <html>
    <head>
        <title>ALEAPP Timeline</title>
        <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
            }}
            .timeline {{
                width: 100%;
                height: {chart_height}px;
                margin-bottom: 20px;
            }}
            .bottom-container {{
                display: flex;
                gap: 20px;
                align-items: flex-start;
            }}
            .device-info {{
                border: 1px solid #ccc;
                padding: 10px;
                background: #f8f8f8;
                width: 350px;
                height: 400px;
                overflow-y: auto;
                box-sizing: border-box;
                font-size: 14px;
                white-space: normal;
                flex-shrink: 0;
            }}
            .clicked-event-box {{
                border: 1px solid #ccc;
                padding: 10px;
                font-size: 14px;
                width: 750px;
                height: 400px;
                overflow-y: auto;
                box-sizing: border-box;
                white-space: normal;
                flex-shrink: 0;
            }}
            .aleapp-button {{
                display: inline-block;
                margin: 15px 0;
                padding: 10px 20px;
                font-size: 16px;
                background-color: #007acc;
                color: white;
                border: none;
                border-radius: 6px;
                cursor: pointer;
            }}
            .aleapp-button:hover {{
                background-color: #005fa3;
            }}
        </style>
    </head>
    <body>
        <h2>📊 ALEAPP Timeline from Extracted Data</h2>

        <!-- Button to open ALEAPP index.html -->
        <button class="aleapp-button" onclick="window.open('file://{aleapp_index_path}', '_blank')">
            Open Full ALEAPP Report
        </button>

        <div class="timeline">
            {html_core}
        </div>

        <div class="bottom-container">
            <div class="device-info">
                <h3>Device Details</h3>
                {device_info_html}
            </div>
            <div id="details" class="clicked-event-box">
                <h3>Clicked Event</h3>
                <p>Click on a timeline point to see details here.</p>
            </div>
        </div>

        <script>
            var plot = document.querySelectorAll(".js-plotly-plot")[0];
            plot.on('plotly_click', function(data) {{
                var fullText = data.points[0].customdata[0];  // full datalist
                var activity = data.points[0].y;
                var timestamp = data.points[0].x;

                document.getElementById('details').innerHTML =
                    '<h3>Clicked Event</h3>' +
                    '<b>Timestamp:</b> ' + timestamp + '<br>' +
                    '<b>Activity:</b> ' + activity + '<br><br>' +
                    '<b>Full datalist:</b><br>' +
                    '<div style="max-height: 300px; overflow-y: auto; border:1px solid #eee; padding:10px; background:#f8f8f8; font-family: monospace; white-space: pre-wrap;">' +
                    fullText.replace(/</g, "&lt;").replace(/>/g, "&gt;") +
                    '</div>';
            }});
        </script>
    </body>
    </html>
    """

    with open(html_output, "w", encoding="utf-8") as f:
        f.write(full_html)

    print(f"Timeline chart saved to: {html_output}")
    webbrowser.open(f"file://{html_output}")


def parse_datetime(dt_str):
    #Parse a datetime string in the format YYYY-MM-DD HH:MM:SS.
    #Returns a string formatted as such if valid, else None.
    if not dt_str:
        return None
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        print(f"Error: Invalid datetime format '{dt_str}'. Expected 'YYYY-MM-DD HH:MM:SS'.")
        return None

def masters():
    #creates argument parser so the script can run from the command line
    parser = argparse.ArgumentParser(description="Run ALEAPP and generate a timeline visualization.") #--help
    parser.add_argument("--start", required=False, default="2024-07-13 18:00:00",
                        help="Start time (format: YYYY-MM-DD HH:MM:SS)")


    parser.add_argument("--end", required=False, default="2024-07-16 18:00:00",
                        help="End time (format: YYYY-MM-DD HH:MM:SS)")

    parser.add_argument("--input", required=False, default=None,
                        help="Input file/folder path (zip/tar/fs directory)")
    parser.add_argument("--output", required=False, default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "Output"),
                        help="Output folder for ALEAPP report")

    args = parser.parse_args() #reads arguments passed
    output_path = args.output
    input_path = args.input

    if input_path is None:
        input_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Input")
        print(input_folder)
        entries = os.listdir(input_folder)

        if not entries:
            print("No files or folders found in the input folder.")
            sys.exit(1)

        print("\nAvailable input options:")
        for i, name in enumerate(entries, start=1):
            full_path = os.path.join(input_folder, name)
            entry_type = "Folder" if os.path.isdir(full_path) else "File"
            print(f"{i}. {name} ({entry_type})")

        while True:
            try:
                choice = int(input(f"\nSelect an option by number (1-{len(entries)}): "))
                if 1 <= choice <= len(entries):
                    break
                else:
                    print("Invalid number, try again.")
            except ValueError:
                print("Please enter a valid number.")

        input_path = os.path.join(input_folder, entries[choice - 1])
        print(f"Selected input: {input_path}")
    else:
        print(f"Using input path from argument: {input_path}")

    #Parse initial timeline times
    start_time = parse_datetime(args.start)
    end_time = parse_datetime(args.end)
    if start_time is None or end_time is None:
        print("Invalid initial time parameters. Exiting.")
        sys.exit(1)

    # --- INITIALIZE PROCESSING TIMERS ---
    total_processing_time = 0.0
    cumulative_data_time = 0.0
    cumulative_timeline_time = 0.0

    # --- ALEAPP SUBPROCESS ---
    print("\n[Timer Start] ALEAPP subprocess")
    aleapp_start_time = time.time()
    report_location = run_aleapp(input_path, output_path)
    aleapp_end_time = time.time()
    aleapp_duration = aleapp_end_time - aleapp_start_time
    total_processing_time += aleapp_duration
    print(f"[Timer End] ALEAPP subprocess completed in {aleapp_duration:.2f} seconds.")

    if not report_location:
        print("No report location returned from ALEAPP. Exiting.")
        sys.exit(1)

    db_path = os.path.join(report_location, "_Timeline", "tl.db")
    device_info_html = read_device_info_html(report_location)

    # --- FIRST TIMELINE ---
    print(f"\nGenerating initial timeline for: {start_time} → {end_time}")

    print("[Timer Start] Data extraction/filtering")
    data_start_time = time.time()

    df = extract_data_from_db(db_path, start_time, end_time)

    data_end_time = time.time()
    data_duration = data_end_time - data_start_time
    cumulative_data_time += data_duration
    total_processing_time += data_duration
    print(f"[Timer End] Data extraction/filtering completed in {data_duration:.2f} seconds.")

    print("[Timer Start] Timeline generation")
    timeline_start_time = time.time()

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    csv_output = os.path.join(output_path, f"timeline_{timestamp}.csv")
    html_output = os.path.join(output_path, f"timeline_{timestamp}.html")
    create_timeline_from_dataframe(df, csv_output, html_output, device_info_html, report_location)

    timeline_end_time = time.time()
    timeline_duration = timeline_end_time - timeline_start_time
    cumulative_timeline_time += timeline_duration
    total_processing_time += timeline_duration
    print(f"[Timer End] Timeline generation completed in {timeline_duration:.2f} seconds.")

    # --- LOOP FOR ADDITIONAL TIMELINES ---
    while True:
        again = input("\nDo you want to generate another timeline with a different timeframe? (y/n): ").lower()
        if again != "y":
            break

        start_time_new = input(f"Enter start time (YYYY-MM-DD HH:MM:SS) [default: {args.start}]: ") or args.start
        end_time_new = input(f"Enter end time (YYYY-MM-DD HH:MM:SS) [default: {args.end}]: ") or args.end

        start_time_parsed = parse_datetime(start_time_new)
        end_time_parsed = parse_datetime(end_time_new)

        if start_time_parsed is None or end_time_parsed is None:
            print("Invalid datetime format. Please try again.")
            continue

        print(f"\nGenerating timeline for: {start_time_parsed} → {end_time_parsed}")

        # Data extraction/filtering
        print("[Timer Start] Data extraction/filtering")
        data_start_time = time.time()

        df = extract_data_from_db(db_path, start_time_parsed, end_time_parsed)

        data_end_time = time.time()
        data_duration = data_end_time - data_start_time
        cumulative_data_time += data_duration
        total_processing_time += data_duration
        print(f"[Timer End] Data extraction/filtering completed in {data_duration:.2f} seconds.")

        # Timeline generation
        print("[Timer Start] Timeline generation")
        timeline_start_time = time.time()

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        csv_output = os.path.join(output_path, f"timeline_{timestamp}.csv")
        html_output = os.path.join(output_path, f"timeline_{timestamp}.html")
        create_timeline_from_dataframe(df, csv_output, html_output, device_info_html, report_location)

        timeline_end_time = time.time()
        timeline_duration = timeline_end_time - timeline_start_time
        cumulative_timeline_time += timeline_duration
        total_processing_time += timeline_duration
        print(f"[Timer End] Timeline generation completed in {timeline_duration:.2f} seconds.")

    #FINAL REPORT OF TIMINGS
    print("\n=== Processing Summary (excluding user input) ===")
    print(f"ALEAPP Runtime: {aleapp_duration:.2f} seconds")
    print(f"Automation Script Runtime: {cumulative_data_time:.2f} seconds")
    print(f"Timeline Generation Runtime: {cumulative_timeline_time:.2f} seconds")
    print(f"Total Processing Runtime: {total_processing_time:.2f} seconds")



if __name__ == "__main__":
    masters()


