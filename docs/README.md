# Documentation Structure

This directory contains documentation for the Locomotion Data Standardization project built with MkDocs.

## Documentation Site

### 🎯 Main Documentation

**Purpose**: Comprehensive documentation for researchers, contributors, and developers  
**Audience**: Dataset users, contributors, and maintainers  
**URL**: Built site available via GitHub Pages

**Content includes**:
- Getting started guides and tutorials
- User-friendly reference documentation
- Contributor guides for dataset submission
- API reference for tool developers
- Troubleshooting and support resources

**Build**:
```bash
mkdocs serve  # Development server
mkdocs build  # Production build
```

## Documentation Philosophy

### Documentation Focus

**Content organized around**:
- Task-oriented documentation ("How do I...")
- Progressive disclosure (basic → advanced)
- Practical examples and real-world usage
- Clear troubleshooting and support paths
- Technical implementation details for contributors
- Architecture decisions and rationale

### Design Principles

1. **User-Centered Design**: Documentation organized around user goals and tasks
2. **Progressive Disclosure**: Information revealed in appropriate depth for user needs
3. **Searchable Content**: Enhanced search functionality across both sites
4. **Mobile-Responsive**: Optimized for all device types
5. **Accessibility**: WCAG 2.1 AA compliance with enhanced focus indicators

## Site Features

### User Experience Enhancements

- **Tabbed Content**: Easy switching between Python/MATLAB examples
- **Code Copy Buttons**: One-click copying of code snippets
- **Interactive Examples**: Live code demonstrations where possible
- **Search Highlighting**: Enhanced search with result highlighting
- **Dark/Light Themes**: User preference support
- **Mobile Navigation**: Optimized mobile experience

### Technical Features

- **Fast Search**: Client-side search with intelligent ranking
- **Git Integration**: Automatic page modification dates
- **Version Control**: Support for versioned documentation
- **Cross-References**: Intelligent linking between related content
- **Analytics Ready**: Google Analytics integration support

## Contributing to Documentation

### User Guide Updates

1. **Content Guidelines**: Follow user-focused writing style
2. **Examples**: Include both Python and MATLAB examples
3. **Testing**: Verify all code examples work
4. **Accessibility**: Ensure content is accessible

### Engineering Docs Updates

1. **Technical Accuracy**: Verify architecture diagrams are current
2. **Decision Records**: Document architectural decisions
3. **Process Updates**: Keep workflows current with implementation
4. **Cross-References**: Link to relevant user documentation

## File Organization

```
docs/
├── README.md                    # This file
├── user_guide/                  # User-focused documentation
│   ├── mkdocs.yml              # User guide configuration
│   ├── docs/                   # User guide content
│   │   ├── index.md            # User-focused landing page
│   │   ├── getting_started/    # Installation and quick start
│   │   ├── user_guide/         # Working with data, validation
│   │   ├── contributor_guide/  # Dataset contribution guides
│   │   ├── tutorials/          # Python/MATLAB tutorials
│   │   └── reference/          # API docs, specifications
│   └── site/                   # Built user guide site
├── software_engineering/        # Engineering documentation
│   ├── mkdocs.yml              # Engineering docs configuration
│   ├── docs/                   # Engineering content
│   │   ├── 00_OVERVIEW.md      # Technical overview
│   │   ├── 01_USER_GUIDE.md    # User research and personas
│   │   ├── 02_REQUIREMENTS.md  # System requirements
│   │   ├── 03_ARCHITECTURE.md  # System architecture
│   │   └── ...                 # Additional engineering docs
│   └── site/                   # Built engineering site
└── [legacy content moved to appropriate sites]
```

## Migration Summary

### Content Moved to User Guide

- `docs/tutorials/` → `user_guide/docs/tutorials/`
- `docs/standard_spec/` → `reference/standard_spec/`
- `docs/datasets_documentation/` → `user_guide/docs/reference/datasets_documentation/`

### Content Retained in Engineering Docs

- `docs/software_engineering/` → `software_engineering/docs/`
- All technical architecture and design documentation
- Development processes and project management docs

### New Content Created

- User-focused landing pages and getting started guides
- Comprehensive troubleshooting documentation
- Contributor onboarding and best practices
- Enhanced API reference documentation

## Build and Deployment

### Development

```bash
# Start both sites in development mode
cd user_guide && python -m mkdocs serve --dev-addr=localhost:8000 &
cd software_engineering && python -m mkdocs serve --dev-addr=localhost:8001 &
```

### Production

```bash
# Build both sites
cd user_guide && python -m mkdocs build
cd software_engineering && python -m mkdocs build

# Sites will be built to:
# user_guide/site/
# software_engineering/site/
```

### CI/CD Integration

Both sites can be deployed independently:

- **User Guide**: Primary site for public consumption
- **Engineering Docs**: Internal or stakeholder-restricted access

## Quality Assurance

### Link Checking

```bash
# Check internal links
cd user_guide && python -m mkdocs build --strict
cd software_engineering && python -m mkdocs build --strict
```

### Content Validation

1. **Code Examples**: All examples tested with actual datasets
2. **Cross-References**: Links verified between sites
3. **Accessibility**: Regular accessibility audits
4. **User Testing**: Periodic usability testing with target users

## Support and Maintenance

### Regular Updates

- **User Guide**: Updated with each release and user feedback
- **Engineering Docs**: Updated with architectural changes and decisions
- **Cross-Site Links**: Maintained as content evolves

### Contact Information

- **Content Issues**: [docs@locomotion-standardization.org](mailto:docs@locomotion-standardization.org)
- **Technical Issues**: [GitHub Issues](https://github.com/your-org/locomotion-data-standardization/issues)
- **User Feedback**: [GitHub Discussions](https://github.com/your-org/locomotion-data-standardization/discussions)

---

*This documentation structure supports both user needs and engineering requirements while maintaining clear separation of concerns and optimal user experience.*