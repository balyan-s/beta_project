from datasets import load_dataset
import json

def inspect_raw_data():
    print("Loading dataset...")
    dataset = load_dataset("amazon/AmazonQAC", split="train", streaming=True)
    
    # Grab the very first row
    sample = next(iter(dataset))
    
    print("\n--- RAW DATA DICTIONARY ---")
    # Print it beautifully so we can see all columns and arrays
    print(json.dumps(sample, indent=2, default=str))

if __name__ == "__main__":
    inspect_raw_data()