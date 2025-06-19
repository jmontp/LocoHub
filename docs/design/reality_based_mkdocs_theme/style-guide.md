# High-Performance Documentation Theme - Style Guide

## Overview

The Locomotion Data Standardization documentation theme is designed for **scientific and academic users** who require fast, accessible, and professional documentation. This style guide provides comprehensive guidelines for maintaining consistency and performance across all documentation pages.

## Design Principles

### 1. Performance First
- **Mobile-first responsive design** with optimized critical path
- **Minimized CSS bundle** through efficient selectors and modern CSS features
- **Reduced animation duration** with respect for `prefers-reduced-motion`
- **Optimized images** with lazy loading and appropriate formats

### 2. Accessibility by Design
- **WCAG 2.1 AA compliance** with high contrast ratios and focus indicators
- **Screen reader optimization** with semantic HTML and ARIA labels
- **Keyboard navigation support** with visible focus states
- **Reduced motion support** for users with vestibular disorders

### 3. Scientific Professionalism
- **Academic typography** with clear hierarchy and optimal line spacing
- **Citation-friendly formatting** with print optimization
- **Status-aware components** for tracking implementation progress
- **Trust-building visual language** with consistent branding

## Color System

### Primary Academic Palette

```css
--primary-blue: #1e40af;        /* Main brand color */
--primary-blue-light: #3b82f6;  /* Interactive states */
--primary-blue-dark: #1e3a8a;   /* High emphasis */
--secondary-gray: #374151;      /* Supporting elements */
--secondary-gray-light: #6b7280; /* Muted content */
--secondary-gray-dark: #1f2937; /* Dark accents */
```

### Status Indication Colors

```css
--status-success: #059669;      /* Available/Working features */
--status-info: #0284c7;         /* Informational content */
--status-warning: #d97706;      /* Experimental/Partial features */
--status-error: #dc2626;        /* Broken/Deprecated features */
--status-neutral: #6b7280;      /* Planned/Draft features */
```

### Text Hierarchy

```css
--text-primary: #111827;        /* Main headings and content */
--text-secondary: #374151;      /* Body text and descriptions */
--text-muted: #6b7280;          /* Labels and metadata */
--text-inverse: #ffffff;        /* Text on dark backgrounds */
```

### Surface Colors

```css
--surface-primary: #ffffff;     /* Main content background */
--surface-secondary: #f9fafb;   /* Secondary panels */
--surface-tertiary: #f3f4f6;    /* Subtle backgrounds */
--surface-elevated: #ffffff;    /* Cards and elevated content */
```

## Typography System

### Font Stack

```css
--font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
--font-mono: "SF Mono", "Monaco", "Inconsolata", "Roboto Mono", "Source Code Pro", monospace;
--font-serif: "Georgia", "Times New Roman", serif; /* For citations */
```

### Type Scale

| Element | Size | Weight | Line Height | Usage |
|---------|------|--------|-------------|-------|
| H1 | 2rem | 700 | 1.2 | Page titles |
| H2 | 1.5rem | 600 | 1.3 | Section headings |
| H3 | 1.25rem | 600 | 1.4 | Subsection headings |
| Body | 1rem | 400 | 1.6 | Main content |
| Small | 0.875rem | 400 | 1.5 | Captions, metadata |
| Code | 0.875rem | 400 | 1.5 | Code blocks |

## Spacing System

### Consistent Spacing Scale

```css
--spacing-xs: 0.25rem;   /* 4px  - Tight spacing */
--spacing-sm: 0.5rem;    /* 8px  - Small gaps */
--spacing-md: 1rem;      /* 16px - Standard spacing */
--spacing-lg: 1.5rem;    /* 24px - Section spacing */
--spacing-xl: 2rem;      /* 32px - Large sections */
```

### Usage Guidelines

- **Component padding**: Use `--spacing-md` for standard padding
- **Section margins**: Use `--spacing-xl` between major sections
- **Element gaps**: Use `--spacing-sm` for small gaps, `--spacing-lg` for larger separations
- **Border radius**: `--border-radius-sm: 0.375rem`, `--border-radius-md: 0.5rem`

## Component Library

### Status Badges

Professional indicators for feature implementation status.

```html
<span class="status-badge status-available">Available</span>
<span class="status-badge status-verified">Verified</span>
<span class="status-badge status-experimental">Experimental</span>
<span class="status-badge status-planned">Planned</span>
<span class="status-badge status-deprecated">Deprecated</span>
```

**Sizing variants:**
- `.status-badge--sm` - For inline use
- `.status-badge--lg` - For prominent display

