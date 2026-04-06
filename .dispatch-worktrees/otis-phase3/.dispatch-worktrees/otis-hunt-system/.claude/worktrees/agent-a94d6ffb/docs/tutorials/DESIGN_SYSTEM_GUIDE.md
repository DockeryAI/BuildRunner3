# Design System Guide

Learn to leverage BuildRunner's industry-specific design profiles and use case patterns to create consistent, professional UIs quickly.

## Table of Contents

- [Introduction](#introduction)
- [Industry Profiles Overview](#industry-profiles-overview)
- [Use Case Patterns](#use-case-patterns)
- [Getting Started](#getting-started)
- [Selecting Industry Profiles](#selecting-industry-profiles)
- [Merging Multiple Profiles](#merging-multiple-profiles)
- [Generating Tailwind Configs](#generating-tailwind-configs)
- [Customizing Merged Profiles](#customizing-merged-profiles)
- [Real-World Example: Healthcare Dashboard](#real-world-example-healthcare-dashboard)
- [Real-World Example: Fintech API](#real-world-example-fintech-api)
- [Real-World Example: E-commerce + SaaS](#real-world-example-e-commerce--saas)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

## Introduction

BuildRunner 3.0 includes pre-built design systems for common industries and use cases. Instead of starting from scratch, you can:

- **Select industry profiles** (Healthcare, Fintech, E-commerce, etc.)
- **Choose use case patterns** (Dashboard, API, Forms, etc.)
- **Merge multiple profiles** for hybrid applications
- **Generate Tailwind configs** ready to use
- **Customize colors, spacing, typography** to match your brand

This approach saves hours of design system setup while maintaining professional standards.

## Industry Profiles Overview

BuildRunner includes these industry profiles:

### Healthcare
- **Colors:** Calming blues, medical whites, health greens
- **Typography:** Accessible, clear sans-serif fonts
- **Spacing:** Generous whitespace for readability
- **Patterns:** HIPAA-compliant forms, patient dashboards, medical charts
- **Accessibility:** WCAG AAA compliance built-in

### Fintech
- **Colors:** Trust-building blues, professional grays, alert reds/greens
- **Typography:** Modern, professional fonts
- **Spacing:** Dense information displays
- **Patterns:** Transaction tables, account dashboards, payment forms
- **Security:** Visual indicators for secure areas

### E-commerce
- **Colors:** Vibrant, conversion-optimized palette
- **Typography:** Product-focused, clear CTAs
- **Spacing:** Product grid layouts
- **Patterns:** Product cards, checkout flows, shopping carts
- **Conversion:** Tested CTA styles and layouts

### SaaS
- **Colors:** Modern, tech-forward palette
- **Typography:** Clean, minimal fonts
- **Spacing:** Efficient use of screen space
- **Patterns:** Onboarding flows, usage dashboards, settings panels
- **Engagement:** User activation patterns

### Education
- **Colors:** Engaging, focus-friendly colors
- **Typography:** Readable, student-friendly fonts
- **Spacing:** Clear content hierarchy
- **Patterns:** Course layouts, progress trackers, quiz interfaces
- **Accessibility:** Student-centered design

## Use Case Patterns

Each profile includes patterns for common use cases:

### Dashboard
- Multi-column layouts
- Widget/card systems
- Charts and graphs
- Real-time updates
- Navigation patterns

### API Documentation
- Code highlighting
- Request/response examples
- Interactive testing
- Endpoint organization
- Authentication flows

### Forms
- Field validation
- Multi-step wizards
- File uploads
- Auto-save
- Error handling

### Tables
- Sorting and filtering
- Pagination
- Bulk actions
- Responsive layouts
- Export functionality

### Marketing
- Landing pages
- Feature showcases
- Pricing tables
- Testimonials
- Call-to-actions

## Getting Started

### Prerequisites

```bash
# Ensure BuildRunner is installed
br --version

# Ensure you have a project initialized
br init  # If not already done
```

### View Available Profiles

```bash
# List all industry profiles
br design profiles list

# Output:
# Available Industry Profiles:
#   healthcare    - Healthcare and medical applications
#   fintech       - Financial services and banking
#   ecommerce     - E-commerce and retail
#   saas          - SaaS and B2B applications
#   education     - Educational platforms
```

### View Profile Details

```bash
# See what's in a specific profile
br design profiles show healthcare

# Output shows:
# - Color palette
# - Typography scale
# - Spacing system
# - Component patterns
# - Example usage
```

## Selecting Industry Profiles

### Single Profile Setup

For a pure healthcare application:

```bash
# Apply healthcare profile to project
br design apply healthcare

# What this does:
# 1. Creates design/profile.json with healthcare settings
# 2. Generates tailwind.config.js
# 3. Creates design/tokens.css with CSS variables
# 4. Adds component examples to design/examples/
```

**Generated Files:**

`design/profile.json`:
```json
{
  "industry": "healthcare",
  "version": "3.0.0",
  "colors": {
    "primary": {
      "50": "#e3f2fd",
      "100": "#bbdefb",
      "500": "#2196f3",
      "900": "#0d47a1"
    },
    "success": {
      "500": "#4caf50"
    },
    "error": {
      "500": "#f44336"
    }
  },
  "typography": {
    "fontFamily": {
      "sans": ["Inter", "system-ui", "sans-serif"],
      "mono": ["JetBrains Mono", "monospace"]
    },
    "fontSize": {
      "xs": "0.75rem",
      "sm": "0.875rem",
      "base": "1rem",
      "lg": "1.125rem",
      "xl": "1.25rem"
    }
  },
  "spacing": {
    "unit": "0.25rem",
    "scale": [0, 1, 2, 4, 6, 8, 12, 16, 24, 32]
  }
}
```

`tailwind.config.js`:
```javascript
module.exports = {
  content: ['./src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#e3f2fd',
          100: '#bbdefb',
          500: '#2196f3',
          900: '#0d47a1',
        },
        // ... more colors
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
```

### Preview Profile

```bash
# Generate preview HTML
br design preview healthcare

# Opens preview.html in browser showing:
# - Color palette swatches
# - Typography samples
# - Spacing examples
# - Component previews
```

## Merging Multiple Profiles

For hybrid applications (e.g., Healthcare + Dashboard):

### Step 1: Identify Needed Profiles

```bash
# You're building a healthcare patient portal with:
# - Medical data (Healthcare profile)
# - Analytics dashboard (Dashboard pattern)
```

### Step 2: Merge Profiles

```bash
# Merge healthcare industry with dashboard pattern
br design merge healthcare dashboard

# Or use shorthand:
br design apply healthcare+dashboard
```

### Step 3: Review Merged Config

BuildRunner intelligently merges profiles:

**Priority Rules:**
1. Industry-specific colors preserved
2. Pattern-specific layouts added
3. Conflicts resolved with prompts

Example merge result:

```json
{
  "sources": ["healthcare", "dashboard"],
  "merged_at": "2024-01-15T10:30:00Z",
  "colors": {
    "primary": {
      "500": "#2196f3"  // From healthcare
    }
  },
  "layouts": {
    "dashboard": {
      "sidebar": "280px",
      "header": "64px",
      "columns": 12
    }
  }
}
```

### Step 4: Resolve Conflicts

If profiles conflict:

```bash
# Interactive conflict resolution
br design merge healthcare fintech

# Prompts:
# "Both profiles define 'primary.500' color:"
#   Healthcare: #2196f3 (Calming Blue)
#   Fintech:    #1565c0 (Trust Blue)
# Choose [h]ealthcare, [f]intech, or [c]ustom: h
```

## Generating Tailwind Configs

### Basic Generation

```bash
# Generate Tailwind config from current profile
br design generate tailwind

# Creates tailwind.config.js
```

### With Plugins

```bash
# Generate with common plugins
br design generate tailwind --plugins forms,typography,aspect-ratio

# Installs and configures:
# - @tailwindcss/forms
# - @tailwindcss/typography
# - @tailwindcss/aspect-ratio
```

### Custom Purge Paths

```bash
# Specify content paths
br design generate tailwind --content "src/**/*.tsx,app/**/*.tsx"

# Result in tailwind.config.js:
# content: ['src/**/*.tsx', 'app/**/*.tsx']
```

### Multiple Output Formats

```bash
# Generate for different frameworks

# React/Next.js
br design generate tailwind --framework react

# Vue.js
br design generate tailwind --framework vue

# Svelte
br design generate tailwind --framework svelte
```

## Customizing Merged Profiles

### Override Colors

```bash
# Edit design/profile.json
{
  "industry": "healthcare",
  "customizations": {
    "colors": {
      "primary": {
        "500": "#1976d2"  // Your brand blue
      },
      "brand": {
        "500": "#ff6b00"  // Custom brand color
      }
    }
  }
}

# Regenerate config
br design generate tailwind
```

### Add Custom Fonts

```bash
# Update typography
{
  "customizations": {
    "typography": {
      "fontFamily": {
        "sans": ["Your Custom Font", "Inter", "sans-serif"]
      }
    }
  }
}
```

### Modify Spacing

```bash
# Adjust spacing scale
{
  "customizations": {
    "spacing": {
      "custom-tight": "0.125rem",
      "custom-loose": "3rem"
    }
  }
}
```

### Extend Components

Add custom component patterns:

```bash
# design/components/custom-card.json
{
  "name": "custom-card",
  "base": "healthcare-card",
  "overrides": {
    "borderRadius": "1rem",
    "padding": "2rem",
    "shadow": "xl"
  }
}

# Generate component CSS
br design generate component custom-card
```

## Real-World Example: Healthcare Dashboard

Building a patient portal with:
- Patient data dashboard
- Appointment scheduling
- Medical records access
- HIPAA compliance

### Step 1: Initialize with Profile

```bash
# Create project
mkdir patient-portal
cd patient-portal
br init

# Apply healthcare + dashboard profiles
br design apply healthcare+dashboard
```

### Step 2: Customize Colors

```bash
# Edit design/profile.json
{
  "sources": ["healthcare", "dashboard"],
  "customizations": {
    "colors": {
      "primary": "#0066cc",  // Hospital brand blue
      "accent": "#00a86b",   // Health green
      "alert": "#dc3545"     // Medical alert red
    }
  }
}

# Regenerate
br design generate tailwind
```

### Step 3: Use Generated Components

Create `src/components/PatientCard.tsx`:

```tsx
// Uses healthcare profile's card pattern
export function PatientCard({ patient }) {
  return (
    <div className="healthcare-card p-6 rounded-lg shadow-md">
      <div className="flex items-center gap-4">
        <div className="healthcare-avatar">
          {patient.initials}
        </div>
        <div>
          <h3 className="text-lg font-semibold text-primary-900">
            {patient.name}
          </h3>
          <p className="text-sm text-gray-600">
            MRN: {patient.mrn}
          </p>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-4">
        <div>
          <span className="text-xs text-gray-500">Last Visit</span>
          <p className="text-sm font-medium">{patient.lastVisit}</p>
        </div>
        <div>
          <span className="text-xs text-gray-500">Next Appointment</span>
          <p className="text-sm font-medium">{patient.nextAppt}</p>
        </div>
      </div>
    </div>
  );
}
```

### Step 4: Build Dashboard Layout

```tsx
// src/layouts/DashboardLayout.tsx
export function DashboardLayout({ children }) {
  return (
    <div className="dashboard-layout">
      {/* Uses dashboard profile's layout pattern */}
      <aside className="dashboard-sidebar">
        <nav>{/* Navigation */}</nav>
      </aside>

      <div className="dashboard-main">
        <header className="dashboard-header">
          {/* Header */}
        </header>

        <main className="dashboard-content">
          {children}
        </main>
      </div>
    </div>
  );
}
```

### Result

Professional healthcare dashboard with:
- ✅ WCAG AAA accessible colors
- ✅ Healthcare-appropriate typography
- ✅ Dashboard layout patterns
- ✅ Consistent component styling
- ✅ HIPAA-compliant UI patterns

## Real-World Example: Fintech API

Building a financial API platform with:
- Developer documentation
- API explorer
- Transaction history
- Analytics dashboard

### Step 1: Merge Profiles

```bash
# Fintech industry + API documentation pattern
br design apply fintech+api
```

### Step 2: Customize for Brand

```bash
# design/profile.json
{
  "sources": ["fintech", "api"],
  "customizations": {
    "colors": {
      "trust": "#1565c0",      // Finance blue
      "success": "#2e7d32",     // Money green
      "danger": "#c62828",      // Alert red
      "code": "#263238"         // Code bg
    },
    "typography": {
      "fontFamily": {
        "mono": ["Fira Code", "monospace"]  // For code blocks
      }
    }
  }
}
```

### Step 3: Use API Documentation Pattern

```tsx
// src/components/ApiEndpoint.tsx
export function ApiEndpoint({ endpoint }) {
  return (
    <div className="api-endpoint-card">
      {/* Uses fintech colors + API pattern layout */}
      <div className="api-method-badge method-post">
        POST
      </div>

      <code className="api-path text-code">
        /api/v1/transactions
      </code>

      <div className="api-description">
        Create a new transaction
      </div>

      <div className="api-code-block">
        <pre className="language-json">
{`{
  "amount": 150.00,
  "currency": "USD",
  "recipient": "acct_123"
}`}
        </pre>
      </div>
    </div>
  );
}
```

### Step 4: Build Transaction Table

```tsx
// Uses fintech table pattern with money-specific formatting
export function TransactionTable({ transactions }) {
  return (
    <table className="fintech-table">
      <thead>
        <tr>
          <th>Date</th>
          <th>Description</th>
          <th className="text-right">Amount</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {transactions.map(tx => (
          <tr key={tx.id}>
            <td>{tx.date}</td>
            <td>{tx.description}</td>
            <td className={`text-right font-mono ${
              tx.amount > 0 ? 'text-success' : 'text-danger'
            }`}>
              {formatCurrency(tx.amount)}
            </td>
            <td>
              <span className={`badge badge-${tx.status}`}>
                {tx.status}
              </span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

### Result

Professional fintech platform with:
- ✅ Trust-building colors
- ✅ Developer-friendly code blocks
- ✅ Financial data formatting
- ✅ Security visual indicators
- ✅ API documentation patterns

## Real-World Example: E-commerce + SaaS

Building a marketplace platform with:
- Product listings
- Seller dashboards
- Analytics
- SaaS onboarding

### Step 1: Merge Multiple Profiles

```bash
# Combine three profiles
br design merge ecommerce saas dashboard

# Or shorthand:
br design apply ecommerce+saas+dashboard
```

### Step 2: Resolve Conflicts

```bash
# BuildRunner prompts for conflict resolution:
# "primary.500" defined in multiple profiles:
#   E-commerce: #ff6b00 (Orange - High conversion)
#   SaaS:       #6366f1 (Indigo - Tech-forward)
# Choose [e]commerce, [s]aas, or split by context: split

# Define contexts:
# - Marketing pages: E-commerce colors
# - Admin dashboard: SaaS colors
```

### Step 3: Context-Based Theming

```bash
# design/profile.json
{
  "sources": ["ecommerce", "saas", "dashboard"],
  "contexts": {
    "marketing": {
      "primary": "#ff6b00",
      "accent": "#f59e0b"
    },
    "dashboard": {
      "primary": "#6366f1",
      "accent": "#8b5cf6"
    }
  }
}

# Generate context-aware configs
br design generate tailwind --contexts
```

### Step 4: Build Components

Product card (marketing context):

```tsx
export function ProductCard({ product }) {
  return (
    <div className="context-marketing">
      <div className="product-card">
        <img src={product.image} className="product-image" />
        <h3 className="text-lg font-bold text-primary-600">
          {product.name}
        </h3>
        <p className="text-2xl font-bold text-primary-500">
          ${product.price}
        </p>
        <button className="btn-primary">
          Add to Cart
        </button>
      </div>
    </div>
  );
}
```

Seller dashboard (dashboard context):

```tsx
export function SellerDashboard({ stats }) {
  return (
    <div className="context-dashboard">
      <div className="dashboard-layout">
        <div className="stats-grid">
          <StatCard
            title="Revenue"
            value={`$${stats.revenue}`}
            trend={stats.revenueTrend}
            className="stat-card"
          />
          {/* More stats */}
        </div>
      </div>
    </div>
  );
}
```

### Result

Cohesive multi-profile platform with:
- ✅ Conversion-optimized product pages
- ✅ Professional seller dashboards
- ✅ SaaS-style onboarding
- ✅ Context-aware theming
- ✅ Consistent design language

## Best Practices

### 1. Start with Industry Profile

Choose the profile closest to your domain:
```bash
# Don't start from scratch
❌ br design generate tailwind

# Start with relevant profile
✅ br design apply healthcare
```

### 2. Merge Sparingly

Only merge what you need:
```bash
# Too many profiles = inconsistent
❌ br design apply healthcare+fintech+ecommerce+saas

# Focused merge
✅ br design apply healthcare+dashboard
```

### 3. Customize After Merging

Follow this order:
1. Apply industry profile
2. Merge use case patterns
3. Customize colors/fonts
4. Generate final config

```bash
br design apply healthcare
br design merge dashboard
# Edit design/profile.json for customizations
br design generate tailwind
```

### 4. Version Control Your Profile

```bash
# Commit design system config
git add design/profile.json tailwind.config.js
git commit -m "feat: configure healthcare design system"
```

### 5. Document Customizations

```bash
# design/README.md
# Design System

Based on Healthcare profile with Dashboard patterns.

## Customizations
- Primary color: #0066cc (Hospital brand blue)
- Custom spacing: Added tight spacing for tables
- Font: Using hospital's brand font "CustomSans"

## Usage
See design/examples/ for component examples.
```

### 6. Test Accessibility

```bash
# Generate with accessibility testing
br design generate tailwind --with-a11y-tests

# Validates:
# - Color contrast ratios
# - Focus indicators
# - Touch target sizes
```

## Troubleshooting

### Issue: "Profile not found"

**Cause:** Typo in profile name

**Solution:**
```bash
# List available profiles
br design profiles list

# Use exact name
br design apply healthcare  # Not "health-care"
```

### Issue: Merged config has wrong colors

**Cause:** Merge order matters

**Solution:**
```bash
# Last profile wins for conflicts
br design merge healthcare fintech  # Fintech colors used

# Reverse order:
br design merge fintech healthcare  # Healthcare colors used

# Or be explicit:
br design merge healthcare fintech --prefer healthcare
```

### Issue: Generated Tailwind config not working

**Cause:** Content paths incorrect

**Solution:**
```bash
# Check content paths in tailwind.config.js
module.exports = {
  content: [
    './src/**/*.{js,jsx,ts,tsx}',  // Adjust to your structure
  ],
}

# Regenerate with correct paths:
br design generate tailwind --content "app/**/*.tsx"
```

### Issue: Custom colors not appearing

**Cause:** Forgot to regenerate config

**Solution:**
```bash
# After editing design/profile.json:
br design generate tailwind  # Must regenerate
```

### Issue: Conflicts during merge

**Cause:** Multiple profiles define same token

**Solution:**
```bash
# Use interactive conflict resolution:
br design merge healthcare fintech  # Follow prompts

# Or skip conflicts:
br design merge healthcare fintech --strategy prefer-first
```

## Summary

You've learned:

✅ How industry profiles save setup time
✅ How to select appropriate profiles
✅ How to merge multiple profiles
✅ How to generate Tailwind configs
✅ How to customize merged profiles
✅ Real-world examples for Healthcare, Fintech, E-commerce + SaaS
✅ Best practices for design systems
✅ Troubleshooting common issues

## Next Steps

- Explore [QUALITY_GATES.md](QUALITY_GATES.md) - Enforce design consistency
- Read [PARALLEL_BUILDS.md](PARALLEL_BUILDS.md) - Work on multiple features
- See [examples/](../../examples/) - Full example projects

Start building beautiful, consistent UIs with BuildRunner's design system!
