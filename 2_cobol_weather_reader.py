#!/usr/bin/env python3
"""
COBOL Weather Map Reader (simulated)
Reads EBCDIC-encoded weather data, outputs ASCII art map.
This simulates the logic of a legacy COBOL program that processes mainframe data.
"""

from pathlib import Path

# Weather symbol legend - how COBOL interprets each character
WEATHER_LEGEND = {
    'T': 'Temp High',
    'R': 'Rain',
    'F': 'Cold Front',
    'H': 'High Pressure',
    'L': 'Low Pressure',
    'C': 'Cloudy',
    'S': 'Snow',
    '.': 'Clear'
}

def ebcdic_decode(data):
    """Decode EBCDIC bytes to text (Cp500 - IBM mainframe standard)"""
    return data.decode('cp500')

def read_ebcdic_file(filename):
    """Read and decode EBCDIC file."""
    with open(filename, 'rb') as f:
        ebcdic_bytes = f.read()
    return ebcdic_decode(ebcdic_bytes)

def render_ascii_map(text_content):
    """
    COBOL-style ASCII weather map rendering.
    Takes the text content and produces a bordered ASCII visualization.
    """
    lines = text_content.strip().split('\n')
    header = lines[0]
    weather_rows = lines[1:]

    # Build ASCII art output
    output = []
    output.append("=" * 50)
    output.append(f"  WEATHER MAP FORECAST  (COBOL Reader)")
    output.append("=" * 50)
    output.append(f"  {header}")
    output.append("-" * 50)

    for row in weather_rows:
        # Render each character with legend
        rendered = ""
        for char in row:
            if char in WEATHER_LEGEND:
                rendered += char
            else:
                rendered += ' '
        output.append(f"  {rendered}")

    output.append("-" * 50)
    output.append("  Legend:")
    for sym, desc in WEATHER_LEGEND.items():
        output.append(f"    {sym} = {desc}")
    output.append("=" * 50)

    return '\n'.join(output) + '\n'

def main():
    """Main COBOL reader process."""
    input_file = 'ebcdic_data/weather_input.ebcdic'
    output_dir = Path('output_cobol')
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / 'weather_map.txt'

    try:
        # Read EBCDIC file
        print(f"[COBOL] Reading EBCDIC file: {input_file}")
        text_content = read_ebcdic_file(input_file)

        # Render ASCII map
        print("[COBOL] Rendering ASCII weather map...")
        ascii_map = render_ascii_map(text_content)

        # Write output
        with open(output_file, 'w') as f:
            f.write(ascii_map)

        print(f"✓ [COBOL] Output written to {output_file}")
        print("\n" + ascii_map)

    except FileNotFoundError as e:
        print(f"✗ [COBOL] Error: {e}")
        return 1

    return 0

if __name__ == '__main__':
    exit(main())
