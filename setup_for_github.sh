#!/bin/bash
# Setup script for preparing HA Insights for GitHub HACS installation

# Create necessary directories
mkdir -p custom_components/ha_insights/analytics
mkdir -p custom_components/ha_insights/translations

# Copy main integration files
cp -v ha_insights/*.py custom_components/ha_insights/
cp -v ha_insights/manifest.json custom_components/ha_insights/
cp -v ha_insights/services.yaml custom_components/ha_insights/

# Copy analytics
cp -v ha_insights/analytics/*.py custom_components/ha_insights/analytics/

# Copy translations
cp -v ha_insights/translations/*.json custom_components/ha_insights/translations/

# Copy example file to proper location
cp -v ha_insights/example_lovelace.yaml custom_components/ha_insights/

# Copy GitHub workflow files
mkdir -p .github/workflows
cp -v .github/workflows/*.yaml .github/workflows/

echo
echo "===================================================================="
echo "Setup complete! Now you should:"
echo "1. Create a GitHub repository with name 'ha_insights'"
echo "2. IMPORTANT: Replace GITHUB_USERNAME in manifest.json and README.md with your actual GitHub username"
echo "   - This is required for proper linking and HACS installation"
echo "   - For example, if your GitHub username is 'johnsmith', change all occurrences to 'johnsmith'"
echo "3. Upload these files to your GitHub repository:"
echo "   - custom_components/ (entire directory)"
echo "   - README.md"
echo "   - LICENSE"
echo "   - hacs.json"
echo "   - .github/ (entire directory)"
echo "===================================================================="
echo
echo "Then users can install via HACS by adding your repository."
echo "====================================================================" 