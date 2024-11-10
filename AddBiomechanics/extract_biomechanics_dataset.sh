common_folder=""
for f in *.zip; do 
    if [ -z "$common_folder" ]; then
        common_folder="${f%%_*}"
        mkdir -p "$common_folder"
    fi
    unzip "$f" -d "$common_folder" 
    find "$common_folder" -name "*.b3d" -exec cp {} "$common_folder" \; 
done
