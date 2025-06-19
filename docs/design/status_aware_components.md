# Status-Aware Component Library

**Created:** 2025-06-19 with user permission  
**Purpose:** UI components that communicate feature availability and implementation status

## Component Overview

This library provides reusable components that help users distinguish between available, partial, planned, and broken features. Each component is designed to support honest communication about system capabilities.

## Core Status Indicators

### 1. Feature Status Badges

#### Available Feature Badge
```html
<span class="feature-badge feature-available">
  <span class="badge-icon">✅</span>
  <span class="badge-text">Available</span>
</span>
```

#### Tested Feature Badge
```html
<span class="feature-badge feature-verified">
  <span class="badge-icon">🧪</span>
  <span class="badge-text">Tested</span>
</span>
```

#### Partial Implementation Badge
```html
<span class="feature-badge feature-partial">
  <span class="badge-icon">⚠️</span>
  <span class="badge-text">Partial</span>
</span>
```

#### Planned Feature Badge
```html
<span class="feature-badge feature-planned">
  <span class="badge-icon">🚧</span>
  <span class="badge-text">Planned</span>
</span>
```

#### Broken Feature Badge
```html
<span class="feature-badge feature-broken">
  <span class="badge-icon">❌</span>
  <span class="badge-text">Not Working</span>
</span>
```

### CSS Styling
```css
.feature-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border-radius: 14px;
  font-size: 0.85em;
  font-weight: 500;
  margin-left: 8px;
  white-space: nowrap;
}

.badge-icon {
  font-size: 0.9em;
}

.badge-text {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

/* Status-specific styling */
.feature-available {
  background-color: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.feature-verified {
  background-color: #d1ecf1;
  color: #0c5460;
  border: 1px solid #bee5eb;
}

.feature-partial {
  background-color: #fff3cd;
  color: #856404;
  border: 1px solid #ffeaa7;
}

.feature-planned {
  background-color: #f8f9fa;
  color: #495057;
  border: 1px solid #dee2e6;
}

.feature-broken {
  background-color: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}
```

## Feature Documentation Components

### 2. Feature Overview Card

```html
<div class="feature-card">
  <div class="feature-header">
    <h3 class="feature-title">LocomotionData Library</h3>
    <div class="feature-badges">
      <span class="feature-badge feature-available">
        <span class="badge-icon">✅</span>
        <span class="badge-text">Available</span>
      </span>
      <span class="feature-badge feature-verified">
        <span class="badge-icon">🧪</span>
        <span class="badge-text">Tested</span>
      </span>
    </div>
  </div>
  
  <div class="feature-description">
    <p>Core library for loading and analyzing phase-indexed locomotion data with efficient 3D array operations.</p>
  </div>
  
  <div class="feature-details">
    <div class="feature-section">
      <h4 class="section-title">✅ What Works</h4>
      <ul class="feature-list">
        <li>3D array operations for gait cycle analysis</li>
        <li>Data quality assessment and outlier detection</li>
        <li>Publication-ready visualization tools</li>
        <li>Multi-format data loading (parquet, CSV)</li>
      </ul>
    </div>
    
    <div class="feature-section">
      <h4 class="section-title">⚠️ Current Limitations</h4>
      <ul class="feature-list">
        <li>Requires exact 150 points per gait cycle</li>
        <li>Phase-indexed data works best</li>
      </ul>
    </div>
    
    <div class="feature-section">
      <h4 class="section-title">🔗 Resources</h4>
      <ul class="feature-list">
        <li><a href="#" class="feature-link">API Documentation</a></li>
        <li><a href="#" class="feature-link">Working Examples</a></li>
        <li><a href="#" class="feature-link">Test Coverage Report</a></li>
      </ul>
    </div>
  </div>
  
  <div class="feature-meta">
    <span class="last-verified">Last verified: 2025-06-19</span>
    <span class="test-coverage">Test coverage: 95%</span>
  </div>
</div>
```

