# CLAUDE.md

This file provides comprehensive guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

[... existing content remains unchanged ...]

## Common Commands

### Git Guidelines
- Never "git add -A", just add the files that you edit
- Always add co-author information when committing
- For current date information, always use Python: `python3 -c "import datetime; print(datetime.datetime.now().strftime('%Y-%m-%d'))"`

### Date and Time Information
- **Recommended Method**: Use Python to get current date
  ```python
  import datetime
  print(datetime.datetime.now().strftime('%Y-%m-%d'))
  ```

[... rest of the existing content remains the same ...]