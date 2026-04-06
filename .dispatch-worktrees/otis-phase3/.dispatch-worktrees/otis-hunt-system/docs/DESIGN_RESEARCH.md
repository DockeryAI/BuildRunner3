# Design Research - Pattern Extraction

**How BuildRunner extracts design patterns from existing applications to improve profiles.**

---

## Overview

BuildRunner's design research system analyzes successful applications in each industry to extract:
- Common color patterns
- UI component usage
- Navigation patterns
- Compliance implementations
- UX best practices

---

## How It Works

### 1. Pattern Extraction

```bash
br design research <industry>
```

**What it analyzes:**
- Top 50+ apps in the industry
- Color palette frequency
- Component library patterns
- Navigation structure preferences
- Layout conventions
- Accessibility implementations

### 2. Best Practices Compilation

**Sources:**
- Industry leaders (top 10 apps by usage)
- Design systems (Material, Apple HIG, etc.)
- Compliance documentation
- Accessibility guidelines

### 3. Pattern Validation

**Criteria:**
- Used by 70%+ of leading apps
- Proven conversion/engagement metrics
- Accessibility compliant
- Mobile-responsive by default

---

## Research Output

### Healthcare Example

```bash
br design research healthcare
```

**Output:**
```yaml
analyzed_apps: 52
timeframe: Last updated 2025-01

color_patterns:
  primary_blue:
    frequency: 87%  # 45 of 52 apps
    common_shades:
      - "#0066CC"  # Trust blue
      - "#0052A3"  # Darker variant
      - "#1976D2"  # Material blue

  medical_green:
    frequency: 73%
    common_shades:
      - "#00A86B"  # Medical green
      - "#4CAF50"  # Success green

navigation_patterns:
  sidebar: 78%          # Most common
  bottom_tabs: 15%      # Mobile apps
  top_tabs: 7%          # Rare

layout_preferences:
  card_based: 92%       # Overwhelming majority
  table_based: 45%      # Often combined with cards
  list_based: 38%

compliance_implementations:
  hipaa_audit_log: 100%      # Required
  session_timeout: 95%       # Standard: 15 min
  phi_encryption: 100%       # Required
  role_based_access: 98%

accessibility:
  wcag_aa: 89%          # Most apps
  wcag_aaa: 23%         # Premium apps
  screen_reader: 95%    # Standard
```

---

## CLI Usage

### Research Specific Industry

```bash
# Full research report
br design research healthcare

# JSON output for programmatic use
br design research fintech --format json

# Compare multiple industries
br design research healthcare fintech --compare
```

### Update Research Data

```bash
# Update local research database
br design research --update

# Force re-analysis
br design research healthcare --refresh
```

---

## Integration with PRD Wizard

Design research automatically informs:
- **Color suggestions** - Most common industry colors
- **Component recommendations** - Proven component libraries
- **Navigation patterns** - Industry-standard navigation
- **Compliance checklists** - Required security/privacy measures

### Automatic Research

```bash
# PRD wizard automatically runs design research
br spec wizard

# Select: Healthcare + Dashboard
# Wizard uses research data to suggest:
# - Primary color: #0066CC (used by 87% of healthcare apps)
# - Navigation: Sidebar (used by 78%)
# - Layout: Card-based grid (used by 92%)
```

---

## Customizing Research

### Add Custom Data Sources

```yaml
# .buildrunner/design_research.yaml
custom_sources:
  healthcare:
    - url: https://example-health-app.com
      weight: high  # Prioritize this example

    - url: https://competitor-app.com
      weight: medium
```

### Override Pattern Priorities

```yaml
pattern_overrides:
  healthcare:
    colors:
      primary: "#0052A3"  # Prefer this over extracted average
    navigation:
      preferred: sidebar  # Always suggest sidebar
```

---

## Pattern Categories

### 1. Visual Design Patterns

**Colors:**
- Primary brand colors
- Secondary/accent colors
- Semantic colors (success, error, warning)
- Neutral palettes

**Typography:**
- Heading font families
- Body text fonts
- Code/monospace fonts
- Font size scales

### 2. Layout Patterns

**Grid Systems:**
- Column counts (12, 16, 24)
- Gutter sizes
- Breakpoints (mobile, tablet, desktop)

**Component Spacing:**
- Padding scales
- Margin scales
- Border radius values