### Feature Card CSS
```css
.feature-card {
  border: 1px solid #e9ecef;
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 24px;
  background-color: #ffffff;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.feature-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.feature-title {
  font-size: 1.4em;
  font-weight: 600;
  margin: 0;
  color: #212529;
}

.feature-badges {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.feature-description {
  margin-bottom: 20px;
  color: #495057;
  line-height: 1.5;
}

.feature-section {
  margin-bottom: 16px;
}

.section-title {
  font-size: 1.1em;
  font-weight: 600;
  margin-bottom: 8px;
  color: #343a40;
}

.feature-list {
  margin: 0;
  padding-left: 20px;
}

.feature-list li {
  margin-bottom: 4px;
  color: #495057;
}

.feature-link {
  color: #007bff;
  text-decoration: none;
}

.feature-link:hover {
  text-decoration: underline;
}

.feature-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #e9ecef;
  font-size: 0.9em;
  color: #6c757d;
}
```

## Code Example Components

### 3. Tested Code Example

```html
<div class="code-example">
  <div class="code-header">
    <h4 class="code-title">Loading Locomotion Data</h4>
    <div class="code-badges">
      <span class="feature-badge feature-verified">
        <span class="badge-icon">🧪</span>
        <span class="badge-text">Tested</span>
      </span>
      <span class="test-status">✓ Passes all tests</span>
    </div>
  </div>
  
  <div class="code-block">
    <pre><code class="language-python">
from locomotion_analysis import LocomotionData

# Load phase-indexed data
loco = LocomotionData('dataset_phase.parquet')

# Get available subjects and tasks
subjects = loco.get_subjects()
tasks = loco.get_tasks()

# Analyze specific subject-task combination
data_3d, features = loco.get_cycles('SUB01', 'normal_walk')
mean_patterns = loco.get_mean_patterns('SUB01', 'normal_walk')
    </code></pre>
  </div>
  
  <div class="code-output">
    <h5>Expected Output:</h5>
    <pre class="output-text">
Data validation passed: 12 subjects, 3 tasks
Loaded data with 4500 rows, 12 subjects, 3 tasks, 18 features
Variable name validation: All 18 variables are standard compliant
    </pre>
  </div>
  
  <div class="code-meta">
    <span class="test-info">✓ Tested with demo_clean_phase.parquet</span>
    <span class="last-run">Last verified: 2025-06-19</span>
  </div>
</div>
```

### Code Example CSS
```css
.code-example {
  border: 1px solid #d1ecf1;
  border-radius: 6px;
  margin: 16px 0;
  background-color: #f8f9fa;
}

.code-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background-color: #e9ecef;
  border-bottom: 1px solid #d1ecf1;
}

.code-title {
  font-size: 1.1em;
  font-weight: 600;
  margin: 0;
  color: #495057;
}

.code-badges {
  display: flex;
  align-items: center;
  gap: 12px;
}

.test-status {
  font-size: 0.85em;
  color: #28a745;
  font-weight: 500;
}

.code-block {
  padding: 16px;
  background-color: #ffffff;
}

.code-block pre {
  margin: 0;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 0.9em;
  line-height: 1.4;
}

.code-output {
  padding: 12px 16px;
  background-color: #f8f9fa;
  border-top: 1px solid #e9ecef;
}

.code-output h5 {
  margin: 0 0 8px 0;
  font-size: 0.9em;
  color: #495057;
}

.output-text {
  background-color: #ffffff;
  border: 1px solid #e9ecef;
  border-radius: 4px;
  padding: 8px;
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 0.85em;
  color: #495057;
  margin: 0;
}

.code-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  background-color: #e9ecef;
  font-size: 0.8em;
  color: #6c757d;
}

.test-info {
  color: #28a745;
}
```

## Warning and Alert Components

### 4. Implementation Gap Warning

```html
<div class="alert alert-warning">
  <div class="alert-header">
    <span class="alert-icon">⚠️</span>
    <h4 class="alert-title">Implementation Gap</h4>
  </div>
  <div class="alert-content">
    <p>This CLI command has limited test coverage and may not handle all edge cases reliably.</p>
    <ul>
      <li><strong>Known Issue:</strong> May fail with datasets containing missing phase data</li>
      <li><strong>Workaround:</strong> Validate data format before processing</li>
      <li><strong>Status:</strong> Improvement planned for next release</li>
    </ul>
  </div>
</div>
```

