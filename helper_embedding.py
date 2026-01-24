import onnxruntime as ort
import numpy as np
from transformers import AutoTokenizer

# Load tokenizer and model
tokenizer = AutoTokenizer.from_pretrained("presaved_model")
session = ort.InferenceSession("presaved_model/model.onnx")

def embed(text):
    tokens = tokenizer(text, return_tensors="np", padding="max_length", truncation=True, max_length=128)
    inputs = {
        "input_ids": tokens["input_ids"],
        "attention_mask": tokens["attention_mask"]
    }

    outputs = session.run(None, inputs)
    cls_embedding = outputs[0][0][0]  # [CLS] token embedding
    return cls_embedding

# Example usage
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python onnx_embedder.py 'your query here'")
        exit(1)

    query = sys.argv[1]
    vec = embed(query)
    print("First 5 dimensions:", np.round(vec[:5], 4).tolist())