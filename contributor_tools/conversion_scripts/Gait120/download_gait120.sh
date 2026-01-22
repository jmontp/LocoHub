#!/bin/bash
# Download Gait120 dataset from Figshare
#
# Dataset: Comprehensive Human Locomotion and Electromyography Dataset: Gait120
# DOI: 10.6084/m9.figshare.27677016
# Paper: https://www.nature.com/articles/s41597-025-05391-0
#
# Total size: ~15 GB (12 zip files, ~1.3 GB each)
# Contains 120 subjects (S001-S120), 7 tasks, ~6,882 movement cycles
#
# Usage:
#   ./download_gait120.sh [output_directory]
#
# Default output: /mnt/s/locomotion_data/Gait120

set -e

# Configuration
OUTPUT_DIR="${1:-/mnt/s/locomotion_data/Gait120}"
FIGSHARE_ARTICLE_ID="27677016"

echo "==================================="
echo "Gait120 Dataset Download Script"
echo "==================================="
echo ""
echo "Dataset: Comprehensive Human Locomotion and Electromyography Dataset: Gait120"
echo "DOI: https://doi.org/10.6084/m9.figshare.${FIGSHARE_ARTICLE_ID}"
echo ""
echo "Output directory: ${OUTPUT_DIR}"
echo ""

# Create output directory
mkdir -p "${OUTPUT_DIR}"
cd "${OUTPUT_DIR}"

# Check for required tools
if ! command -v wget &> /dev/null && ! command -v curl &> /dev/null; then
    echo "Error: wget or curl is required but not installed."
    exit 1
fi

# Use curl if wget not available
if command -v wget &> /dev/null; then
    DOWNLOAD_CMD="wget -c"
else
    DOWNLOAD_CMD="curl -L -C - -O"
fi

echo "Step 1: Fetching file list from Figshare API..."
echo ""

# Get file list from Figshare API
FIGSHARE_API="https://api.figshare.com/v2/articles/${FIGSHARE_ARTICLE_ID}/files"
FILE_LIST=$(curl -s "${FIGSHARE_API}")

if [ -z "${FILE_LIST}" ] || [ "${FILE_LIST}" == "[]" ]; then
    echo "Error: Could not fetch file list from Figshare."
    echo "Please download manually from:"
    echo "  https://springernature.figshare.com/articles/dataset/Comprehensive_Human_Locomotion_and_Electromyography_Dataset_Gait120/${FIGSHARE_ARTICLE_ID}"
    exit 1
fi

# Parse and download each file
echo "Step 2: Downloading dataset files..."
echo ""

# Extract download URLs and file names using jq if available, otherwise use grep/sed
if command -v jq &> /dev/null; then
    FILES=$(echo "${FILE_LIST}" | jq -r '.[] | "\(.download_url) \(.name)"')
else
    # Basic parsing without jq (may not work for all cases)
    echo "Warning: jq not installed. Using basic parsing."
    echo "For best results, install jq: sudo apt install jq"
    FILES=$(echo "${FILE_LIST}" | grep -oP '"download_url":"[^"]+"|"name":"[^"]+"' | paste - - | sed 's/"download_url":"//g' | sed 's/"name":"//g' | sed 's/"//g')
fi

# Count files
FILE_COUNT=$(echo "${FILE_LIST}" | jq 'length' 2>/dev/null || echo "unknown")
echo "Found ${FILE_COUNT} files to download"
echo ""

# Download each file
CURRENT=0
while IFS= read -r line; do
    if [ -z "${line}" ]; then
        continue
    fi

    URL=$(echo "${line}" | awk '{print $1}')
    NAME=$(echo "${line}" | awk '{print $2}')

    if [ -z "${URL}" ] || [ -z "${NAME}" ]; then
        continue
    fi

    CURRENT=$((CURRENT + 1))

    # Check if file already exists
    if [ -f "${NAME}" ]; then
        echo "[${CURRENT}] Skipping ${NAME} (already exists)"
        continue
    fi

    echo "[${CURRENT}] Downloading ${NAME}..."
    if command -v wget &> /dev/null; then
        wget -c "${URL}" -O "${NAME}" || {
            echo "  Download failed, retrying..."
            sleep 2
            wget -c "${URL}" -O "${NAME}"
        }
    else
        curl -L -C - -o "${NAME}" "${URL}" || {
            echo "  Download failed, retrying..."
            sleep 2
            curl -L -C - -o "${NAME}" "${URL}"
        }
    fi
    echo ""
done <<< "${FILES}"

echo ""
echo "Step 3: Extracting zip files..."
echo ""

# Extract all zip files
for zipfile in *.zip; do
    if [ -f "${zipfile}" ]; then
        echo "Extracting ${zipfile}..."
        unzip -o -q "${zipfile}"
    fi
done

echo ""
echo "Step 4: Verifying extraction..."
echo ""

# Count extracted subject folders
SUBJECT_COUNT=$(find . -maxdepth 1 -type d -name "S*" | wc -l)
echo "Found ${SUBJECT_COUNT} subject folders"

# List task directories in first available subject
FIRST_SUBJECT=$(find . -maxdepth 1 -type d -name "S*" | sort | head -1)
if [ -n "${FIRST_SUBJECT}" ] && [ -d "${FIRST_SUBJECT}/JointAngle" ]; then
    echo ""
    echo "Task folders found in ${FIRST_SUBJECT}/JointAngle:"
    ls -1 "${FIRST_SUBJECT}/JointAngle/" 2>/dev/null || echo "  (none)"
fi

echo ""
echo "==================================="
echo "Download complete!"
echo "==================================="
echo ""
echo "Dataset location: ${OUTPUT_DIR}"
echo "Subject folders: ${SUBJECT_COUNT}"
echo ""
echo "Next steps:"
echo "  1. Verify the data structure matches expected format"
echo "  2. Run the conversion script:"
echo "     python contributor_tools/conversion_scripts/Gait120/convert_gait120_to_parquet.py \\"
echo "         --input ${OUTPUT_DIR}"
echo ""
