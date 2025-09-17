#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

if ! command -v vim &> /dev/null; then
    echo " 'vim' not found. Installing vim..."
    sudo apt-get update && sudo apt-get install -y vim
fi
# --- Configuration ---
YAML_FILE="docstrings.yaml"
EXTRACT_SCRIPT="extract_docs.py"
WRITE_BACK_SCRIPT="write_docs.py"
# --- End Configuration ---

echo " 1. Synchronizing: Extracting latest docstrings from Python files into ${YAML_FILE}..."
python3 ${EXTRACT_SCRIPT}

echo " 2. Opening ${YAML_FILE} in vim for editing. Save and quit (:wq) when done."
echo "   (If you quit without saving, no changes will be committed)."

# Store the file's modification time *before* opening vim
BEFORE_MTIME=$(stat -c %Y ${YAML_FILE})

# Open the YAML file in vim and wait for the user to close it.
vim ${YAML_FILE}

# Store the file's modification time *after* closing vim
AFTER_MTIME=$(stat -c %Y ${YAML_FILE})

# Only run the write-back and git commands if the file was actually saved in vim.
if [[ "${BEFORE_MTIME}" != "${AFTER_MTIME}" ]]; then
  echo " 3. Changes detected. Writing docstrings back to Python files..."
  python3 ${WRITE_BACK_SCRIPT}
  echo " Docstrings updated successfully!"
  
  # --- NEW: Git Commit and Push Section ---
  echo " 4. Committing and pushing changes..."
  
  # Prompt the user for a commit message
  read -p "Enter commit message (or press Enter for a default): " COMMIT_MESSAGE
  
  # Use a default message if the user provides no input
  if [[ -z "${COMMIT_MESSAGE}" ]]; then
    COMMIT_MESSAGE="docs: Update documentation via script"
  fi
  
  # Add all changes, commit with the message, and push
  git add .
  git commit -m "${COMMIT_MESSAGE}"
  git push
  
  echo " Changes have been pushed to the remote repository!"
else
  echo " No changes were saved in vim. Skipping write-back and commit steps."
fi