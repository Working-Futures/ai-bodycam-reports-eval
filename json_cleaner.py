import json

def filter_diarized_json(input_file, output_file):
    """
    Loads a diarized JSON file, extracts only the keys:
    'start', 'end', 'text', 'speaker',
    and writes the filtered list to a new JSON file.
    """
    # Load JSON data
    with open(input_file, "r") as f:
        data = json.load(f)

    # Extract only desired keys
    filtered_data = [
        {key: item.get(key) for key in ("start", "end", "text", "speaker") if key in item}
        for item in data
    ]

    # Save filtered data
    with open(output_file, "w") as f:
        json.dump(filtered_data, f, indent=2)

    print(f"Filtered JSON saved to {output_file}")