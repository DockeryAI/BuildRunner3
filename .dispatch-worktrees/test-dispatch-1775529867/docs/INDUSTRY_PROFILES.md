# Industry Profiles - Complete Reference

**All 8 industry profiles with colors, compliance, security, and component libraries.**

---

## Table of Contents

- [Healthcare](#1-healthcare)
- [Fintech](#2-fintech)
- [E-commerce](#3-e-commerce)
- [SaaS](#4-saas)
- [Education](#5-education)
- [Social](#6-social)
- [Marketplace](#7-marketplace)
- [Analytics](#8-analytics)
- [Profile Structure](#profile-structure)
- [Customization Guide](#customization-guide)

---

## 1. Healthcare

**Medical applications, patient portals, telemedicine platforms**

### Design Specification

```yaml
name: healthcare
display_name: Healthcare & Medical
```

### Color Palette

| Color | Hex | Usage | Psychology |
|-------|-----|-------|------------|
| **Primary** | `#0066CC` | Trust Blue | Professionalism, reliability, calm |
| **Secondary** | `#00A86B` | Medical Green | Health, growth, vitality |
| **Accent** | `#FF6B6B` | Alert Red | Urgent alerts, critical values |
| **Neutral** | `#F5F5F5` | Clinical White | Cleanliness, simplicity, clarity |

**Rationale**: Blue conveys trust and professionalism (used by 87% of healthcare apps). Green represents health and vitality. Red is reserved exclusively for alerts to avoid alarm fatigue.

### Typography

```css
Heading: Inter (700) - Professional, highly legible
Body: Inter (400) - Excellent readability for medical text
Mono: JetBrains Mono - Clear code/data display
```

### Compliance & Regulations

#### HIPAA (Health Insurance Portability and Accountability Act)

**Privacy Rule Requirements:**
- ✅ Minimum necessary standard - only show needed PHI
- ✅ Patient access rights - export records on demand
- ✅ Accounting of disclosures - who accessed what

**Security Rule Requirements:**
- ✅ Administrative safeguards - policies and training
- ✅ Physical safeguards - device controls
- ✅ Technical safeguards - encryption, auth, audit

**Implementation Checklist:**
```markdown
- [ ] Encrypt all PHI data at rest (AES-256)
- [ ] Encrypt all PHI data in transit (TLS 1.3+)
- [ ] Implement automatic session timeout (15 min)
- [ ] Log all PHI access (who, what, when)
- [ ] Role-based access control (doctor, nurse, admin)
- [ ] Secure password policies (min 12 chars, MFA)
- [ ] Business Associate Agreements with vendors
- [ ] Annual security risk assessment
- [ ] Breach notification procedures documented
- [ ] Patient consent management
```

#### Additional Compliance

- **WCAG 2.1 AA**: Accessibility for disabled patients
- **ADA**: Americans with Disabilities Act compliance
- **21 CFR Part 11**: FDA electronic records (for clinical trials)
- **HL7 FHIR**: Interoperability standard for health data

### Security Requirements

```yaml
- end_to_end_encryption
- audit_logging
- role_based_access (RBAC)
- phi_protection
- secure_messaging
- session_management
- data_breach_response
```

### Component Library

**Clinical Components:**
- `PatientCard` - Patient demographics and summary
- `VitalsWidget` - Real-time vital signs display
- `MedicationList` - Current medications with interactions
- `AllergyBadge` - Prominent allergy warnings
- `LabResultsTable` - Test results with reference ranges

**Workflow Components:**
- `AppointmentScheduler` - Calendar booking system
- `ConsultationNotes` - SOAP note templates
- `PrescriptionWriter` - e-Prescribing interface
- `ImagingViewer` - X-ray/MRI image viewer
- `ConsentForm` - Digital consent signatures

**Administrative:**
- `InsuranceVerifier` - Insurance eligibility checks
- `BillingDashboard` - Claims and payments
- `AuditLog` - HIPAA compliance audit trail

### Design Patterns

```yaml
layout: clinical-minimal
  # Clean, distraction-free, focus on patient care
  # White space, clear hierarchy, minimal decoration

navigation: sidebar
  # Persistent access to patient sections
  # Easy switching between patients

data_entry: guided
  # Step-by-step forms with inline validation
  # Prevent errors in medical data entry

alerts: critical-prominent
  # Allergies and warnings always visible
  # Red only for truly urgent items
```

### Example Apps

- **Epic MyChart** - Patient portal (inspiration for layout)
- **Athenahealth** - EHR system (workflow patterns)
- **Teladoc** - Telemedicine (video consultation UI)
- **HealthKit** - Apple health app (data visualization)

---

## 2. Fintech

**Banking, payments, investment platforms, cryptocurrency**

### Design Specification

```yaml
name: fintech
display_name: Financial Technology
```

### Color Palette

| Color | Hex | Usage | Psychology |
|-------|-----|-------|------------|
| **Primary** | `#1E3A8A` | Professional Navy | Trust, stability, security |
| **Secondary** | `#10B981` | Success Green | Growth, profit, positive |
| **Accent** | `#F59E0B` | Gold | Premium, value, wealth |
| **Danger** | `#EF4444` | Alert Red | Loss, negative, warning |

**Rationale**: Navy blue conveys trust and professionalism (used by Chase, AmEx, Capital One). Green represents financial growth. Gold suggests premium value.

### Typography

```css
Heading: Manrope (700) - Modern, professional, geometric
Body: Inter (400) - Excellent number readability
Mono: IBM Plex Mono - Clear financial data display
```

### Compliance & Regulations

#### PCI DSS (Payment Card Industry Data Security Standard)

**12 Requirements:**
1. ✅ Install and maintain firewall configuration
2. ✅ Don't use vendor-supplied defaults
3. ✅ Protect stored cardholder data
4. ✅ Encrypt transmission of cardholder data
5. ✅ Protect systems against malware
6. ✅ Develop and maintain secure systems
7. ✅ Restrict access to cardholder data
8. ✅ Identify and authenticate access
9. ✅ Restrict physical access to cardholder data
10. ✅ Track and monitor network access
11. ✅ Regularly test security systems
12. ✅ Maintain information security policy

**Implementation Checklist:**
```markdown
- [ ] NEVER store full credit card numbers
- [ ] Use payment gateway (Stripe/Square) for card processing
- [ ] Store only tokenized payment methods
- [ ] Implement 2FA/MFA for all accounts
- [ ] Security scanning quarterly
- [ ] Penetration testing annually
- [ ] Fraud detection algorithms
- [ ] Real-time transaction monitoring
- [ ] Incident response plan documented
- [ ] PCI DSS compliance attestation (SAQ)
```

#### Additional Compliance

- **SOC 2 Type II**: Security and availability controls
- **GDPR**: European data protection (for EU customers)
- **KYC/AML**: Know Your Customer / Anti-Money Laundering
- **Dodd-Frank**: Financial reform regulations (US)
- **MiFID II**: Markets in Financial Instruments (EU)

### Security Requirements

```yaml
- tokenized_payments
- two_factor_authentication
- fraud_detection
- rate_limiting
- ip_whitelist
- transaction_monitoring
- encryption_at_rest
- secure_api_design
```

### Component Library

**Financial Display:**
- `BalanceCard` - Account balance with trends
- `TransactionList` - Transaction history with filters
- `InvestmentChart` - Portfolio performance graphs
- `CurrencyConverter` - Real-time exchange rates
- `StockTicker` - Live stock price updates

**Actions:**
- `TransferForm` - Money transfer interface
- `PaymentButton` - Secure payment submission
- `InvestmentTrader` - Buy/sell stocks
- `BudgetPlanner` - Budget creation tools
- `GoalTracker` - Savings goal progress

**Security:**
- `TwoFactorAuth` - 2FA code entry
- `BiometricPrompt` - Fingerprint/Face ID
- `SecuritySettings` - Security preferences
- `FraudAlert` - Suspicious activity warnings
- `TransactionApproval` - High-value confirmations

### Design Patterns

```yaml
layout: security-first
  # Clear trust indicators (locks, badges)
  # Explicit confirmation for financial actions
  # Real-time balance updates

navigation: bottom-tabs
  # Quick access to accounts, payments, cards
  # Always visible, thumb-friendly

data_entry: validated
  # Real-time validation of amounts
  # Clear error messages
  # Confirmation screens before submission

financial_data: precise
  # Always show currency symbols
  # 2 decimal precision
  # Color-coded positive/negative
```

### Example Apps

- **Stripe Dashboard** - Payment analytics (data viz inspiration)
- **Robinhood** - Stock trading (mobile-first design)
- **Revolut** - Digital banking (card management UI)
- **Coinbase** - Cryptocurrency (wallet interface)

---

## 3. E-commerce

**Online stores, retail platforms, shopping apps**

### Design Specification

```yaml
name: ecommerce
display_name: E-commerce & Retail
```

### Color Palette

| Color | Hex | Usage | Psychology |
|-------|-----|-------|------------|
| **Primary** | `#F97316` | Vibrant Orange | Energy, action, conversion |
| **Secondary** | `#8B5CF6` | Royal Purple | Premium, luxury, quality |
| **Success** | `#22C55E` | Fresh Green | In stock, available, success |
| **Sale** | `#DC2626` | Sale Red | Urgency, discounts, limited time |

**Rationale**: Orange encourages action and clicks (used by Amazon, Etsy). Purple conveys premium quality. Red creates urgency for sales.

### Typography

```css
Heading: Poppins (700) - Friendly, modern, approachable
Body: Inter (400) - Easy reading for descriptions
Price: Roboto (700) - Clear number display
```

### Compliance & Regulations

#### PCI DSS (for payments)
- ✅ Tokenized checkout flow
- ✅ No card storage on servers
- ✅ Secure payment gateway integration

#### GDPR (EU customers)
- ✅ Cookie consent banners
- ✅ Data export on request
- ✅ Right to be forgotten
- ✅ Privacy policy transparency

#### Consumer Protection
- ✅ Clear refund/return policies
- ✅ Honest product descriptions
- ✅ Accurate shipping estimates
- ✅ Price transparency (no hidden fees)

**Implementation Checklist:**
```markdown
- [ ] SSL certificate for entire site
- [ ] PCI-compliant checkout (use Stripe/PayPal)
- [ ] GDPR cookie consent
- [ ] Accessibility (WCAG 2.1 AA)
- [ ] Mobile-responsive design
- [ ] Page load under 3 seconds
- [ ] SEO optimization
- [ ] Product schema markup
- [ ] Analytics tracking (privacy-compliant)
```

### Component Library

**Product Display:**
- `ProductCard` - Product image, price, rating
- `ProductGallery` - Image carousel with zoom
- `PriceTag` - Price with discounts/sale badges
- `RatingStars` - Customer rating display
- `StockBadge` - In stock / low stock / sold out

**Shopping Experience:**
- `AddToCartButton` - Prominent CTA
- `CartWidget` - Mini cart with item count
- `CheckoutFlow` - Multi-step checkout
- `ShippingCalculator` - Real-time shipping costs
- `PromoCodeInput` - Discount code entry

**Discovery:**
- `CategoryNav` - Product category navigation
- `SearchBar` - Product search with suggestions
- `FilterPanel` - Price, brand, rating filters
- `SortDropdown` - Sort by price/rating/date
- `RecommendationCarousel` - "You might also like"

**Social Proof:**
- `ReviewSection` - Customer reviews and photos
- `TrustBadges` - Security and guarantee badges
- `RecentPurchases` - "X people bought this"
- `LiveInventory` - "Only 3 left in stock!"

### Design Patterns

```yaml
layout: conversion-optimized
  # Large product images (3:4 aspect ratio)
  # Clear CTAs above the fold
  # Sticky add-to-cart button on mobile

navigation: mega-menu
  # Category mega menu on hover
  # Search prominent in header
  # Cart always visible

checkout: streamlined
  # Guest checkout option
  # Progress indicator
  # Address autocomplete
  # One-click payment (Apple Pay, Google Pay)

mobile: thumb-friendly
  # Bottom navigation for cart/search
  # Large touch targets
  # Swipeable product images
```

### Example Apps

- **Amazon** - Product listings (best practices)
- **Shopify stores** - Checkout flow
- **ASOS** - Mobile app (filter/sort UI)
- **Etsy** - Social proof and reviews

---

## 4. SaaS

**B2B software, productivity tools, cloud platforms**

### Design Specification

```yaml
name: saas
display_name: SaaS & B2B Software
```

### Color Palette

| Color | Hex | Usage | Psychology |
|-------|-----|-------|------------|
| **Primary** | `#7C3AED` | Modern Purple | Innovation, creativity, tech |
| **Secondary** | `#3B82F6` | Bright Blue | Productivity, trust, clarity |
| **Success** | `#10B981` | Success Green | Completion, success, growth |
| **Warning** | `#F59E0B` | Attention Orange | Warnings, upgrades, upsells |

**Rationale**: Purple suggests modern innovation (used by Stripe, Notion, Twilio). Blue conveys productivity and professionalism.

### Typography

```css
Heading: Cal Sans (700) - Modern, distinctive, brand
Body: Inter (400) - Excellent UI readability
Code: Fira Code (400) - Developer-friendly code blocks
```

### Compliance & Regulations

#### SOC 2 Type II
**Trust Service Criteria:**
- **Security**: Protection against unauthorized access
- **Availability**: System availability for operation and use
- **Processing Integrity**: Complete, valid, accurate processing
- **Confidentiality**: Protected as committed or agreed
- **Privacy**: Personal information collection, use, disclosure

**Implementation Checklist:**
```markdown
- [ ] Annual SOC 2 Type II audit
- [ ] Security policies documented
- [ ] Incident response plan
- [ ] Business continuity plan
- [ ] Vendor risk management
- [ ] Access control procedures
- [ ] Change management process
- [ ] Monitoring and logging
- [ ] Encryption at rest and in transit
- [ ] Penetration testing annually
```

#### Additional Compliance
- **ISO 27001**: Information security management
- **GDPR**: EU data protection
- **CCPA**: California privacy law
- **HIPAA**: If handling health data
- **FedRAMP**: If selling to US government

### Component Library

**Dashboard:**
- `DashboardGrid` - Responsive widget grid
- `KPICard` - Key metric display
- `UsageChart` - Usage analytics
- `TeamActivityFeed` - Recent team actions
- `QuickActions` - Common task shortcuts

**Collaboration:**
- `CommentThread` - Inline comments
- `MentionAutocomplete` - @mention users
- `NotificationCenter` - Activity notifications
- `ShareDialog` - Sharing and permissions
- `VersionHistory` - Document versions

**Settings:**
- `SettingsNav` - Settings sidebar
- `BillingSection` - Subscription management
- `TeamManagement` - User roles and invites
- `IntegrationsList` - Third-party integrations
- `APIKeyManager` - Developer API keys

### Design Patterns

```yaml
layout: sidebar-app
  # Persistent sidebar navigation
  # Content area with toolbar
  # Right panel for details/settings

navigation: hierarchical
  # Workspaces → Projects → Documents
  # Breadcrumbs for navigation
  # Quick switcher (Cmd+K)

onboarding: progressive
  # Empty states with CTAs
  # Onboarding checklists
  # Contextual tips
  # Product tours

collaboration: real-time
  # Live cursors (multiplayer)
  # Presence indicators
  # Real-time updates
  # Optimistic UI
```

### Example Apps

- **Notion** - Workspace design (sidebar, pages)
- **Slack** - Real-time collaboration
- **Figma** - Multiplayer cursors
- **Linear** - Keyboard-first navigation

---

## 5. Education

**Learning platforms, course management, EdTech**

### Design Specification

```yaml
name: education
display_name: Education & Learning
```

### Color Palette

| Color | Hex | Usage | Psychology |
|-------|-----|-------|------------|
| **Primary** | `#6366F1` | Learning Indigo | Focus, knowledge, calm |
| **Secondary** | `#EC4899` | Energetic Pink | Engagement, excitement, fun |
| **Success** | `#10B981` | Achievement Green | Progress, completion, success |
| **Info** | `#3B82F6` | Information Blue | Learning, resources, help |

### Compliance

- **FERPA**: Student privacy protection
- **COPPA**: Children's online privacy (under 13)
- **WCAG 2.1 AA**: Accessibility for disabled students
- **Section 508**: Accessibility for federal education

### Component Library

- `CourseCard` - Course preview and enrollment
- `LessonPlayer` - Video/content player
- `ProgressTracker` - Course completion progress
- `QuizInterface` - Interactive assessments
- `DiscussionBoard` - Student discussions
- `GradeBook` - Grade tracking
- `CertificateBadge` - Completion certificates

---

## 6. Social

**Social networks, community platforms, messaging**

### Design Specification

```yaml
name: social
display_name: Social & Community
```

### Color Palette

| Color | Hex | Usage | Psychology |
|-------|-----|-------|------------|
| **Primary** | `#0EA5E9` | Social Blue | Connection, communication, calm |
| **Secondary** | `#F43F5E` | Love Red | Likes, hearts, passion |
| **Accent** | `#8B5CF6` | Creative Purple | Stories, creativity, expression |
| **Online** | `#10B981` | Online Green | Active, available, online |

### Compliance

- **GDPR**: User data and consent
- **CCPA**: California privacy
- **COPPA**: Child protection (if under 13)
- **Content moderation**: Hate speech, harassment policies
- **DMCA**: Copyright takedown procedures

### Component Library

- `FeedPost` - Social media post card
- `StoryCarousel` - Instagram-style stories
- `CommentSection` - Nested comments
- `ReactionButtons` - Like, love, share
- `ChatInterface` - Real-time messaging
- `UserProfile` - Profile pages
- `FollowButton` - Follow/unfollow actions
- `NotificationBell` - Activity notifications

---

## 7. Marketplace

**Multi-vendor platforms, gig economy, listings**

### Design Specification

```yaml
name: marketplace
display_name: Marketplace & Platforms
```

### Color Palette

| Color | Hex | Usage | Psychology |
|-------|-----|-------|------------|
| **Primary** | `#7C3AED` | Platform Purple | Innovation, variety, choice |
| **Secondary** | `#EC4899` | Action Pink | CTAs, engagement, urgency |
| **Trust** | `#3B82F6` | Trust Blue | Verified sellers, secure payments |
| **Earnings** | `#10B981` | Money Green | Earnings, payouts, success |

### Compliance

- **PCI DSS**: Payment processing
- **Escrow requirements**: Buyer/seller protection
- **KYC/AML**: Seller verification
- **Consumer protection**: Refund/dispute policies
- **Tax reporting**: 1099 forms (US)

### Component Library

- `ListingCard` - Product/service listings
- `SellerProfile` - Seller ratings and reviews
- `BookingCalendar` - Appointment booking
- `MessageCenter` - Buyer-seller chat
- `PayoutDashboard` - Seller earnings
- `DisputeCenter` - Dispute resolution
- `VerificationBadge` - Verified seller badges

---

## 8. Analytics

**Business intelligence, dashboards, data visualization**

### Design Specification

```yaml
name: analytics
display_name: Analytics & BI
```

### Color Palette

| Color | Hex | Usage | Psychology |
|-------|-----|-------|------------|
| **Primary** | `#6366F1` | Data Indigo | Analysis, intelligence, insight |
| **Charts** | Multi-hue | Data visualization | Categorical distinction |
| **Positive** | `#10B981` | Positive trend | Growth, increase, success |
| **Negative** | `#EF4444` | Negative trend | Decline, decrease, warning |

### Compliance

- **GDPR**: Data processing transparency
- **SOC 2**: Data security controls
- **Data retention**: Policies for data deletion
- **Anonymization**: PII protection

### Component Library

- `KPICard` - Single metric display
- `LineChart` - Trends over time
- `BarChart` - Comparisons
- `PieChart` - Proportions
- `Heatmap` - Pattern visualization
- `DataTable` - Sortable, filterable tables
- `FilterPanel` - Date range, segments
- `ExportButton` - CSV/PDF export
- `ReportBuilder` - Custom report creation

---

## Profile Structure

Each industry profile follows this structure:

```yaml
# Identity
name: string                  # snake_case identifier
display_name: string          # Human-readable name
description: string           # Purpose and use cases

# Visual Design
colors:
  primary: hex                # Main brand color
  secondary: hex              # Supporting color
  accent: hex                 # Call-to-action color
  neutral: hex                # Background/neutral

typography:
  heading_font: string        # Display font
  body_font: string           # Text font
  mono_font: string           # Code/data font

# Compliance
compliance: array             # Regulatory requirements
security: array               # Security requirements

# UI Components
components: array             # Component library
patterns: object              # Design patterns
```

---

## Customization Guide

### Overriding Colors

```yaml
# In your project's .buildrunner/config.yaml
design:
  industry: healthcare
  overrides:
    colors:
      primary: "#0052A3"  # Custom brand blue
```

### Adding Custom Components

```yaml
design:
  industry: fintech
  custom_components:
    - CryptoWallet
    - NFTGallery
    - StakingRewards
```

### Mixing Profiles

```yaml
design:
  base_industry: healthcare
  additional_compliance:
    - fintech.pci_dss       # Add payment compliance
    - saas.soc2             # Add SOC 2 requirements
```

---

## Related Documentation

- **[Design System](DESIGN_SYSTEM.md)** - Overview and merging algorithm
- **[Use Case Patterns](USE_CASE_PATTERNS.md)** - UX patterns for app types
- **[PRD Wizard](PRD_WIZARD.md)** - Integration with PROJECT_SPEC

---

**Industry Profiles** - Domain expertise built into your design system 🏗️
