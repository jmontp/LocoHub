# Release Process

How to prepare, tag, and deploy new versions of the locomotion data system.

## Version Numbering

We use [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking changes (2.0.0)
- **MINOR**: New features, backward compatible (1.3.0)
- **PATCH**: Bug fixes (1.2.1)

### Examples
```
1.0.0 -> 1.0.1  # Bug fix
1.0.1 -> 1.1.0  # New feature added
1.1.0 -> 2.0.0  # Breaking change (e.g., variable renamed)
```

## Pre-Release Checklist

### 1. Code Quality
```bash
# Run full test suite
pytest tests/ -v

# Check test coverage (aim for >80%)
pytest tests/ --cov=lib --cov-report=term-missing

# Run linting
black lib/ tests/ --check
flake8 lib/ tests/

# Type checking
mypy lib/ --ignore-missing-imports
```

### 2. Documentation
```bash
# Build docs locally
mkdocs build --strict

# Check for broken links
# linkchecker site/

# Review README is current
# Review CHANGELOG is updated
```

### 3. Dependency Check
```bash
# Check for security issues
pip-audit

# Update requirements if needed
pip freeze > requirements.txt

# Test with minimum supported versions
pip install -r requirements-min.txt
pytest tests/
```

## Release Steps

### 1. Update Version

```python
# lib/__init__.py
__version__ = "1.3.0"  # Update version

# setup.py (if applicable)
setup(
    name="locomotion-data-standardization",
    version="1.3.0",  # Update version
    ...
)
```

### 2. Update CHANGELOG

```markdown
# CHANGELOG.md

## [1.3.0] - 2024-03-15

### Added
- Automated validation range tuning (#123)
- Support for OpenSim data format (#124)

### Changed
- Improved LocomotionData loading speed by 50% (#125)

### Fixed
- Memory leak in validation plotting (#126)
- Incorrect sign for knee moments (#127)

### Breaking Changes
- Renamed `get_data()` to `get_task_data()` for clarity
```

### 3. Create Release Commit

```bash
# Stage changes
git add lib/__init__.py CHANGELOG.md setup.py

# Commit
git commit -m "chore: Prepare release v1.3.0

- Update version to 1.3.0
- Update CHANGELOG with release notes
- Ready for tagging"
```

### 4. Tag Release

```bash
# Create annotated tag
git tag -a v1.3.0 -m "Release version 1.3.0

Highlights:
- Automated validation tuning
- OpenSim format support
- 50% faster data loading

See CHANGELOG.md for full details."

# Push tag
git push origin v1.3.0
```

### 5. Create GitHub Release

```bash
# Using GitHub CLI
gh release create v1.3.0 \
  --title "v1.3.0 - Automated Validation Tuning" \
  --notes-file RELEASE_NOTES.md \
  --target main
```

Or manually on GitHub:
1. Go to Releases → Draft New Release
2. Choose tag `v1.3.0`
3. Copy relevant CHANGELOG section
4. Attach any binary assets if needed
5. Publish release

## Deployment

### PyPI Release (If Applicable)

```bash
# Build distribution
python setup.py sdist bdist_wheel

# Check distribution
twine check dist/*

# Upload to Test PyPI first
twine upload --repository-url https://test.pypi.org/legacy/ dist/*

# Test installation
pip install -i https://test.pypi.org/simple/ locomotion-data-standardization

# Upload to PyPI
twine upload dist/*
```

### Documentation Deployment

```bash
# Build and deploy to GitHub Pages
mkdocs gh-deploy --clean

# Or if using ReadTheDocs
# Push to main branch triggers automatic build
```

### Docker Image (If Applicable)

```bash
# Build image
docker build -t locomotion-data:1.3.0 .

# Tag as latest
docker tag locomotion-data:1.3.0 locomotion-data:latest

# Push to registry
docker push yourregistry/locomotion-data:1.3.0
docker push yourregistry/locomotion-data:latest
```

## Post-Release

### 1. Verify Deployment

```bash
# Test PyPI installation
pip install locomotion-data-standardization==1.3.0

# Test import
python -c "import locomotion_data; print(locomotion_data.__version__)"

# Check documentation is live
curl -I https://your-docs-site.com
```

### 2. Announce Release

- Update project README if needed
- Post in discussions/forums
- Email collaborators if major changes
- Update any dependent projects

### 3. Start Next Cycle

```bash
# Create development branch
git checkout -b dev-1.4.0

# Update version to development
# lib/__init__.py
__version__ = "1.4.0-dev"

git commit -m "chore: Start 1.4.0 development cycle"
```

## Hotfix Process

For urgent fixes to production:

```bash
# Create hotfix branch from tag
git checkout -b hotfix-1.3.1 v1.3.0

# Make fix
# ... edit files ...

# Update version
# lib/__init__.py -> "1.3.1"

# Commit
git commit -m "fix: Critical bug in validation

Fixes issue where validation crashes on empty datasets."

# Tag and release
git tag -a v1.3.1 -m "Hotfix: Validation crash"
git push origin v1.3.1

# Merge back to main and dev
git checkout main
git merge hotfix-1.3.1
git checkout dev-1.4.0  
git merge hotfix-1.3.1
```

## Version Support Policy

- **Latest**: Full support
- **Previous minor**: Security fixes only
- **Older**: Best effort

Example (current: 1.3.0):
- 1.3.x - Full support
- 1.2.x - Security fixes
- 1.1.x - No guaranteed support

## Breaking Change Guidelines

Before making breaking changes:

1. **Deprecate first** (if possible)
```python
def old_method(self):
    warnings.warn(
        "old_method is deprecated, use new_method instead",
        DeprecationWarning,
        stacklevel=2
    )
    return self.new_method()
```

2. **Document migration path**
```markdown
## Migration Guide: v1.x to v2.0

### Changed: Variable naming
Old: `knee_angle`
New: `knee_flexion_angle_ipsi_rad`

Migration:
```python
# Old code
angle = data.get_variable('knee_angle')

# New code  
angle = data.get_variable('knee_flexion_angle_ipsi_rad')
```
```

3. **Provide compatibility layer** (optional)
```python
# lib/compat.py
def load_legacy_data(file_path):
    """Load data in old format and convert."""
    old_data = pd.read_csv(file_path)
    return convert_to_new_format(old_data)
```

## Release Automation

Consider setting up CI/CD:

```yaml
# .github/workflows/release.yml
name: Release
on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Run tests
        run: pytest tests/
        
      - name: Build package
        run: python setup.py sdist bdist_wheel
        
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          password: ${{ secrets.PYPI_API_TOKEN }}
          
      - name: Create GitHub Release
        uses: softprops/action-gh-release@v1
        with:
          files: dist/*
```

## Summary

Release process ensures quality and stability:
1. **Test thoroughly** before release
2. **Document changes** clearly
3. **Version semantically** for clarity
4. **Deploy carefully** with verification
5. **Communicate** with users