### Feature Cards

Structured cards for documenting features with status indicators.

```html
<div class="feature-card feature-card--available">
  <div class="feature-header">
    <h3 class="feature-title">Data Validation System</h3>
    <div class="feature-badges">
      <span class="status-badge status-available">Available</span>
      <span class="quality-badge quality-badge--peer-reviewed">Peer Reviewed</span>
    </div>
  </div>
  <div class="feature-content">
    <p>Comprehensive validation system for biomechanical datasets...</p>
  </div>
  <div class="verification-meta">
    <span class="last-verified last-verified--recent">Last verified: 2025-06-19</span>
    <div class="coverage-indicator coverage-indicator--high">
      <div class="coverage-bar">
        <div class="coverage-fill" style="width: 95%"></div>
      </div>
      <span class="coverage-percentage">95%</span>
    </div>
  </div>
</div>
```

**Status modifiers:**
- `.feature-card--available` - Green top border
- `.feature-card--verified` - Blue top border
- `.feature-card--partial` - Orange top border
- `.feature-card--planned` - Gray top border
- `.feature-card--broken` - Red top border

### Code Examples

Enhanced code blocks with copy functionality and status indicators.

```html
<div class="code-example code-example--tested">
  <div class="code-header">
    <span class="code-title">Python Example</span>
    <div class="code-actions">
      <span class="test-indicator test-indicator--passing">Tests Passing</span>
      <button class="code-copy-btn">Copy</button>
    </div>
  </div>
  <pre><code class="language-python">
import locomotion_analysis as la
data = la.LocomotionData.from_parquet('dataset.parquet')
  </code></pre>
</div>
```

**Status indicators:**
- `.test-indicator--passing` - Green checkmark
- `.test-indicator--failing` - Red X mark
- `.test-indicator--pending` - Orange circle

### Scientific Admonitions

Professional alert boxes for different types of information.

```html
<div class="admonition admonition--note">
  <div class="admonition-title">Research Note</div>
  <div class="admonition-content">
    <p>This validation approach has been peer-reviewed...</p>
  </div>
</div>
```

**Types available:**
- `.admonition--note` - Blue informational
- `.admonition--tip` - Green success
- `.admonition--warning` - Orange caution
- `.admonition--danger` - Red error
- `.admonition--quote` - Gray citation

### Academic Citations

Styled citation blocks for research references.

```html
<div class="citation">
  <div class="citation-content">
    The standardization of biomechanical data formats enables reproducible research across institutions and accelerates scientific discovery.
  </div>
  <div class="citation-author">
    Smith, J. et al. (2024). Biomechanical Data Standards. Journal of Biomechanics.
  </div>
</div>
```

### Interactive Elements

#### Collapsible Sections

```html
<div class="collapsible">
  <button class="collapsible-header">
    Detailed Implementation Notes
    <span class="collapsible-toggle">▼</span>
  </button>
  <div class="collapsible-content">
    <div class="collapsible-inner">
      <p>Detailed content that can be collapsed...</p>
    </div>
  </div>
</div>
```

#### Tab Containers

```html
<div class="tab-container">
  <div class="tab-list">
    <button class="tab-button active">Python</button>
    <button class="tab-button">MATLAB</button>
  </div>
  <div class="tab-content active">
    Python implementation details...
  </div>
  <div class="tab-content">
    MATLAB implementation details...
  </div>
</div>
```

### System Status Dashboard

Professional metrics display for system health.

```html
<div class="system-status">
  <h2 class="status-title">System Status Overview</h2>
  <div class="status-grid">
    <div class="status-item status-item--available">
      <div class="status-count">42</div>
      <div class="status-label">Available Features</div>
    </div>
    <div class="status-item status-item--verified">
      <div class="status-count">38</div>
      <div class="status-label">Verified Components</div>
    </div>
  </div>
  <p class="status-summary">All core systems operational</p>
</div>
```

### Research Metrics

```html
<div class="research-metrics">
  <div class="metric-card">
    <div class="metric-value">2,000+</div>
    <div class="metric-label">Gait Cycles</div>
    <div class="metric-description">Validated biomechanical data</div>
  </div>
  <div class="metric-card">
    <div class="metric-value">3</div>
    <div class="metric-label">Research Labs</div>
    <div class="metric-description">Contributing institutions</div>
  </div>
</div>
```

## Responsive Design Guidelines

### Breakpoints

```css
/* Mobile First Approach */
/* Base: 320px+ (Mobile) */
@media screen and (min-width: 769px)  { /* Tablet */ }
@media screen and (min-width: 1024px) { /* Desktop */ }
@media screen and (min-width: 1200px) { /* Large Desktop */ }
```

