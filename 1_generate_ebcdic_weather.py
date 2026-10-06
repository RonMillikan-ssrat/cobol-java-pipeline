#!/usr/bin/env python3
"""
Generate random EBCDIC-encoded weather data files.
Weather symbols: T=temp, R=rain, F=front, H=high, L=low, C=cloud, S=snow, .=clear
"""

import random
import struct
from pathlib import Path
from datetime import datetime

def ebcdic_encode(text):
    """Encode text to EBCDIC (Cp500 - IBM mainframe standard)"""
    return text.encode('cp500')

def generate_weather_map(width=40, height=20, seed=None):
    """Generate a random weather map."""
    if seed is not None:
        random.seed(seed)

    symbols = ['T', 'R', 'F', 'H', 'L', 'C', 'S', '.', '.', '.']  # . is more common (clear)
    weather_map = ''.join(random.choice(symbols) for _ in range(width * height))

    # Reshape into rows
    rows = [weather_map[i*width:(i+1)*width] for i in range(height)]
    return '\n'.join(rows)

def write_ebcdic_file(filename, weather_map):
    """Write weather map to file in EBCDIC format."""
    # Add header: timestamp + metadata
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    header = f"WEATHER_MAP {timestamp} ASCII WEATHER FORECAST\n"

    # Full content in EBCDIC
    content = header + weather_map
    ebcdic_bytes = ebcdic_encode(content)

    with open(filename, 'wb') as f:
        f.write(ebcdic_bytes)

    return len(ebcdic_bytes), content

def main():
    """Generate a test EBCDIC weather file."""
    Path('ebcdic_data').mkdir(exist_ok=True)

    # Generate with a seed for reproducibility
    weather_map = generate_weather_map(width=40, height=20, seed=42)
    filename = 'ebcdic_data/weather_input.ebcdic'
    size, content = write_ebcdic_file(filename, weather_map)

    print(f"✓ Generated {filename} ({size} bytes)")
    print(f"\nInternal content (what's in the EBCDIC file):")
    print(content)

if __name__ == '__main__':
    main()
