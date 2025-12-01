from jiwer import wer, Compose, RemovePunctuation, ToLowerCase, RemoveMultipleSpaces, Strip

# Preprocessing pipeline
transform = Compose([
    ToLowerCase(),
    RemovePunctuation(),
    RemoveMultipleSpaces(),
    Strip()
])

def compute_wer(reference_file, hypothesis_file):
    """
    Computes the Word Error Rate (WER) between a ground truth file
    and a hypothesis file using a fixed preprocessing pipeline.
    """
    # Load files
    with open(reference_file, "r") as f:
        reference = f.read()
    with open(hypothesis_file, "r") as f:
        hypothesis = f.read()

    # Apply preprocessing
    reference_processed = transform(reference)
    hypothesis_processed = transform(hypothesis)

    # Compute WER
    error = wer(reference_processed, hypothesis_processed)
    print(f"Word Error Rate (WER): {error:.3f}")
    return error
