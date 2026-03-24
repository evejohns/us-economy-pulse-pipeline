#!/usr/bin/env python3
"""
Secret Audit Scanner

This script scans a repository for accidentally committed secrets such as:
- API keys and tokens
- Database credentials
- Private keys
- Hardcoded environment values

Exit code 1 indicates critical findings were detected.
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple


# Regex patterns for detecting secrets
SECRET_PATTERNS = {
    "api_key": {
        "pattern": r"['\"]?(api[_-]?key|apikey)['\"]?\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{20,})['\"]?",
        "severity": "critical",
        "description": "Potential API key found",
    },
    "supabase_url": {
        "pattern": r"https://[a-zA-Z0-9\-]+\.supabase\.co",
        "severity": "warning",
        "description": "Supabase URL detected (may be public, verify context)",
    },
    "jwt_token": {
        "pattern": r"(eyJ[A-Za-z0-9_\-\.]+)",
        "severity": "critical",
        "description": "JWT token detected",
    },
    "password_in_url": {
        "pattern": r"(postgresql|mysql|mongodb|postgres)://[^:]+:[^@]+@",
        "severity": "critical",
        "description": "Password found in connection string",
    },
    "aws_key_id": {
        "pattern": r"AKIA[0-9A-Z]{16}",
        "severity": "critical",
        "description": "AWS Access Key ID detected",
    },
    "aws_secret_key": {
        "pattern": r"aws_secret_access_key\s*[:=]\s*['\"]?([a-zA-Z0-9/+=]{40})['\"]?",
        "severity": "critical",
        "description": "AWS Secret Access Key pattern detected",
    },
    "github_token": {
        "pattern": r"gh[pousr]_[A-Za-z0-9_]{36,255}",
        "severity": "critical",
        "description": "GitHub token pattern detected",
    },
    "private_key": {
        "pattern": r"-----BEGIN (RSA|DSA|EC|PGP|OPENSSH) PRIVATE KEY",
        "severity": "critical",
        "description": "Private key file detected",
    },
    "env_var_exposed": {
        "pattern": r"(DATABASE_URL|FRED_API_KEY|SUPABASE_KEY|SECRET_KEY)\s*[:=]\s*['\"]?[a-zA-Z0-9_\-]{8,}['\"]?",
        "severity": "warning",
        "description": "Environment variable with potential value exposed",
    },
}

# Directories and files to exclude from scanning
EXCLUDE_DIRS = {".git", "node_modules", "venv", ".venv", "__pycache__", ".pytest_cache", ".tox"}
EXCLUDE_FILES = {".gitignore", ".gitattributes"}
EXCLUDE_EXTENSIONS = {".pyc", ".pyo", ".so", ".dll", ".exe", ".bin"}

# Patterns for common false positives (test fixtures, examples)
FALSE_POSITIVE_PATTERNS = {
    r"example|test|fixture|demo|fake|mock",
    r"xxxxx+|yyyyy+|zzzzz+",
    r"12345+|00000+|11111+",
    r"placeholder|redacted|\[REDACTED\]",
}


def should_skip_file(file_path: Path) -> bool:
    """Check if file should be skipped from scanning."""
    # Skip excluded directories
    if any(part in EXCLUDE_DIRS for part in file_path.parts):
        return True

    # Skip excluded file names
    if file_path.name in EXCLUDE_FILES:
        return True

    # Skip excluded extensions
    if file_path.suffix in EXCLUDE_EXTENSIONS:
        return True

    return False


def is_likely_false_positive(line: str, match: str) -> bool:
    """Check if a match is likely a false positive (test data, example, etc)."""
    lower_line = line.lower()
    for pattern in FALSE_POSITIVE_PATTERNS:
        if re.search(pattern, lower_line):
            return True
    return False


def scan_file(file_path: Path) -> List[Tuple[int, str, str, str]]:
    """
    Scan a single file for secrets.

    Returns:
        List of tuples: (line_number, pattern_name, matched_text, severity)
    """
    findings = []

    if should_skip_file(file_path):
        return findings

    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line_num, line in enumerate(f, 1):
                for pattern_name, pattern_info in SECRET_PATTERNS.items():
                    matches = re.finditer(pattern_info["pattern"], line, re.IGNORECASE)
                    for match in matches:
                        matched_text = match.group(0)

                        # Skip likely false positives
                        if is_likely_false_positive(line, matched_text):
                            continue

                        # Skip .example files for most patterns (they're meant to be templates)
                        if file_path.suffix == ".example" and pattern_name != "private_key":
                            continue

                        findings.append(
                            (
                                line_num,
                                pattern_name,
                                matched_text[:50],  # Truncate for safety in output
                                pattern_info["severity"],
                            )
                        )

    except (IsADirectoryError, PermissionError, UnicodeDecodeError):
        pass

    return findings


def scan_directory(directory: Path) -> Tuple[List[dict], int]:
    """
    Recursively scan a directory for secrets.

    Returns:
        Tuple of (findings list, critical count)
    """
    all_findings = []
    critical_count = 0

    for file_path in directory.rglob("*"):
        if file_path.is_file():
            findings = scan_file(file_path)
            for line_num, pattern_name, matched_text, severity in findings:
                all_findings.append(
                    {
                        "file": str(file_path.relative_to(directory)),
                        "line": line_num,
                        "pattern": pattern_name,
                        "matched": matched_text,
                        "severity": severity,
                        "description": SECRET_PATTERNS[pattern_name]["description"],
                    }
                )
                if severity == "critical":
                    critical_count += 1

    return all_findings, critical_count


def format_report(findings: List[dict]) -> str:
    """Format findings into a human-readable report."""
    if not findings:
        return "✓ No secrets detected\n"

    report = f"\nFound {len(findings)} potential secret(s):\n"
    report += "=" * 80 + "\n\n"

    # Sort by severity (critical first) then by file
    sorted_findings = sorted(
        findings, key=lambda x: (x["severity"] != "critical", x["file"], x["line"])
    )

    for finding in sorted_findings:
        severity_icon = "🔴 CRITICAL" if finding["severity"] == "critical" else "🟡 WARNING"
        report += f"{severity_icon}\n"
        report += f"  File:        {finding['file']}\n"
        report += f"  Line:        {finding['line']}\n"
        report += f"  Pattern:     {finding['pattern']}\n"
        report += f"  Description: {finding['description']}\n"
        report += f"  Matched:     {finding['matched']}\n"
        report += "\n"

    report += "=" * 80 + "\n"
    return report


def main():
    """Main entry point for the audit script."""
    parser = argparse.ArgumentParser(
        description="Scan repository for accidentally committed secrets"
    )
    parser.add_argument(
        "--path",
        type=str,
        default=".",
        help="Path to scan (default: current directory)",
    )

    args = parser.parse_args()

    scan_path = Path(args.path).resolve()

    if not scan_path.exists():
        print(f"Error: Path does not exist: {scan_path}")
        sys.exit(1)

    if scan_path.is_file():
        findings, critical_count = [], 0
        file_findings = scan_file(scan_path)
        if file_findings:
            for line_num, pattern_name, matched_text, severity in file_findings:
                findings.append(
                    {
                        "file": scan_path.name,
                        "line": line_num,
                        "pattern": pattern_name,
                        "matched": matched_text,
                        "severity": severity,
                        "description": SECRET_PATTERNS[pattern_name]["description"],
                    }
                )
                if severity == "critical":
                    critical_count += 1
    else:
        findings, critical_count = scan_directory(scan_path)

    print(format_report(findings))

    if critical_count > 0:
        print(f"\n⚠️  {critical_count} critical finding(s) detected")
        sys.exit(1)
    else:
        print("✓ No critical secrets detected")
        sys.exit(0)


if __name__ == "__main__":
    main()
