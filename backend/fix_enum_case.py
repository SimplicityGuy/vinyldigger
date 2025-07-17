#!/usr/bin/env python3
"""
Script to fix enum case issues in the VinylDigger backend.
This ensures all enum values are lowercase as per project conventions.
"""

import re
from pathlib import Path


def fix_enum_values(file_path: Path) -> bool:
    """Fix enum values in a Python file to be lowercase."""
    with open(file_path) as f:
        content = f.read()

    modified = False

    # Patterns to fix uppercase enum values
    patterns = [
        # Fix enum definitions like: DISCOGS = "DISCOGS" -> DISCOGS = "discogs"
        (r'(\b[A-Z_]+\s*=\s*)"([A-Z_]+)"', lambda m: f'{m.group(1)}"{m.group(2).lower()}"'),
        (r"(\b[A-Z_]+\s*=\s*)'([A-Z_]+)'", lambda m: f"{m.group(1)}'{m.group(2).lower()}'"),
    ]

    for pattern, replacement in patterns:
        # Only apply to lines that look like enum definitions
        lines = content.split("\n")
        new_lines = []
        in_enum_class = False

        for line in lines:
            # Check if we're entering an enum class
            if "class" in line and "(str, Enum)" in line:
                in_enum_class = True
            elif line.strip() and not line.startswith(" ") and not line.startswith("\t"):
                # We've left the enum class
                in_enum_class = False

            # Only apply replacements inside enum classes
            if in_enum_class and "=" in line and ('"' in line or "'" in line):
                new_line = re.sub(pattern, replacement, line)
                if new_line != line:
                    modified = True
                    print(f"  Fixed: {line.strip()} -> {new_line.strip()}")
                new_lines.append(new_line)
            else:
                new_lines.append(line)

        content = "\n".join(new_lines)

    # Write back if modified
    if modified:
        with open(file_path, "w") as f:
            f.write(content)
        return True

    return False


def fix_migration_enums(file_path: Path) -> bool:
    """Fix enum values in migration files to be lowercase."""
    with open(file_path) as f:
        content = f.read()

    original_content = content

    # Fix CREATE TYPE statements
    # Match patterns like: CREATE TYPE name AS ENUM ('VALUE1', 'VALUE2')
    def fix_enum_values_in_sql(match):
        prefix = match.group(1)
        values = match.group(2)
        # Split values and convert to lowercase
        value_list = re.findall(r"'([^']+)'", values)
        lowercase_values = [f"'{v.lower()}'" for v in value_list]
        return f"{prefix}({', '.join(lowercase_values)})"

    # Apply to specific enum types we know about
    enum_types = [
        "apiservice",
        "oauthprovider",
        "oauthenvironment",
        "searchplatform",
        "searchstatus",
        "recommendationtype",
        "dealscore",
        "matchconfidence",
    ]

    for enum_type in enum_types:
        pattern = rf"(CREATE TYPE {enum_type} AS ENUM )\(([^)]+)\)"
        content = re.sub(pattern, fix_enum_values_in_sql, content, flags=re.IGNORECASE)

    if content != original_content:
        with open(file_path, "w") as f:
            f.write(content)
        print(f"Fixed migration file: {file_path}")
        return True

    return False


def main():
    print("Fixing enum case issues in VinylDigger backend...")

    # Fix Python model files
    models_dir = Path(__file__).parent / "src" / "models"
    fixed_count = 0

    print("\nChecking model files...")
    for py_file in models_dir.glob("*.py"):
        print(f"Checking {py_file.name}...")
        if fix_enum_values(py_file):
            fixed_count += 1

    # Fix migration files
    migrations_dir = Path(__file__).parent / "alembic" / "versions"
    print("\nChecking migration files...")
    for py_file in migrations_dir.glob("*.py"):
        print(f"Checking {py_file.name}...")
        if fix_migration_enums(py_file):
            fixed_count += 1

    print(f"\nFixed {fixed_count} files.")

    # Note about SearchStatus - it should remain uppercase
    print("\nNote: SearchStatus enum values (PENDING, RUNNING, COMPLETED, FAILED) are kept uppercase")
    print("as they represent internal states, not platform names.")


if __name__ == "__main__":
    main()
