#!/usr/bin/env python3
"""
Output Comparison Engine
Compares COBOL and Java weather map outputs for validation.
Generates detailed comparison report and statistics.
"""

import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def read_output_file(filepath):
    """Read output file and return lines."""
    with open(filepath, 'r') as f:
        return f.readlines()

def extract_weather_map(lines):
    """Extract just the weather data rows (skip headers/footers/legend)."""
    map_rows = []
    in_map = False
    for line in lines:
        line = line.rstrip('\n')
        # Start after header separator
        if line.startswith('-' * 50):
            in_map = not in_map
            continue
        # Stop at end separator
        if line.startswith('=' * 50):
            in_map = False
        # Collect map rows
        if in_map and line.strip() and not line.startswith('Legend'):
            # Extract just the weather characters (strip leading whitespace)
            weather_chars = line.strip()
            if weather_chars and weather_chars[0] not in ['=', '-']:
                map_rows.append(weather_chars)
    return map_rows

def compare_outputs(cobol_file, java_file):
    """Compare COBOL and Java outputs."""
    cobol_lines = read_output_file(cobol_file)
    java_lines = read_output_file(java_file)

    # Extract weather maps
    cobol_map = extract_weather_map(cobol_lines)
    java_map = extract_weather_map(java_lines)

    comparison = {
        'timestamp': datetime.now().isoformat(),
        'files': {
            'cobol': str(cobol_file),
            'java': str(java_file)
        },
        'line_counts': {
            'cobol': len(cobol_lines),
            'java': len(java_lines),
            'cobol_map_rows': len(cobol_map),
            'java_map_rows': len(java_map)
        },
        'character_counts': {
            'cobol': sum(len(line) for line in cobol_lines),
            'java': sum(len(line) for line in java_lines),
            'cobol_map': sum(len(row) for row in cobol_map),
            'java_map': sum(len(row) for row in java_map)
        },
        'differences': [],
        'statistics': {}
    }

    # Compare line by line
    max_lines = max(len(cobol_lines), len(java_lines))
    matching_lines = 0

    for i in range(max_lines):
        cobol_line = cobol_lines[i].rstrip('\n') if i < len(cobol_lines) else None
        java_line = java_lines[i].rstrip('\n') if i < len(java_lines) else None

        if cobol_line != java_line:
            comparison['differences'].append({
                'line_num': i + 1,
                'cobol': cobol_line,
                'java': java_line,
                'cobol_len': len(cobol_line) if cobol_line else 0,
                'java_len': len(java_line) if java_line else 0
            })
        else:
            matching_lines += 1

    # Calculate statistics
    comparison['statistics'] = {
        'total_lines': max_lines,
        'matching_lines': matching_lines,
        'different_lines': len(comparison['differences']),
        'match_percentage': round((matching_lines / max_lines * 100) if max_lines > 0 else 0, 2)
    }

    # Weather map specific comparison
    if len(cobol_map) == len(java_map):
        map_matching_chars = 0
        map_total_chars = 0
        for cobol_row, java_row in zip(cobol_map, java_map):
            for c1, c2 in zip(cobol_row, java_row):
                map_total_chars += 1
                if c1 == c2:
                    map_matching_chars += 1

        comparison['statistics']['weather_map_match_percentage'] = round(
            (map_matching_chars / map_total_chars * 100) if map_total_chars > 0 else 0, 2
        )
        comparison['statistics']['weather_map_total_chars'] = map_total_chars
        comparison['statistics']['weather_map_matching_chars'] = map_matching_chars

    return comparison

