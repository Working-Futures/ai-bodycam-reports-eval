from google import genai

API_KEY = "YOUR_API_KEY"

client = genai.Client(api_key=API_KEY)

def generate_narrative(input_json_path, output_txt_path):
    # Read the entire JSON file as raw text
    with open(input_json_path, "r") as f:
        json_raw = f.read()

    # Instruction prompt
    instruction = (
        'Using the provided body-worn camera audio transcript, write the "Narrative" '
        'section of a police report from my perspective. Begin with "Narrative:" and write '
        "1-4 paragraphs in first-person past tense. Follow the exact sequence of events: "
        "I responded to the call, arrived at the scene, took action, and concluded the incident. "
        "Use only the information from the audio. If any detail is missing or unclear, use an inline "
        "[INSERT: specific missing detail] placeholder. The output must be a single, continuous "
        "narrative without bullet points or refusal language."
    )

    full_prompt = f"{instruction}\n\nTranscript (JSON):\n{json_raw}"

    response = client.models.generate_content(
        model="gemini-3-pro-preview",
        contents=full_prompt
    )

    # Extract output narrative
    output_text = response.text

    # Save to output file
    with open(output_txt_path, "w") as f:
        f.write(output_text)

    print(f"Saved narrative to {output_txt_path}")


# -----------------------
# Example usage:
# -----------------------

generate_narrative(
    input_json_path="output_json_cleaned.json",
    output_txt_path="output.txt"
)
