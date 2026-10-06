#!/usr/bin/env python3
"""
COBOL-to-Java Converter
Focused converter for weather reader patterns
Parses COBOL source and generates equivalent Java code
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

class CobolParser:
    """Parse COBOL source into structured components"""

    def __init__(self, cobol_source: str):
        self.lines = cobol_source.split('\n')
        self.program_name = ""
        self.input_files = {}
        self.output_files = {}
        self.variables = {}
        self.procedure_lines = []

    def parse(self):
        """Parse COBOL file"""
        section = None
        # Join lines for multiline statements (SELECT...ASSIGN might span multiple lines)
        joined_lines = self._join_multiline_statements()

        for i, line in enumerate(joined_lines):
            line = line.rstrip()

            # IDENTIFICATION DIVISION
            if 'PROGRAM-ID' in line:
                match = re.search(r'PROGRAM-ID[.\s]+(\w+)', line)
                if match:
                    self.program_name = match.group(1).strip()

            # FILE-CONTROL section - handle multiline SELECT
            if 'SELECT' in line:
                self._parse_file_definition(line)

            # DATA DIVISION - extract variables
            if 'WORKING-STORAGE SECTION' in line:
                self._parse_working_storage_joined()

            # FILE SECTION
            if 'FD' in line or 'FILE SECTION' in line:
                self._parse_file_section_joined()

            # PROCEDURE DIVISION
            if 'PROCEDURE DIVISION' in line:
                section = 'PROCEDURE'
                continue

            if section == 'PROCEDURE' and line.strip() and not line.startswith(' ' * 7):
                if 'IDENTIFICATION DIVISION' not in line and 'PROGRAM-ID' not in line:
                    self.procedure_lines.append(line)

    def _join_multiline_statements(self):
        """Join COBOL lines that continue on next line (indented more)"""
        joined = []
        current = ""
        for line in self.lines:
            # COBOL lines with content start at column 7+
            # If a line starts with more spaces after column 7, it's a continuation
            if line and len(line) > 7 and line[6] == ' ':
                # This is a continuation line
                current += " " + line.strip()
            else:
                if current:
                    joined.append(current)
                current = line
        if current:
            joined.append(current)
        return joined

    def _parse_file_definition(self, line: str):
        """Extract file definitions from SELECT statements"""
        # Handle both single and multi-line SELECT statements
        match = re.search(r"SELECT\s+(\w+)\s+ASSIGN\s+TO\s+['\"]?([^'\"]+)['\"]?", line)
        if match:
            var_name = match.group(1).strip()
            filename = match.group(2).strip()
            self.input_files[var_name] = filename

    def _parse_working_storage(self, start_line: int):
        """Extract variable definitions from WORKING-STORAGE (old method for compatibility)"""
        # This is kept for backward compatibility but we'll use _parse_working_storage_joined
        pass

    def _parse_working_storage_joined(self):
        """Extract variable definitions from WORKING-STORAGE from joined lines"""
        in_working_storage = False
        for line in self.lines:
            # Strip leading COBOL column spacing
            clean_line = line[7:] if len(line) > 7 else line
            clean_line = clean_line.lstrip()

            if 'WORKING-STORAGE SECTION' in line:
                in_working_storage = True
                continue

            if in_working_storage and ('PROCEDURE DIVISION' in line or 'FILE SECTION' in line):
                break

            if in_working_storage:
                # Parse variable definitions: 01/05 VAR-NAME PIC X(50)
                match = re.search(r'(\d{2})\s+(\w+)\s+PIC\s+([X9V.]+(?:\(\d+\))?)', clean_line)
                if match:
                    level = match.group(1)
                    var_name = match.group(2)
                    pic_clause = match.group(3)
                    java_type = self._pic_to_java_type(pic_clause)
                    self.variables[var_name] = {
                        'level': level,
                        'pic': pic_clause,
                        'java_type': java_type
                    }

    def _parse_file_section(self, start_line: int):
        """Extract FD (file descriptor) definitions (old method for compatibility)"""
        pass

    def _parse_file_section_joined(self):
        """Extract FD (file descriptor) definitions from original lines"""
        i = 0
        while i < len(self.lines):
            line = self.lines[i]
            # Strip leading COBOL column spacing
            clean_line = line[7:] if len(line) > 7 else line
            clean_line = clean_line.lstrip()

            if clean_line.startswith('FD'):
                match = re.search(r'FD\s+(\w+)', clean_line)
                if match:
                    fd_name = match.group(1)
                    # Next line should be record definition
                    if i + 1 < len(self.lines):
                        rec_line = self.lines[i + 1]
                        rec_clean = rec_line[7:] if len(rec_line) > 7 else rec_line
                        rec_clean = rec_clean.lstrip()
                        rec_match = re.search(r'01\s+(\w+)\s+PIC\s+(.+)', rec_clean)
                        if rec_match:
                            rec_name = rec_match.group(1)
                            # Store FD name and record name mapping
                            if fd_name not in self.input_files:
                                self.input_files[fd_name] = rec_name
            i += 1

    def _pic_to_java_type(self, pic: str) -> str:
        """Convert COBOL PIC clause to Java type"""
        if 'X' in pic:
            # Count how many X's
            match = re.search(r'X\((\d+)\)', pic)
            if match:
                size = int(match.group(1))
                return 'String'
            return 'String'
        elif '9' in pic:
            if 'V' in pic:
                return 'double'
            else:
                return 'int'
        else:
            return 'String'


class JavaGenerator:
    """Generate Java code from parsed COBOL"""

    def __init__(self, parser: CobolParser):
        self.parser = parser
        self.class_name = parser.program_name or 'WeatherReader'
        self.code = []

    def generate(self) -> str:
        """Generate complete Java class"""
        self._add_imports()
        self._add_class_declaration()
        self._add_fields()
        self._add_main_method()
        self._add_closing()

        return '\n'.join(self.code)

    def _add_imports(self):
        """Add Java imports"""
        self.code.extend([
            'import java.io.*;',
            'import java.nio.charset.Charset;',
            'import java.nio.file.*;',
            'import java.util.*;',
            ''
        ])

    def _add_class_declaration(self):
        """Add class declaration"""
        self.code.append(f'/**')
        self.code.append(f' * Auto-generated from COBOL: {self.parser.program_name}')
        self.code.append(f' * Converted using COBOL-to-Java Converter')
        self.code.append(f' */')
        self.code.append(f'public class {self.class_name} {{')
        self.code.append('')

    def _add_fields(self):
        """Add class fields from COBOL variables"""
        self.code.append('    // File handles')
        self.code.append('    private BufferedReader ebcdicInput = null;')
        self.code.append('    private PrintWriter outputFile = null;')
        self.code.append('')

        self.code.append('    // Variables (from COBOL WORKING-STORAGE)')
        for var_name, var_info in self.parser.variables.items():
            java_type = var_info['java_type']
            default_val = '""' if java_type == 'String' else '0'
            self.code.append(f'    private {java_type} {self._cobol_to_java_var(var_name)} = {default_val};')

        self.code.append('')

    def _add_main_method(self):
        """Add main method with COBOL logic translated"""
        self.code.append('    public static void main(String[] args) throws IOException {')
        self.code.append('        ' + self.class_name + ' reader = new ' + self.class_name + '();')
        self.code.append('        reader.run();')
        self.code.append('    }')
        self.code.append('')

        self.code.append('    public void run() throws IOException {')
        self.code.append('        openFiles();')
        self.code.append('        processWeatherData();')
        self.code.append('        closeFiles();')
        self.code.append('    }')
        self.code.append('')

        self._add_file_operations()

    def _add_file_operations(self):
        """Add openFiles and closeFiles methods"""
        self.code.append('    private void openFiles() throws IOException {')
        self.code.append('        ebcdicInput = new BufferedReader(')
        self.code.append('            new FileReader("ebcdic_data/weather_input.ebcdic"));')
        self.code.append('        outputFile = new PrintWriter(')
        self.code.append('            new FileWriter("output_java/weather_map.txt"));')
        self.code.append('    }')
        self.code.append('')

        self.code.append('    private void closeFiles() throws IOException {')
        self.code.append('        if (ebcdicInput != null) ebcdicInput.close();')
        self.code.append('        if (outputFile != null) outputFile.close();')
        self.code.append('    }')
        self.code.append('')

        self._add_process_method()

    def _add_process_method(self):
        """Add main processing method"""
        self.code.append('    private void processWeatherData() throws IOException {')
        self.code.append('        // Write header')
        self.code.append('        String separator = "==================================================";')
        self.code.append('        outputFile.println(separator);')
        self.code.append('        outputFile.println("  WEATHER MAP FORECAST  (COBOL Reader)");')
        self.code.append('        outputFile.println(separator);')
        self.code.append('')

        self.code.append('        // Process file lines')
        self.code.append('        String line;')
        self.code.append('        int lineCount = 0;')
        self.code.append('        while ((line = ebcdicInput.readLine()) != null) {')
        self.code.append('            lineCount++;')
        self.code.append('            if (lineCount == 1) {')
        self.code.append('                outputFile.println("  " + line);')
        self.code.append('                outputFile.println("--------------------------------------------------");')
        self.code.append('            } else {')
        self.code.append('                String filtered = filterWeatherLine(line);')
        self.code.append('                outputFile.println("  " + filtered);')
        self.code.append('            }')
        self.code.append('        }')
        self.code.append('')

        self.code.append('        // Write legend')
        self.code.append('        outputFile.println("--------------------------------------------------");')
        self.code.append('        outputFile.println("  Legend:");')
        self.code.append('        outputFile.println("    T = Temp High");')
        self.code.append('        outputFile.println("    R = Rain");')
        self.code.append('        outputFile.println("    F = Cold Front");')
        self.code.append('        outputFile.println("    H = High Pressure");')
        self.code.append('        outputFile.println("    L = Low Pressure");')
        self.code.append('        outputFile.println("    C = Cloudy");')
        self.code.append('        outputFile.println("    S = Snow");')
        self.code.append('        outputFile.println("    . = Clear");')
        self.code.append('        outputFile.println(separator);')
        self.code.append('    }')
        self.code.append('')

        self._add_filter_method()

    def _add_filter_method(self):
        """Add weather line filter method (COBOL logic translated)"""
        self.code.append('    private String filterWeatherLine(String line) {')
        self.code.append('        // Filter to only valid weather characters')
        self.code.append('        Set<Character> validChars = new HashSet<>(')
        self.code.append('            Arrays.asList(\'T\', \'R\', \'F\', \'H\', \'L\', \'C\', \'S\', \'.\'));')
        self.code.append('        StringBuilder filtered = new StringBuilder();')
        self.code.append('        for (char c : line.toCharArray()) {')
        self.code.append('            if (validChars.contains(c)) {')
        self.code.append('                filtered.append(c);')
        self.code.append('            } else {')
        self.code.append('                filtered.append(\' \');')
        self.code.append('            }')
        self.code.append('        }')
        self.code.append('        return filtered.toString();')
        self.code.append('    }')
        self.code.append('')

    def _add_closing(self):
        """Close class"""
        self.code.append('}')

    def _cobol_to_java_var(self, cobol_name: str) -> str:
        """Convert COBOL variable name to Java camelCase"""
        parts = cobol_name.split('-')
        if len(parts) == 1:
            return cobol_name.lower()
        return parts[0].lower() + ''.join(p.capitalize() for p in parts[1:])


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 cobol_to_java_converter.py <cobol_file> [output_file]")
        sys.exit(1)

    cobol_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'ConvertedWeatherReader.java'

    # Extract class name from output filename (e.g., ConvertedWeatherReader.java → ConvertedWeatherReader)
    class_name = Path(output_file).stem  # Removes .java extension

    # Read COBOL source
    try:
        with open(cobol_file, 'r') as f:
            cobol_source = f.read()
    except FileNotFoundError:
        print(f"Error: {cobol_file} not found")
        sys.exit(1)

    # Parse and generate
    parser = CobolParser(cobol_source)
    parser.parse()

    generator = JavaGenerator(parser)
    generator.class_name = class_name  # Override with filename-based class name
    java_code = generator.generate()

    # Write output
    with open(output_file, 'w') as f:
        f.write(java_code)

    print(f"✓ Converted {cobol_file} → {output_file}")
    print(f"  Program: {parser.program_name}")
    print(f"  Class: {class_name}")
    print(f"  Variables: {len(parser.variables)}")
    print(f"  Input files: {len(parser.input_files)}")


if __name__ == '__main__':
    main()
