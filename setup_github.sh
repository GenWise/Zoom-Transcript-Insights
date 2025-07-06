#!/bin/bash

# Script to initialize git repository and push to GitHub
# Usage: ./setup_github.sh <github_repo_url>

set -e  # Exit on error

# Display banner
echo "=================================================="
echo "   Zoom Transcript Insights - GitHub Setup Tool   "
echo "=================================================="
echo

# Check if GitHub URL is provided
if [ $# -ne 1 ]; then
    echo "Usage: ./setup_github.sh <github_repo_url>"
    echo "Example: ./setup_github.sh https://github.com/username/repo.git"
    exit 1
fi

GITHUB_URL=$1

# Validate GitHub URL format
if ! [[ $GITHUB_URL =~ ^https://github\.com/.+/.+\.git$ ]]; then
    echo "Error: Invalid GitHub URL format. Please use the format: https://github.com/username/repo.git"
    exit 1
fi

# Check for git installation
if ! command -v git &> /dev/null; then
    echo "Error: git is not installed. Please install git and try again."
    exit 1
fi

# Initialize git if not already initialized
if [ ! -d ".git" ]; then
    echo "Initializing git repository..."
    git init
    echo "✅ Git repository initialized."
else
    echo "✅ Git repository already initialized."
fi

# Create .gitignore if it doesn't exist
if [ ! -f ".gitignore" ]; then
    echo "Creating .gitignore file..."
    cat > .gitignore << EOL
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
*.egg-info/
.installed.cfg
*.egg

# Virtual Environment
venv/
ENV/
.env

# IDE files
.idea/
.vscode/
*.swp
*.swo

# Logs
logs/
*.log

# Temporary files
temp/
*.tmp

# Google API credentials
*-[0-9a-f]*.json

# Environment variables
.env
*.env
EOL
    echo "✅ .gitignore created."
else
    echo "✅ .gitignore file already exists."
fi

# Check for sensitive files
echo "Checking for sensitive files..."
SENSITIVE_FILES=$(find . -name "*.json" -o -name "*.pem" -o -name "*.key" -o -name ".env" | grep -v "package.json" | grep -v "tsconfig.json" || true)
if [ ! -z "$SENSITIVE_FILES" ]; then
    echo "⚠️  Warning: Found potentially sensitive files that will be excluded from git:"
    echo "$SENSITIVE_FILES"
    echo
    echo "These files are listed in .gitignore and won't be pushed to GitHub."
fi

# Add all files
echo "Adding files to git..."
git add .
echo "✅ Files added to git."

# Check if there are changes to commit
if git diff-index --quiet HEAD -- 2>/dev/null || [ -z "$(git status --porcelain)" ]; then
    echo "No changes to commit. Repository is up to date."
else
    # Commit changes
    echo "Committing changes..."
    git commit -m "Initial commit of Zoom Transcript Insights"
    echo "✅ Changes committed."
fi

# Check if remote origin already exists
if git remote | grep -q "^origin$"; then
    echo "Remote 'origin' already exists. Updating URL..."
    git remote set-url origin $GITHUB_URL
else
    # Add remote
    echo "Adding remote origin..."
    git remote add origin $GITHUB_URL
fi
echo "✅ Remote origin set to: $GITHUB_URL"

# Push to GitHub
echo "Pushing to GitHub..."
echo "This may prompt for your GitHub credentials if not already configured."
git branch -M main
git push -u origin main || echo "⚠️  Failed to push to main branch, trying master..." && git push -u origin master
echo "✅ Repository pushed to GitHub!"

echo
echo "=================================================="
echo "   Setup Complete! Repository is now on GitHub    "
echo "=================================================="
echo
echo "Next steps:"
echo "1. Visit $GITHUB_URL to view your repository"
echo "2. Set up webhook integration for automatic processing"
echo "3. Configure email notifications for new insights"
echo 