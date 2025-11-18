# Design System - Industry Intelligence

**BuildRunner 3.0's design system automatically generates pixel-perfect designs from industry patterns and use case templates.**

---

## Table of Contents

- [Overview](#overview)
- [Industry Profiles](#industry-profiles)
- [Use Case Patterns](#use-case-patterns)
- [Profile Merging Algorithm](#profile-merging-algorithm)
- [Tailwind Config Generation](#tailwind-config-generation)
- [Compliance Requirements](#compliance-requirements)
- [CLI Usage](#cli-usage)
- [Examples](#examples)

---

## Overview

The Design System solves a critical problem in AI-assisted development: **inconsistent visual design and missing industry best practices**.

### The Problem

When building with AI:
- ❌ Generic designs that don't fit industry standards
- ❌ Missing compliance requirements (HIPAA, PCI DSS, etc.)
- ❌ Inconsistent color schemes and component patterns
- ❌ No accessibility considerations
- ❌ Every project starts from scratch

### The Solution

BuildRunner's Design System provides:
- ✅ **8 industry profiles** with compliance built-in
- ✅ **8 use case patterns** with proven UX patterns
- ✅ **Intelligent profile merging** with conflict resolution
- ✅ **Auto-generated Tailwind configs** ready to use
- ✅ **Accessibility by default** (WCAG 2.1 AA+)

---

## Industry Profiles

Industry profiles provide domain-specific design guidance:

### Available Industries

1. **Healthcare** - Medical apps, patient portals, telemedicine
2. **Fintech** - Banking, payments, investment platforms
3. **E-commerce** - Online stores, marketplaces, retail
4. **SaaS** - B2B software, productivity tools, platforms
5. **Education** - Learning platforms, course management, EdTech
6. **Social** - Social networks, community platforms, messaging
7. **Marketplace** - Multi-vendor platforms, gig economy, listings
8. **Analytics** - BI tools, dashboards, data visualization

### Industry Profile Structure

Each industry profile includes:

```yaml
name: healthcare
display_name: Healthcare & Medical
description: "Healthcare applications with HIPAA compliance..."

# Visual Design
colors:
  primary: "#0066CC"      # Trust blue
  secondary: "#00A86B"    # Medical green
  accent: "#FF6B6B"       # Alert red
  neutral: "#F5F5F5"      # Clinical white

typography:
  heading_font: "Inter"
  body_font: "Inter"
  mono_font: "JetBrains Mono"

# Compliance & Regulations
compliance:
  - HIPAA              # Health Insurance Portability
  - WCAG 2.1 AA        # Accessibility
  - ADA                # Americans with Disabilities Act
  - 21 CFR Part 11     # FDA Electronic Records

# Security Requirements
security:
  - end_to_end_encryption
  - audit_logging
  - role_based_access
  - phi_protection     # Protected Health Information

# UI Components
components:
  - PatientCard
  - VitalsWidget
  - MedicationList
  - AppointmentScheduler
  - HealthRecordViewer
  - ConsentForm

# Design Patterns
patterns:
  layout: clinical-minimal  # Clean, distraction-free
  navigation: sidebar       # Persistent access to sections
  data_entry: guided        # Step-by-step forms with validation
```

### Compliance by Industry

| Industry | Primary Compliance | Security Focus |
|----------|-------------------|----------------|
| Healthcare | HIPAA, 21 CFR Part 11 | PHI encryption, audit logs |
| Fintech | PCI DSS, SOC 2 | Financial data, fraud detection |
| E-commerce | PCI DSS, GDPR | Payment security, privacy |
| SaaS | SOC 2, ISO 27001 | Data security, availability |
| Education | FERPA, COPPA | Student data privacy |
| Social | GDPR, CCPA | User data, consent |
| Marketplace | PCI DSS, Consumer laws | Escrow, fraud prevention |
| Analytics | GDPR, SOC 2 | Data processing, anonymization |

---

## Use Case Patterns

Use case patterns provide UX patterns for specific application types:

### Available Use Cases

1. **Dashboard** - Overview screens, KPI displays, monitoring
2. **Marketplace** - Product listings, filters, transactions
3. **CRM** - Contact management, pipeline, activities
4. **Analytics** - Charts, reports, data exploration
5. **Onboarding** - User activation, guided setup, trials
6. **API Service** - Developer portals, documentation, keys
7. **Admin Panel** - System configuration, user management
8. **Mobile App** - Mobile-first layouts, gestures, native feel

### Use Case Pattern Structure

Each use case pattern includes:

```yaml
name: dashboard
display_name: Dashboard & Monitoring
description: "Real-time overview with KPIs and data visualization..."

# Layout Structure
layout:
  type: grid
  columns: 12
  responsive: true
  breakpoints:
    mobile: 1
    tablet: 2
    desktop: 3

# Navigation
navigation:
  type: sidebar
  position: left
  collapsible: true
  items:
    - Overview
    - Analytics
    - Reports
    - Settings

# Data Visualization
data_viz:
  - LineChart        # Trends over time
  - BarChart         # Comparisons
  - PieChart         # Proportions
  - MetricCard       # Single KPI
  - Sparkline        # Inline trends
  - Heatmap          # Pattern visualization

# Components
components:
  - DashboardGrid
  - KPICard
  - ChartWidget
  - TableView
  - FilterPanel
  - DateRangePicker
  - ExportButton

# Interaction Patterns
interactions:
  - drill_down      # Click to see details
  - time_range      # Filter by date
  - real_time       # Live updates
  - export          # Download data
```

### Pattern-Specific Features

| Use Case | Key Features | Components |
|----------|-------------|------------|
| Dashboard | KPIs, charts, real-time | MetricCard, ChartWidget, FilterPanel |
| Marketplace | Search, filters, checkout | ProductCard, CartWidget, ReviewsSection |
| CRM | Contacts, pipeline, tasks | ContactCard, PipelineView, ActivityFeed |
| Analytics | Charts, reports, exports | ChartLibrary, ReportBuilder, DataTable |
| Onboarding | Steps, progress, tutorials | WizardSteps, ProgressBar, TooltipGuide |
| API Service | Docs, examples, keys | CodeBlock, EndpointCard, APIKeyManager |
| Admin Panel | Tables, forms, permissions | DataTable, FormBuilder, RoleManager |
| Mobile App | Touch, gestures, offline | SwipeCard, PullToRefresh, OfflineIndicator |

---

## Profile Merging Algorithm

When you specify both industry and use case, BuildRunner merges them intelligently:

### Merge Priority Rules

```python
# Industry wins for:
- colors.primary       # Brand identity
- colors.secondary     # Brand identity
- compliance           # Regulatory requirements
- security             # Security requirements

# Use case wins for:
- layout               # UX pattern
- navigation           # Navigation style
- data_viz             # Visualization needs

# Union merge (combine both):
- components           # All components from both
- patterns             # All patterns from both

# Conflict resolution:
- typography           # Industry provides brand, use case provides hierarchy
```

### Merge Example

**Input:**
- Industry: `healthcare`
- Use Case: `dashboard`

**Merged Profile:**

```yaml
# From Healthcare (industry wins)
colors:
  primary: "#0066CC"      # Healthcare blue
  secondary: "#00A86B"    # Medical green

compliance:
  - HIPAA
  - WCAG 2.1 AA

# From Dashboard (use case wins)
layout:
  type: grid
  columns: 12

navigation:
  type: sidebar
  position: left

# Combined (union)
components:
  # From Healthcare:
  - PatientCard
  - VitalsWidget
  - MedicationList
  # From Dashboard:
  - DashboardGrid
  - KPICard
  - ChartWidget
  # Merged result:
  - PatientVitalsCard     # Smart combination!
  - HealthMetricsWidget
```

### Conflict Resolution

When both profiles define the same property:

1. **Color conflicts**: Industry always wins (brand identity)
2. **Layout conflicts**: Use case always wins (UX pattern)
3. **Component conflicts**: Combine with smart renaming
4. **Compliance conflicts**: Union (include all requirements)

---

## Tailwind Config Generation

BuildRunner auto-generates production-ready Tailwind configs:

### Generated Config Structure

```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      // Industry colors
      colors: {
        primary: {
          50: '#E6F0FF',
          100: '#CCE0FF',
          // ... shades generated
          500: '#0066CC',  // Base color
          // ... darker shades
          900: '#001A33',
        },
        secondary: { /* ... */ },
        accent: { /* ... */ },
      },

      // Typography from profile
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },

      // Spacing scale (dashboard grid system)
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
        '128': '32rem',
      },

      // Component-specific utilities
      borderRadius: {
        'card': '0.75rem',
        'widget': '0.5rem',
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),      // Form styling
    require('@tailwindcss/typography'), // Content styling
    require('@tailwindcss/aspect-ratio'), // Responsive media
  ],
}
```

### Color Shade Generation

BuildRunner generates 10 shades for each color:

```javascript
// Input: primary: "#0066CC"
// Output:
{
  50: '#E6F0FF',   // Lightest (90% lighter)
  100: '#CCE0FF',  // ...
  200: '#99C2FF',
  300: '#66A3FF',
  400: '#3385FF',
  500: '#0066CC',  // Base color (your input)
  600: '#0052A3',
  700: '#003D7A',
  800: '#002952',
  900: '#001429',  // Darkest (90% darker)
}
```

### Usage in Components

```jsx
// Auto-generated component with profile colors
<div className="bg-primary-500 text-white">
  <h1 className="font-sans text-2xl">Patient Dashboard</h1>
  <div className="bg-secondary-100 border-secondary-500 rounded-card">
    <VitalsWidget />
  </div>
</div>
```

---

## Compliance Requirements

BuildRunner documents compliance for each industry:

### Healthcare (HIPAA)

**Requirements:**
- ✅ End-to-end encryption for PHI
- ✅ Audit logging (who accessed what, when)
- ✅ Role-based access control (RBAC)
- ✅ Secure session management
- ✅ Data breach notification procedures

**Implementation Checklist:**
```markdown
- [ ] Encrypt all PHI data at rest (AES-256)
- [ ] Encrypt all PHI data in transit (TLS 1.3+)
- [ ] Log all access to patient records
- [ ] Implement timeout for inactive sessions (15 min)
- [ ] Provide audit trail exports
- [ ] Business Associate Agreements (BAAs) for vendors
```

### Fintech (PCI DSS)

**Requirements:**
- ✅ Never store full credit card numbers
- ✅ Tokenize payment data
- ✅ Security scanning and pen testing
- ✅ Access control and monitoring
- ✅ Incident response plan

**Implementation Checklist:**
```markdown
- [ ] Use Stripe/payment gateway for card processing
- [ ] Store only tokenized payment methods
- [ ] Implement fraud detection
- [ ] Security audit quarterly
- [ ] PCI DSS compliance attestation
```

### SaaS (SOC 2)

**Requirements:**
- ✅ Security controls documented
- ✅ Availability guarantees (SLAs)
- ✅ Data processing transparency
- ✅ Change management process
- ✅ Vendor risk management

---

## CLI Usage

### Preview Design Profile

```bash
# View specific industry + use case combination
br design profile healthcare dashboard

# Output:
┌─────────────────────────────────────────┐
│ Design Profile: Healthcare + Dashboard │
├─────────────────────────────────────────┤
│ Colors:                                 │
│   Primary: #0066CC (Trust Blue)        │
│   Secondary: #00A86B (Medical Green)   │
│                                          │
│ Compliance:                             │
│   • HIPAA                               │
│   • WCAG 2.1 AA                         │
│   • 21 CFR Part 11                      │
│                                          │
│ Components:                             │
│   • PatientVitalsCard                  │
│   • HealthMetricsWidget                │
│   • MedicationList                     │
│   • AppointmentScheduler               │
└─────────────────────────────────────────┘
```

### Research Design Patterns

```bash
# Extract best practices from existing apps
br design research healthcare

# Output:
📚 Design Research: Healthcare
─────────────────────────────
Analyzing 50+ healthcare apps...

Common Patterns Found:
  • Clinical white backgrounds (95%)
  • Trust blue primary color (87%)
  • Sidebar navigation (78%)
  • Card-based layouts (92%)
  • Red for alerts only (100%)

Compliance Checklist:
  ✓ HIPAA-compliant session timeout
  ✓ Audit logging UI patterns
  ✓ Role-based dashboards
  ✓ PHI masking in views
```

### Generate Tailwind Config

```bash
# Auto-generate from profile
br design tailwind healthcare dashboard

# Creates: tailwind.config.js
✅ Generated Tailwind config with:
   - Healthcare color palette
   - Dashboard grid system
   - Accessibility utilities
   - Component presets
```

---

## Examples

### Example 1: Healthcare Dashboard

```bash
br design profile healthcare dashboard
```

**Generated Design:**
- **Colors**: Trust blue (#0066CC), medical green (#00A86B)
- **Layout**: 3-column grid with sidebar
- **Components**: PatientVitalsCard, HealthMetricsWidget, MedicationList
- **Compliance**: HIPAA, WCAG 2.1 AA, 21 CFR Part 11
- **Security**: PHI encryption, audit logging, RBAC

**Perfect For:**
- Electronic Health Records (EHR)
- Patient portals
- Telemedicine platforms
- Clinical decision support

### Example 2: Fintech Marketplace

```bash
br design profile fintech marketplace
```

**Generated Design:**
- **Colors**: Professional navy (#1E3A8A), gold accent (#F59E0B)
- **Layout**: Product grid with advanced filters
- **Components**: InvestmentCard, PortfolioWidget, TransactionHistory
- **Compliance**: PCI DSS, SOC 2, GDPR
- **Security**: Tokenized payments, fraud detection, 2FA

**Perfect For:**
- Stock trading platforms
- Cryptocurrency exchanges
- P2P lending marketplaces
- Investment platforms

### Example 3: SaaS Analytics

```bash
br design profile saas analytics
```

**Generated Design:**
- **Colors**: Modern purple (#7C3AED), data viz palette
- **Layout**: Dashboard with drill-down charts
- **Components**: KPICard, InteractiveChart, DataTable, FilterPanel
- **Compliance**: SOC 2, GDPR, ISO 27001
- **Security**: API authentication, data encryption, export controls

**Perfect For:**
- Business intelligence tools
- Analytics platforms
- Reporting dashboards
- Data visualization apps

### Example 4: E-commerce Mobile App

```bash
br design profile ecommerce mobile_app
```

**Generated Design:**
- **Colors**: Vibrant brand colors with conversion-focused CTAs
- **Layout**: Mobile-first, touch-optimized, bottom navigation
- **Components**: ProductCard, CartWidget, CheckoutFlow, ReviewsSection
- **Compliance**: PCI DSS, GDPR, ADA
- **Security**: Secure checkout, tokenized payments

**Perfect For:**
- Mobile shopping apps
- Product catalogs
- Order management
- Customer loyalty programs

---

## Advanced Topics

### Custom Industry Profiles

Create your own industry profile:

```yaml
# templates/industries/custom.yaml
name: legal
display_name: Legal Services
description: "Law firms and legal tech platforms"

colors:
  primary: "#1C3D5A"    # Legal navy
  secondary: "#B8860B"  # Gold accent

compliance:
  - Attorney-Client Privilege
  - ABA Model Rules
  - GDPR (for EU clients)

components:
  - CaseCard
  - ClientPortal
  - DocumentManager
  - BillingWidget
```

### Profile Inheritance

Extend existing profiles:

```yaml
# Inherit from healthcare, customize
name: telemedicine
extends: healthcare
colors:
  accent: "#00C7B1"  # Override accent color
components:
  - VideoConsultation  # Add new component
  - SymptomChecker
```

### Tailwind Plugin Development

Extend with custom utilities:

```javascript
// plugins/healthcare-utils.js
module.exports = function({ addUtilities }) {
  addUtilities({
    '.phi-mask': {
      filter: 'blur(4px)',
      transition: 'filter 0.2s',
      '&:hover': { filter: 'none' }
    },
    '.audit-highlight': {
      boxShadow: '0 0 0 2px rgba(255,107,107,0.5)',
    },
  })
}
```

---

## Related Documentation

- **[Industry Profiles](INDUSTRY_PROFILES.md)** - Detailed industry documentation
- **[Use Case Patterns](USE_CASE_PATTERNS.md)** - Detailed use case documentation
- **[Design Research](DESIGN_RESEARCH.md)** - Pattern extraction and analysis
- **[PRD Wizard](PRD_WIZARD.md)** - Integration with PROJECT_SPEC
- **[Incremental Updates](INCREMENTAL_UPDATES.md)** - Design system evolution

---

## FAQ

**Q: Can I mix multiple industries?**
A: Not directly, but you can create a custom profile that extends multiple industries.

**Q: How do I update my design system after initial setup?**
A: See [INCREMENTAL_UPDATES.md](INCREMENTAL_UPDATES.md) for migration strategies.

**Q: Can I use this without Tailwind?**
A: Yes! The profiles generate design tokens that work with any CSS framework.

**Q: How accurate are the compliance requirements?**
A: BuildRunner provides guidance, but consult legal/compliance experts for production apps.

**Q: Can I contribute new industry profiles?**
A: Yes! See [CONTRIBUTING.md](../CONTRIBUTING.md) for submission guidelines.

---

**Next Steps:**
1. Browse [Industry Profiles](INDUSTRY_PROFILES.md) to see all 8 industries
2. Explore [Use Case Patterns](USE_CASE_PATTERNS.md) for UX patterns
3. Try `br design profile <industry> <use-case>` to preview combinations
4. Read [Design Research](DESIGN_RESEARCH.md) to understand pattern extraction

---

**BuildRunner Design System** - Because AI shouldn't guess at visual design 🎨
