import json
import glob
import os

merged_data = {}

# The '**/*.json' pattern with recursive=True tells Python to look inside all subfolders
for filepath in glob.glob("**/*.json", recursive=True):
    with open(filepath, "r", encoding="utf-8") as file:
        try:
            data = json.load(file)
            
            # Format the path to use forward slashes (e.g., "archaeology/desert_well.json")
            clean_path = filepath.replace("\\", "/")
            
            if isinstance(data, dict):
                # Inject the folder and file name as a tracker
                data["_source_file"] = clean_path
                
            # Group under the path name so files with the same name in different folders don't overwrite each other
            merged_data[clean_path] = data
            
        except json.JSONDecodeError:
            print(f"Skipping {filepath} - Not a valid JSON file")

# Output the combined data
with open("merged_output.json", "w", encoding="utf-8") as outfile:
    json.dump(merged_data, outfile, indent=4)

print("Merging complete! Searched all subfolders.")