### 5. Feature Limitation Notice

```html
<div class="alert alert-info">
  <div class="alert-header">
    <span class="alert-icon">ℹ️</span>
    <h4 class="alert-title">Current Limitations</h4>
  </div>
  <div class="alert-content">
    <p>This feature works well but has specific requirements:</p>
    <ul>
      <li>Requires phase-indexed data (150 points per cycle)</li>
      <li>Works best with standard variable naming convention</li>
      <li>May show warnings for time-indexed data</li>
    </ul>
  </div>
</div>
```

### Alert CSS
```css
.alert {
  border-radius: 6px;
  padding: 16px;
  margin: 16px 0;
  border-left: 4px solid;
}

.alert-warning {
  background-color: #fff3cd;
  border-left-color: #ffc107;
  color: #856404;
}

.alert-info {
  background-color: #d1ecf1;
  border-left-color: #17a2b8;
  color: #0c5460;
}

.alert-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.alert-icon {
  font-size: 1.2em;
}

.alert-title {
  font-size: 1.1em;
  font-weight: 600;
  margin: 0;
}

.alert-content p {
  margin: 0 0 8px 0;
}

.alert-content ul {
  margin: 0;
  padding-left: 20px;
}

.alert-content li {
  margin-bottom: 4px;
}
```

## Status Summary Components

### 6. System Status Dashboard

```html
<div class="system-status">
  <h3 class="status-title">System Status Overview</h3>
  
  <div class="status-grid">
    <div class="status-item status-available">
      <div class="status-count">8</div>
      <div class="status-label">Available Features</div>
    </div>
    
    <div class="status-item status-verified">
      <div class="status-count">6</div>
      <div class="status-label">Fully Tested</div>
    </div>
    
    <div class="status-item status-partial">
      <div class="status-count">2</div>
      <div class="status-label">Partial Implementation</div>
    </div>
    
    <div class="status-item status-planned">
      <div class="status-count">3</div>
      <div class="status-label">Planned Features</div>
    </div>
  </div>
  
  <div class="status-details">
    <p class="status-summary">
      <strong>95% of core features are available and tested.</strong>
      The system is ready for production use with documented limitations.
    </p>
  </div>
</div>
```

### Status Dashboard CSS
```css
.system-status {
  background-color: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  padding: 20px;
  margin: 24px 0;
}

.status-title {
  font-size: 1.3em;
  font-weight: 600;
  margin: 0 0 16px 0;
  color: #343a40;
}

.status-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}

.status-item {
  text-align: center;
  padding: 16px;
  border-radius: 6px;
  border: 2px solid;
}

.status-item.status-available {
  background-color: #d4edda;
  border-color: #28a745;
}

.status-item.status-verified {
  background-color: #d1ecf1;
  border-color: #007bff;
}

.status-item.status-partial {
  background-color: #fff3cd;
  border-color: #ffc107;
}

.status-item.status-planned {
  background-color: #f8f9fa;
  border-color: #6c757d;
}

.status-count {
  font-size: 2em;
  font-weight: 700;
  margin-bottom: 4px;
}

.status-label {
  font-size: 0.9em;
  font-weight: 500;
}

.status-summary {
  text-align: center;
  color: #495057;
  margin: 0;
}
```

## Usage Guidelines

### For Documentation Authors
1. Always include appropriate status badges
2. Use feature cards for major functionality
3. Show actual, tested code examples
4. Include implementation gaps and warnings
5. Update status when features change

### For Users
1. ✅ **Available** = Safe for production use
2. 🧪 **Tested** = Has comprehensive test coverage  
3. ⚠️ **Partial** = Works but has limitations
4. 🚧 **Planned** = Future functionality, don't rely on
5. ❌ **Not Working** = Known issues, avoid using

### Mobile Responsiveness
All components are designed to work on mobile devices:
- Responsive grid layouts
- Touch-friendly interactive elements
- Readable text sizes
- Accessible color contrast

This component library ensures users can quickly identify what features are ready for use and understand the current state of system capabilities.