# Truth-Oriented Design System

**Created:** 2025-06-19 with user permission  
**Purpose:** Visual design language that prioritizes truthful communication of system capabilities

## Design Philosophy

This design system is built on the principle of **truthful documentation** - visual elements must accurately represent the actual state of features and capabilities, not aspirational or planned functionality.

### Core Principles

1. **Status Transparency**: Every feature must be visually marked with its actual implementation status
2. **Verification Priority**: Working, tested features receive visual prominence
3. **Honest Limitation Communication**: Gaps and limitations are clearly communicated
4. **Trust Building**: Professional aesthetics that convey reliability and accuracy
5. **Reality-Based Hierarchy**: Content organization prioritizes actually-available functionality

## Visual Status Language

### Feature Status Colors

```css
/* Status-based color system */
:root {
  /* Available Features - Green family */
  --available-primary: #28a745;      /* Fully working features */
  --available-light: #d4edda;        /* Available feature backgrounds */
  --available-border: #c3e6cb;       /* Available feature borders */
  
  /* Tested/Verified - Blue family */
  --verified-primary: #007bff;       /* Tested and documented */
  --verified-light: #d1ecf1;         /* Verified feature backgrounds */
  --verified-border: #bee5eb;        /* Verified feature borders */
  
  /* Partial Implementation - Orange family */
  --partial-primary: #fd7e14;        /* Working but limited */
  --partial-light: #fff3cd;          /* Partial feature backgrounds */
  --partial-border: #ffeaa7;         /* Partial feature borders */
  
  /* Planned/Future - Gray family */
  --planned-primary: #6c757d;        /* Future functionality */
  --planned-light: #f8f9fa;          /* Planned feature backgrounds */
  --planned-border: #dee2e6;         /* Planned feature borders */
  
  /* Not Working - Red family */
  --broken-primary: #dc3545;         /* Known issues */
  --broken-light: #f8d7da;           /* Broken feature backgrounds */
  --broken-border: #f5c6cb;          /* Broken feature borders */
  
  /* Warning/Caution - Yellow family */
  --warning-primary: #ffc107;        /* Requires attention */
  --warning-light: #fff3cd;          /* Warning backgrounds */
  --warning-border: #ffeaa7;         /* Warning borders */
}
```

### Typography Hierarchy

```css
/* Truth-focused typography */
.feature-available {
  font-weight: 600;
  color: var(--available-primary);
}

.feature-verified {
  font-weight: 500;
  color: var(--verified-primary);
}

.feature-partial {
  font-weight: 500;
  color: var(--partial-primary);
  font-style: italic;
}

.feature-planned {
  font-weight: 400;
  color: var(--planned-primary);
  opacity: 0.7;
}

.feature-broken {
  font-weight: 500;
  color: var(--broken-primary);
  text-decoration: line-through;
}
```

## Implementation Status Framework

### Current System Analysis

Based on codebase analysis, here's the actual implementation status:

#### ✅ **Fully Available & Tested**
- **LocomotionData Library**: Complete with 3D array operations, validation, plotting
- **Phase Validation System**: Working with comprehensive test coverage
- **Dataset Conversion Tools**: Functional for GTech 2023, UMich 2021, AddBiomechanics
- **Visualization System**: Plots, GIFs, validation reports all working
- **Tutorial System**: Python and MATLAB tutorials tested and verified

#### ⚠️ **Partial Implementation** 
- **CLI Tools**: Most working but some coverage gaps identified in tests
- **Agent Framework**: Present but appears to be development/experimental

#### 🚧 **Planned/Future**
- **Advanced ML Benchmarking**: Framework exists but may need development
- **Automated Documentation**: System present but integration unclear

#### ❌ **Known Limitations**
- Some CLI commands may have incomplete coverage
- Agent framework stability unclear

### Visual Status Indicators

#### Status Badges
```html
<!-- Available Feature -->
<span class="status-badge status-available">
  ✅ Available
</span>

<!-- Verified/Tested -->
<span class="status-badge status-verified">
  🧪 Tested
</span>

<!-- Partial Implementation -->
<span class="status-badge status-partial">
  ⚠️ Partial
</span>

<!-- Planned Feature -->
<span class="status-badge status-planned">
  🚧 Planned
</span>

<!-- Not Working -->
<span class="status-badge status-broken">
  ❌ Not Working
</span>
```

#### CSS for Status Badges
```css
.status-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.8em;
  font-weight: 500;
  margin-left: 8px;
}

.status-available {
  background-color: var(--available-light);
  color: var(--available-primary);
  border: 1px solid var(--available-border);
}

.status-verified {
  background-color: var(--verified-light);
  color: var(--verified-primary);
  border: 1px solid var(--verified-border);
}

.status-partial {
  background-color: var(--partial-light);
  color: var(--partial-primary);
  border: 1px solid var(--partial-border);
}

.status-planned {
  background-color: var(--planned-light);
  color: var(--planned-primary);
  border: 1px solid var(--planned-border);
}

.status-broken {
  background-color: var(--broken-light);
  color: var(--broken-primary);
  border: 1px solid var(--broken-border);
}
```

## Truth-Supporting Content Patterns

### Feature Documentation Template

Every feature should follow this truthful documentation pattern:

```markdown
## Feature Name [Status Badge]

### What Actually Works
- Specific, tested functionality
- Links to working examples
- Actual performance characteristics

### Current Limitations
- Known issues or gaps
- Workarounds if available
- Expected behavior vs actual behavior

### Verification Status
- Test coverage level
- Last verified date
- Testing methodology used

### Usage Examples
- Only examples that actually work
- Real data/output shown
- Error conditions documented
```

### Content Hierarchy Principles

1. **Working First**: Available features get top billing
2. **Verified Prominence**: Tested functionality highlighted
3. **Honest Sequencing**: Limitations follow capabilities, not hidden
4. **Reality Check**: No "coming soon" without clear timelines

## Trust-Building Visual Elements

### Professional Aesthetics
- Clean, scientific styling that conveys accuracy
- Consistent spacing and alignment
- High contrast for accessibility
- Clear visual hierarchy

### Verification Indicators
- Checkmarks for tested features
- Test coverage percentages where available
- "Last verified" dates
- Links to actual test results

### Error-Honest Design
- Clear error state styling
- Helpful error messages
- Recovery guidance
- No hidden failures

## Implementation Guidelines

### For Documentation Authors
1. Always include status badges
2. Test examples before publishing
3. Update status when implementations change
4. Include "last verified" dates

### For Developers
1. Update status badges when code changes
2. Maintain test coverage for "Available" features
3. Document known limitations honestly
4. Provide working examples only

### For Users
1. Visual indicators show feature reliability
2. "Available" = safe to use in production
3. "Partial" = use with caution
4. "Planned" = don't rely on yet

## Responsive Design Considerations

Status indicators must work across devices:
- Mobile-friendly badge sizing
- Touch-friendly interactive elements
- High contrast for accessibility
- Text alternatives for color-blind users

## Accessibility Standards

- WCAG 2.1 AA compliance
- Status conveyed through text, not just color
- Screen reader friendly markup
- Keyboard navigation support

This design system ensures that all visual elements support truthful communication about system capabilities, building user trust through honest representation of what actually works.