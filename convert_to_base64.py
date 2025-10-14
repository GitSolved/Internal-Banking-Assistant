#!/usr/bin/env python3
"""Temporary script to convert coffee.png to base64"""

import base64

# Read coffee.png
with open(r'C:\Users\Lenovo\Desktop\coffee.png', 'rb') as f:
    img_data = f.read()

# Convert to base64
base64_str = base64.b64encode(img_data).decode('utf-8')

# Create the full data URI
data_uri = f'data:image/png;base64,{base64_str}'

# Save to file
with open('coffee_base64.txt', 'w') as f:
    f.write(data_uri)

print(f"Base64 conversion complete. Length: {len(data_uri)} characters")
print("Saved to coffee_base64.txt")
