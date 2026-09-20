#!/bin/bash

set -e

# Initialize project
# - replace project_name in all files
# - rename lib dir

# --- Configuration ---
# The string to be searched for and replaced.
PLACEHOLDER="project_name"

# A space-separated list of files where the replacement should occur.
# IMPORTANT: Adjust this list to match the files in your project.
FILES_TO_PROCESS=(
    "README.md"
    "pyproject.toml"
    "run.sh"
		"tests/test_main.py"
)

# --- Script Logic ---

# Check if the replacement argument is provided
if [ -n "$1" ]; then
    NEW_NAME="$1"
else
    NEW_NAME=$(basename "$PWD")
fi
echo "project name: \"$NEW_NAME\""

# Store the replacement string
NEW_NAME_SNAKE="${NEW_NAME//-/_}"

echo "Initialize project \"${NEW_NAME}\""

# Iterate over the list of files
for FILE in "${FILES_TO_PROCESS[@]}"; do
    # Check if the file exists before attempting to modify it
    if [ -f "$FILE" ]; then
        echo "Processing file: $FILE"

        # Use sed to perform the in-place replacement.
        # The 'i' flag modifies the file in place. We use a non-standard
        # delimiter (e.g., '|') instead of '/' to avoid issues if the
        # replacement string ($NEW_NAME) contains slashes (e.g., 'path/to/project').
        # The 'g' flag ensures all occurrences on a line are replaced (global).
        if [ "$FILE" = "pyproject.toml" ]; then
            sed -i "s|${PLACEHOLDER}.cli|${NEW_NAME_SNAKE}.cli|g; s|${PLACEHOLDER}|${NEW_NAME}|g" "$FILE"
        else
            sed -i "s|${PLACEHOLDER}|${NEW_NAME}|g" "$FILE"
        fi
        
        # Check if sed was successful
        if [ $? -eq 0 ]; then
            echo "- rewrite $FILE."
        else
            echo "Warning: sed failed for $FILE"
        fi
    else
        echo "Warning: File not found: $FILE (Skipping)"
    fi
done

echo "renaming ./project_name to \"$NEW_NAME\""
git mv project_name "$NEW_NAME"

# add venv
echo "creating venv"
python -m venv venv
echo ""
echo "please run"
echo "    . venv/bin/activate"

echo "installing project and dependencies"
./venv/bin/python -m pip install -U pip
./venv/bin/python -m pip install -e .[dev]

echo "removing this script"
rm init-project.sh

echo "happy coding :)"
