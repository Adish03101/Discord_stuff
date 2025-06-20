import json
# Replace 'your_file.json' with your actual file path
with open('recordings/932936687988916244_679388060160491542_20250619_204439_timeline.json', 'r') as f:
    data = json.load(f)

# Pretty print the JSON data
import pprint
pprint.pprint(data)