### Mobile Optimizations

- **Touch targets**: Minimum 44px for interactive elements
- **Readable text**: 16px base font size, never smaller than 14px
- **Optimized spacing**: Reduced spacing scale on mobile
- **Simplified navigation**: Collapsible sections for long content

## Dark Mode Support

Comprehensive dark mode with scientific professionalism maintained.

```css
[data-md-color-scheme="slate"] {
  --surface-primary: #1e293b;
  --surface-secondary: #334155;
  --text-primary: #f1f5f9;
  --text-secondary: #cbd5e1;
  /* Reduced opacity for status backgrounds */
  --status-success-bg: rgba(5, 150, 105, 0.15);
}
```

## Accessibility Requirements

### WCAG 2.1 AA Compliance

- **Color contrast**: Minimum 4.5:1 for normal text, 3:1 for large text
- **Focus indicators**: 3px solid outline with 2px offset
- **Screen reader support**: Semantic HTML with appropriate ARIA labels
- **Keyboard navigation**: All interactive elements accessible via keyboard

### Implementation Checklist

- [ ] Alt text for all images
- [ ] Proper heading hierarchy (H1 → H2 → H3)
- [ ] Skip links to main content
- [ ] ARIA labels for complex interactions
- [ ] Focus trap for modals/dialogs
- [ ] Reduced motion respect

## Performance Guidelines

### CSS Optimization

- **Efficient selectors**: Avoid deep nesting (max 3 levels)
- **CSS custom properties**: Use variables for consistency and performance
- **Critical CSS**: Inline above-the-fold styles
- **Minification**: Compress CSS for production

### JavaScript Performance

- **Lazy loading**: Images and non-critical content
- **Debounced interactions**: Search and scroll handlers
- **Intersection Observer**: For scroll-based animations
- **Performance monitoring**: Track interaction responsiveness

### Image Guidelines

- **Optimized formats**: WebP with fallbacks
- **Responsive images**: srcset for different screen sizes
- **Lazy loading**: Load images as they enter viewport
- **Alt text**: Descriptive alternative text for accessibility

## Print Optimization

Academic-friendly print styles for citations and documentation.

### Print-Specific Features

- **Academic headers**: Document title and page numbers
- **Citation formatting**: URL references for links
- **Page breaks**: Avoid breaking cards and code blocks
- **Color preservation**: Maintain status colors for clarity
- **Typography optimization**: 12pt base with optimal line spacing

## Usage Examples

### Basic Page Structure

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Locomotion Data Standardization</title>
  <link rel="stylesheet" href="extra.css">
</head>
<body>
  <a href="#main-content" class="skip-link">Skip to main content</a>
  
  <main id="main-content">
    <article class="feature-card feature-card--available">
      <!-- Content -->
    </article>
  </main>
  
  <script src="enhanced-interactivity.js"></script>
</body>
</html>
```

### Status-Aware Documentation

```markdown
# Data Validation <span class="status-badge status-available">Available</span>

Our validation system ensures data quality across all datasets.

<div class="feature-card feature-card--verified">
  <div class="feature-header">
    <h3 class="feature-title">Phase-Indexed Validation</h3>
    <div class="feature-badges">
      <span class="status-badge status-verified">Verified</span>
      <span class="quality-badge quality-badge--peer-reviewed">Peer Reviewed</span>
    </div>
  </div>
  <!-- Additional content -->
</div>
```

## Maintenance Guidelines

### Regular Updates

1. **Accessibility audit**: Monthly WCAG compliance check
2. **Performance review**: Quarterly load time analysis
3. **Color contrast**: Annual contrast ratio verification
4. **Component updates**: As needed for new features

### Version Control

- **Semantic versioning**: Major.Minor.Patch format
- **Changelog maintenance**: Document all visual changes
- **Component deprecation**: 6-month notice for breaking changes
- **Browser support**: Last 2 versions of major browsers

## Browser Support

### Primary Support
- **Chrome**: Last 2 versions
- **Firefox**: Last 2 versions  
- **Safari**: Last 2 versions
- **Edge**: Last 2 versions

### Progressive Enhancement
- **Intersection Observer**: Graceful fallback for lazy loading
- **CSS Grid**: Flexbox fallback for older browsers
- **Custom Properties**: Static values for IE11
- **Focus-visible**: Manual class management fallback

---

This style guide ensures consistent, accessible, and performant documentation that serves the needs of scientific and academic users while maintaining professional standards throughout the Locomotion Data Standardization project.