def analyze_differences(comparison):
    """Analyze differences and generate insights."""
    analysis = {
        'verdict': 'PASS',
        'summary': '',
        'issues': [],
        'insights': []
    }

    diffs = comparison['differences']
    stats = comparison['statistics']

    if stats['different_lines'] == 0:
        analysis['summary'] = 'Perfect match! COBOL and Java outputs are identical.'
        analysis['verdict'] = 'PASS'
    else:
        analysis['verdict'] = 'FAIL'
        analysis['summary'] = f"{stats['different_lines']} out of {stats['total_lines']} lines differ ({100 - stats['match_percentage']}% mismatch)."

        # Categorize issues
        legend_diffs = [d for d in diffs if 'Legend' in str(d.get('cobol', '')) or 'Legend' in str(d.get('java', ''))]
        header_diffs = [d for d in diffs if any(x in str(d.get('cobol', '')) or x in str(d.get('java', ''))
                                                 for x in ['==', 'WEATHER MAP'])]
        content_diffs = [d for d in diffs if d not in legend_diffs and d not in header_diffs]

        if legend_diffs:
            analysis['issues'].append({
                'type': 'Legend order difference',
                'count': len(legend_diffs),
                'severity': 'low',
                'note': 'Legend order differs (HashMap vs insertion order) but content is same'
            })

        if header_diffs:
            analysis['issues'].append({
                'type': 'Header/footer difference',
                'count': len(header_diffs),
                'severity': 'low',
                'note': 'Minor formatting differences in headers'
            })

        if content_diffs:
            analysis['issues'].append({
                'type': 'Weather map data mismatch',
                'count': len(content_diffs),
                'severity': 'high',
                'note': 'Critical: weather map data does not match'
            })

        # Insights
        if stats.get('weather_map_match_percentage', 100) < 100:
            analysis['insights'].append(f"Weather map match: {stats.get('weather_map_match_percentage', 'N/A')}%")

        analysis['insights'].append(f"Match rate: {stats['match_percentage']}%")

    return analysis

def generate_report(comparison, output_file):
    """Generate human-readable comparison report."""
    analysis = analyze_differences(comparison)

    report_lines = []
    report_lines.append("=" * 70)
    report_lines.append("COBOL-to-JAVA WEATHER MAP CONVERSION VALIDATION REPORT")
    report_lines.append("=" * 70)
    report_lines.append("")
    report_lines.append(f"Generated: {comparison['timestamp']}")
    report_lines.append(f"COBOL Output: {comparison['files']['cobol']}")
    report_lines.append(f"Java Output:  {comparison['files']['java']}")
    report_lines.append("")

    # Verdict
    report_lines.append(f"VERDICT: {analysis['verdict']}")
    report_lines.append(f"Summary: {analysis['summary']}")
    report_lines.append("")

    # Statistics
    report_lines.append("STATISTICS")
    report_lines.append("-" * 70)
    for key, value in comparison['statistics'].items():
        report_lines.append(f"  {key:.<50} {value}")
    report_lines.append("")

    # Issues
    if analysis['issues']:
        report_lines.append("ISSUES FOUND")
        report_lines.append("-" * 70)
        for issue in analysis['issues']:
            report_lines.append(f"  [{issue['severity'].upper()}] {issue['type']}")
            report_lines.append(f"    Count: {issue['count']}")
            report_lines.append(f"    Note: {issue['note']}")
            report_lines.append("")

    # Insights
    if analysis['insights']:
        report_lines.append("INSIGHTS")
        report_lines.append("-" * 70)
        for insight in analysis['insights']:
            report_lines.append(f"  • {insight}")
        report_lines.append("")

    # Detailed differences (if any, show first 10)
    if comparison['differences']:
        report_lines.append("DETAILED DIFFERENCES (showing first 10)")
        report_lines.append("-" * 70)
        for i, diff in enumerate(comparison['differences'][:10]):
            report_lines.append(f"  Line {diff['line_num']}:")
            report_lines.append(f"    COBOL ({diff['cobol_len']:3d} chars): {repr(diff['cobol'][:80])}")
            report_lines.append(f"    JAVA  ({diff['java_len']:3d} chars): {repr(diff['java'][:80])}")
            report_lines.append("")

    report_lines.append("=" * 70)

    # Write report
    report_text = '\n'.join(report_lines)
    with open(output_file, 'w') as f:
        f.write(report_text)

    return report_text

def main():
    """Run comparison."""
    cobol_file = Path('output_cobol/weather_map.txt')
    java_file = Path('output_java/weather_map.txt')
    results_dir = Path('comparison_results')
    results_dir.mkdir(exist_ok=True)

    # Check files exist
    if not cobol_file.exists():
        print(f"✗ COBOL output file not found: {cobol_file}")
        return 1
    if not java_file.exists():
        print(f"✗ Java output file not found: {java_file}")
        return 1

    # Run comparison
    print("Comparing COBOL and Java outputs...")
    comparison = compare_outputs(cobol_file, java_file)

    # Save JSON results
    json_file = results_dir / f"comparison_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(json_file, 'w') as f:
        json.dump(comparison, f, indent=2)
    print(f"✓ JSON results saved to {json_file}")

    # Generate and save report
    report_file = results_dir / f"comparison_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    report_text = generate_report(comparison, report_file)
    print(f"✓ Report saved to {report_file}")

    # Print report to stdout
    print("\n" + report_text)

    return 0 if comparison['statistics']['different_lines'] == 0 else 1

if __name__ == '__main__':
    exit(main())
