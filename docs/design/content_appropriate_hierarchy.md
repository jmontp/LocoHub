# Content-Appropriate Visual Hierarchy

**Created:** 2025-06-19 with user permission  
**Purpose:** Visual hierarchy system that prioritizes working features and honest capability communication

## Hierarchy Philosophy

This system organizes content based on **actual implementation status** rather than aspirational goals or traditional feature importance. Users see what works first, with clear guidance about limitations and gaps.

## Priority Levels

### 1. **Primary Priority** - Available & Tested Features
Features that are fully implemented, tested, and ready for production use.

**Visual Treatment:**
- Top positioning in navigation and content
- High contrast, prominent styling
- Green/blue color family
- Bold typography weights
- Immediate visibility on page load

**Content Organization:**
1. Core working functionality first
2. Well-tested features with high coverage
3. Production-ready tools and libraries
4. Complete documentation with examples

**Current Primary Features:**
- LocomotionData Library (95% test coverage)
- Phase Validation System (90% test coverage)  
- Tutorial System (tested and verified)
- Visualization Tools (working plots and GIFs)

### 2. **Secondary Priority** - Partial Implementation
Features that work but have known limitations or incomplete coverage.

**Visual Treatment:**
- Secondary positioning after primary features
- Orange/yellow warning indicators
- Clear limitation callouts
- Medium typography weights
- Conditional visibility (may be filtered)

**Content Organization:**
1. What actually works
2. Known limitations prominently displayed
3. Workarounds and best practices
4. Clear usage guidance

**Current Secondary Features:**
- CLI Tools (some coverage gaps)
- Agent Framework (development status unclear)

### 3. **Tertiary Priority** - Planned Features
Future functionality that's documented but not yet implemented.

**Visual Treatment:**
- Lower visual hierarchy
- Gray color family with reduced opacity
- "Coming soon" or "Planned" indicators
- Lighter typography weights
- Often filtered out by default

**Content Organization:**
1. Clear "planned" status indication
2. Expected timeline if available
3. No working examples
4. Link to tracking issues/roadmap

### 4. **Warning Priority** - Broken/Not Working
Features with known issues that should not be used.

**Visual Treatment:**
- Red warning indicators
- Strike-through text styling
- Clear "Do not use" messaging
- High visibility warnings
- May be hidden by default

**Content Organization:**
1. Clear problem statement
2. Why it doesn't work
3. Alternative approaches
4. Timeline for fixes if available

## Implementation Guidelines

### Navigation Hierarchy

```html
<!-- Primary navigation prioritizes working features -->
<nav class="main-navigation">
  <section class="nav-primary">
    <h2>Ready to Use</h2>
    <a href="/locomotion-data-library" class="nav-link available">
      LocomotionData Library
      <span class="status-badge status-available">✅ Available</span>
    </a>
    <a href="/phase-validation" class="nav-link available">
      Phase Validation
      <span class="status-badge status-verified">🧪 Tested</span>
    </a>
    <a href="/tutorials" class="nav-link available">
      Tutorials
      <span class="status-badge status-verified">🧪 Tested</span>
    </a>
  </section>
  
  <section class="nav-secondary">
    <h2>Limited Availability</h2>
    <a href="/cli-tools" class="nav-link partial">
      CLI Tools
      <span class="status-badge status-partial">⚠️ Partial</span>
    </a>
  </section>
  
  <section class="nav-tertiary">
    <h2>Future Features</h2>
    <a href="/advanced-ml" class="nav-link planned">
      Advanced ML Benchmarks
      <span class="status-badge status-planned">🚧 Planned</span>
    </a>
  </section>
</nav>
```

### Page Layout Hierarchy

```css
/* Content hierarchy based on implementation status */
.content-layout {
  display: grid;
  grid-template-areas:
    "available-features"
    "tested-features" 
    "partial-features"
    "planned-features";
  gap: 32px;
}

.available-features {
  grid-area: available-features;
  order: 1;
}

.tested-features {
  grid-area: tested-features;
  order: 2;
}

.partial-features {
  grid-area: partial-features;
  order: 3;
}

.planned-features {
  grid-area: planned-features;
  order: 4;
  opacity: 0.7;
}

/* Visual prominence by status */
.feature-section.available {
  border-left: 4px solid var(--status-available);
  background-color: var(--status-available-bg);
}

.feature-section.partial {
  border-left: 4px solid var(--status-partial);
  background-color: var(--status-partial-bg);
}

.feature-section.planned {
  border-left: 4px solid var(--status-planned);
  background-color: var(--status-planned-bg);
}
```

## Content Structure Patterns

### Feature Introduction Template

