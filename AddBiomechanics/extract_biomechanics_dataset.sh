common_folder=""
for f in *.zip; do 
    if [ -z "$common_folder" ]; then
        common_folder="${f%%_*}"
        mkdir -p "$common_folder"
    fi
    unzip "$f" -d "$common_folder" 
    find "$common_folder" -name "*.b3d" -exec cp {} "$common_folder" \; 
done

# Delete any remaining folders inside the common folder
rm -r "$common_folder"/*/

# Print finished
echo "Finished extracting"

# Move the common folder to /datasets/AddBiomechanics/raw_data
mv "$common_folder" /datasets/AddBiomechanics/raw_data
echo "Moved to /datasets/AddBiomechanics/raw_data"