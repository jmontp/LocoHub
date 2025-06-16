#!/bin/bash
# Deploy MkDocs site to GitHub Pages manually

set -e

echo "Building MkDocs site..."
cd docs/software_engineering
mkdocs build --clean

echo "Deploying to gh-pages branch..."
mkdocs gh-deploy --force

echo "Documentation deployed to GitHub Pages!"
echo "Visit: https://jmontp.github.io/locomotion-data-standardization/"