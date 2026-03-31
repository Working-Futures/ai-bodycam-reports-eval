import json
import re

# file paths
input_file = "maya_actual.json"
output_file = "maya_filtered.json"

# videos to remove
videos_to_remove = {22, 34, 46, 55, 57, 63, 64, 71, 72, 77, 88}

# load json
with open(input_file, "r") as f:
    data = json.load(f)

filtered_data = {}

for key, value in data.items():
    match = re.match(r"video_(\d+)", key)

    if match:
        video_number = int(match.group(1))

        # remove specific videos
        if video_number in videos_to_remove:
            continue

        # remove videos greater than 91
        if video_number > 91:
            continue

    filtered_data[key] = value

# count remaining videos
video_count = len(filtered_data)

# save cleaned json
with open(output_file, "w") as f:
    json.dump(filtered_data, f, indent=2)

print("Remaining videos:", video_count)