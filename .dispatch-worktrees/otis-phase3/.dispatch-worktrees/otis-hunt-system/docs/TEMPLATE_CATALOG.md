# Template Catalog

BuildRunner 3.0 includes pre-built templates for common industries and use cases.

## Industry Profiles (8)

### 1. Healthcare (`templates/industries/healthcare.yaml`)
- **Colors**: Trust blue, Medical green
- **Components**: PatientCard, VitalsWidget, MedicationList
- **Compliance**: HIPAA, WCAG 2.1 AA, ADA
- **Trust Signals**: Compliance badges, encryption indicators

### 2. Fintech (`templates/industries/fintech.yaml`)
- **Colors**: Finance navy, Success green
- **Components**: TransactionCard, BalanceWidget, SecureForm
- **Compliance**: PCI DSS, SOC 2, GDPR
- **Trust Signals**: Bank-grade security, 256-bit encryption

### 3. E-commerce (`templates/industries/ecommerce.yaml`)
- **Colors**: Conversion orange, Trust blue
- **Components**: ProductCard, CartWidget, ReviewCard
- **Compliance**: PCI DSS, GDPR, Accessibility
- **Trust Signals**: Secure checkout, verified reviews

### 4. SaaS (`templates/industries/saas.yaml`)
- **Colors**: Modern purple, Growth green
- **Components**: FeatureCard, PricingTable, DashboardWidget
- **Compliance**: SOC 2, GDPR, ISO 27001
- **Trust Signals**: Uptime guarantees, data privacy

### 5-8. Education, Social, Marketplace, Analytics
See `templates/industries/` for complete profiles.

## Use Case Patterns (8)

### 1. Dashboard (`templates/use_cases/dashboard.yaml`)
- **Layout**: Sidebar + widget grid
- **Components**: StatCard, LineChart, DataTable
- **Data Viz**: Time series, KPIs, tables

### 2. Marketplace (`templates/use_cases/marketplace.yaml`)
- **Layout**: Filter sidebar + product grid
- **Components**: ListingCard, SearchBar, FilterPanel
- **Features**: Search, filters, transactions

### 3-8. CRM, Analytics, Onboarding, API Service, Admin Panel, Mobile App
See `templates/use_cases/` for complete patterns.

## Profile Merging

When you select `Healthcare` + `Dashboard`:
- **Industry** provides: Colors, compliance, trust signals
- **Use case** provides: Layout, navigation, data viz patterns
- **Components**: Union of both sets
- **Result**: Complete design system with Healthcare compliance and Dashboard layout

## Tech Stack Templates (5)

1. **react-fastapi-postgres** - Modern full-stack
2. **mern** - MongoDB, Express, React, Node
3. **django-postgres** - Django monolith
4. **nextjs-supabase** - Serverless JAMstack
5. **vue-flask-mysql** - Alternative stack

See `templates/tech_stacks/` for complete configurations.