```markdown
# Feature Name [Status Badge]

## Quick Start (Available Features Only)
*This section only appears for available/tested features*

## What Actually Works
*Prominent section listing verified functionality*

## Current Limitations  
*Honest assessment of gaps and issues*

## Implementation Status
*Detailed status with test coverage and verification dates*

## Future Plans
*Roadmap information if applicable*
```

### Documentation Page Hierarchy

1. **Hero Section** - Working features with clear status
2. **Quick Start** - Available functionality only
3. **Core Features** - Organized by implementation status
4. **Advanced Features** - Partial implementations with warnings
5. **API Reference** - Status-coded by endpoint/method
6. **Future Roadmap** - Planned features clearly marked

### Search Result Prioritization

```javascript
// Search results prioritized by implementation status
const searchResultPriority = {
  'available': 100,
  'verified': 95,
  'partial': 70,
  'planned': 30,
  'broken': 10
};

function prioritizeSearchResults(results) {
  return results.sort((a, b) => {
    const aPriority = searchResultPriority[a.status] || 50;
    const bPriority = searchResultPriority[b.status] || 50;
    return bPriority - aPriority;
  });
}
```

## Responsive Hierarchy

### Desktop Layout
- Three-column layout with status-based sections
- Prominent sidebar for available features
- Clear visual separation between status levels

### Tablet Layout
- Two-column with collapsible status sections
- Filtering controls for status-based viewing
- Maintained visual hierarchy with compact styling

### Mobile Layout
- Single column with accordion-style status sections
- "Available First" default view
- Easy filtering between status levels

```css
/* Responsive hierarchy adjustments */
@media (max-width: 768px) {
  .content-layout {
    grid-template-areas:
      "status-filter"
      "primary-content";
  }
  
  /* Mobile-first: show available features by default */
  .feature-section.planned,
  .feature-section.partial {
    display: none;
  }
  
  .feature-section.planned.show-planned,
  .feature-section.partial.show-partial {
    display: block;
  }
}
```

## Accessibility Considerations

### Screen Reader Hierarchy
- Clear heading structure (h1-h6) based on implementation status
- ARIA landmarks for different status sections
- Skip links to "Available Features" section

### Keyboard Navigation
- Tab order prioritizes available features
- Status-based keyboard shortcuts (Alt+1 for Available, etc.)
- Clear focus indicators with status context

### Visual Indicators
- High contrast status indicators
- Color + text + icon combinations for status
- Clear text alternatives for all visual status elements

```html
<!-- Accessible status indication -->
<section aria-labelledby="available-features" class="feature-section available">
  <h2 id="available-features">
    Available Features
    <span class="sr-only">Fully implemented and tested features ready for production use</span>
  </h2>
  <!-- Feature content -->
</section>
```

## Content Strategy Alignment

### Documentation Writing Guidelines

1. **Lead with Working Features**
   - Start every page with what actually works
   - Provide working examples first
   - Save limitations for after demonstrating capabilities

2. **Honest Limitation Communication**
   - Clear, specific limitation descriptions
   - Suggested workarounds when available
   - Timeline for improvements if known

3. **Status-Aware Language**
   - "Currently supports..." (not "supports")
   - "Available in this release..." (not "will be available")
   - "Known limitations include..." (not hidden in footnotes)

### Example Application: LocomotionData Library Page

```markdown
# LocomotionData Library ✅ Available 🧪 Tested

## What Works Right Now

The LocomotionData library provides production-ready functionality for:
- Loading phase-indexed datasets (parquet, CSV)
- 3D array operations for gait cycle analysis  
- Data validation and quality assessment
- Publication-ready visualizations

[Working Code Example - Tested 2025-06-19]

## Current Limitations

- Requires exactly 150 points per gait cycle
- Works best with phase-indexed data
- Time-indexed data shows warnings but functions

## Implementation Status

- **Test Coverage:** 95%
- **Last Verified:** 2025-06-19
- **Production Ready:** Yes
- **Breaking Changes:** None planned

## Future Enhancements

🚧 Planned for next release:
- Support for variable cycle lengths
- Enhanced time-indexed data handling
```

## Implementation Checklist

### For Content Creators
- [ ] Lead with working functionality
- [ ] Include status badges on all features
- [ ] Provide honest limitation assessments
- [ ] Use status-appropriate visual hierarchy
- [ ] Include verification dates and test coverage

### For Designers
- [ ] Implement status-based visual priority
- [ ] Create clear status indicator system
- [ ] Design responsive hierarchy patterns
- [ ] Ensure accessibility compliance
- [ ] Test with real content constraints

### For Developers
- [ ] Implement status-aware navigation
- [ ] Create filtering and search prioritization
- [ ] Add interactive status enhancements
- [ ] Maintain status accuracy through CI/CD
- [ ] Track user interaction with status elements

This hierarchy system ensures users immediately see what they can actually use while maintaining honest communication about system limitations and future plans.