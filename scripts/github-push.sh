#!/bin/bash

# 1. Ask for the Repository URL (Remind about SSH)
echo "Enter the GitHub Repository URL (Prefer SSH: git@github.com:user/repo.git):"
read repo_url

# 2. Initialize if .git doesn't exist
if [ ! -d ".git" ]; then
    echo "Initializing new Git repository..."
    git init
    git branch -M main
else
    echo "Existing Git repository detected."
fi

# 3. Check for nested .git folders
if find . -mindepth 2 -name ".git" -type d | grep -q .; then
    echo "Found nested .git folders. Cleaning up and resetting Git index..."
    find . -mindepth 2 -name ".git" -type d -exec rm -rf {} + 2>/dev/null
    # Clear the cached index so Git recognizes these as regular folders now
    git rm --cached -r . --ignore-unmatch >/dev/null
fi

# 4. Add Remote if it doesn't exist
if ! git remote | grep -q "origin"; then
    git remote add origin "$repo_url"
    echo "Remote 'origin' added."
else
    git remote set-url origin "$repo_url"
fi

# 5. Add, Commit, and Push
echo "Enter commit message (default: 'update'):"
read commit_msg

if [ -z "$commit_msg" ]; then
    commit_msg="update"
fi

# Stage everything
git add .

# Let's show what is actually about to be committed so you can verify the file count
echo "--- Files staged for commit: ---"
git status --short
echo "--------------------------------"

git commit -m "$commit_msg"

echo "Pushing to GitHub..."
git push -u origin main

echo "Done! Check your GitHub repo."