### 3. Component Patterns

**Common Components:**
- Card styles (shadow, border, padding)
- Button variants (primary, secondary, ghost)
- Form controls (inputs, selects, checkboxes)
- Navigation (sidebar, tabs, breadcrumbs)

### 4. Interaction Patterns

**User Flows:**
- Onboarding sequences
- Checkout processes
- Form validation approaches
- Error messaging

**Animations:**
- Transition durations
- Easing functions
- Loading states

### 5. Compliance Patterns

**Security:**
- Authentication flows (password, 2FA, biometric)
- Session management (timeouts, persistence)
- Data encryption approaches

**Privacy:**
- Consent flows
- Data export formats
- Deletion procedures

---

## Research Methodology

### Data Collection

1. **Automated Scraping:**
   - Public design systems
   - Open-source app repositories
   - Style guides

2. **Manual Curation:**
   - Industry leader analysis
   - Design award winners
   - Compliance case studies

3. **Community Contributions:**
   - User-submitted examples
   - Design pattern submissions

### Analysis Process

1. **Pattern Extraction:**
   - Color palette extraction (dominant colors)
   - Component identification (CSS selectors)
   - Layout analysis (grid inspection)

2. **Frequency Calculation:**
   - Count pattern occurrences
   - Weight by app popularity
   - Filter outliers

3. **Validation:**
   - Accessibility testing
   - Mobile responsiveness check
   - Cross-browser compatibility

### Update Frequency

- **Minor updates:** Monthly (new app additions)
- **Major updates:** Quarterly (pattern re-analysis)
- **Compliance updates:** As regulations change

---

## Pattern Confidence Scores

Each extracted pattern includes a confidence score:

```yaml
pattern: sidebar_navigation
confidence: 0.78  # 78% of apps use this
sample_size: 52   # Based on 52 analyzed apps
last_updated: "2025-01-15"
```

**Confidence Levels:**
- **90-100%:** Industry standard (use by default)
- **70-89%:** Common pattern (suggest with confidence)
- **50-69%:** Alternative pattern (offer as option)
- **<50%:** Rare pattern (don't suggest)

---

## Contributing Research

### Submit New Patterns

```bash
# Submit app for analysis
br design research submit \
  --industry healthcare \
  --url https://new-healthcare-app.com \
  --category ehr

# Submit design system
br design research submit \
  --industry fintech \
  --design-system stripe \
  --url https://stripe.com/docs/design
```

### Report Outdated Patterns

```bash
# Flag pattern as outdated
br design research flag \
  --industry healthcare \
  --pattern sidebar_navigation \
  --reason "Mobile-first apps now use bottom tabs"
```

---

## Research Database

### Local Cache

```
~/.buildrunner/research/
├── healthcare.json      # Healthcare patterns
├── fintech.json         # Fintech patterns
├── ecommerce.json       # E-commerce patterns
└── metadata.json        # Last updated timestamps
```

### Remote Sync

```bash
# Sync with BuildRunner research database
br design research sync

# View sync status
br design research sync --status
```

---

## Privacy & Ethics

**Data Collection:**
- ✅ Only public design information
- ✅ No user data or analytics
- ✅ No proprietary code or assets
- ❌ No competitive intelligence gathering

**Usage:**
- Patterns used for educational/guidance purposes
- No direct copying of implementations
- Encourages best practices, not plagiarism

---

## Related Documentation

- **[Design System](DESIGN_SYSTEM.md)** - How patterns are used
- **[Industry Profiles](INDUSTRY_PROFILES.md)** - Industry-specific patterns
- **[Use Case Patterns](USE_CASE_PATTERNS.md)** - Application type patterns
- **[PRD Wizard](PRD_WIZARD.md)** - Integration with project setup

---

## FAQ

**Q: How often is research data updated?**
A: Monthly for minor updates, quarterly for major pattern re-analysis.

**Q: Can I contribute my own app to the research database?**
A: Yes! Use `br design research submit` to add your app for analysis.

**Q: Is the research data open source?**
A: Pattern frequency data is open. Individual app analyses are aggregated for privacy.

**Q: How do I disable automatic research in the wizard?**
A: Use `br spec wizard --no-research` to skip pattern suggestions.

---

**Design Research** - Data-driven design decisions powered by industry leaders 📊
