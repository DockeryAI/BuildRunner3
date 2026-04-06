# Use Case Patterns - Complete Reference

**All 8 use case patterns with layouts, components, and UX best practices.**

---

## Table of Contents

- [Dashboard](#1-dashboard)
- [Marketplace](#2-marketplace)
- [CRM](#3-crm)
- [Analytics](#4-analytics)
- [Onboarding](#5-onboarding)
- [API Service](#6-api-service)
- [Admin Panel](#7-admin-panel)
- [Mobile App](#8-mobile-app)
- [Pattern Structure](#pattern-structure)
- [Customization Guide](#customization-guide)

---

## 1. Dashboard

**Overview screens, KPI displays, monitoring, real-time data**

### Use Cases

- Executive dashboards (KPIs, metrics)
- Application monitoring (servers, APIs)
- Analytics overviews (traffic, conversions)
- Patient/customer portals (personal data)
- Team productivity (tasks, progress)

### Layout Structure

```yaml
layout:
  type: grid
  columns: 12
  responsive:
    mobile: 1 column (stacked)
    tablet: 2 columns (6 + 6)
    desktop: 3 columns (4 + 4 + 4)
  spacing: comfortable (24px gaps)
```

**Grid Example:**
```
┌──────────────┬──────────────┬──────────────┐
│   KPI Card   │   KPI Card   │   KPI Card   │
│   (col-4)    │   (col-4)    │   (col-4)    │
├──────────────┴──────────────┼──────────────┤
│   Large Chart (col-8)       │  Widget List │
│                              │   (col-4)    │
├──────────────┬──────────────┼──────────────┤
│  Table View  │  Table View  │   Sidebar    │
│   (col-8)    │              │   (col-4)    │
└──────────────┴──────────────┴──────────────┘
```

### Navigation

```yaml
navigation:
  type: sidebar
  position: left
  collapsible: true
  width: 240px
  items:
    - label: Overview
      icon: home
    - label: Analytics
      icon: chart
    - label: Reports
      icon: document
    - label: Settings
      icon: cog
```

### Data Visualization

```yaml
data_viz:
  primary:
    - LineChart: Trends over time (revenue, users, traffic)
    - BarChart: Comparisons (sales by product, traffic by channel)
    - MetricCard: Single KPI with trend indicator
    - Sparkline: Inline mini-charts

  secondary:
    - PieChart: Proportions (market share, demographics)
    - Heatmap: Pattern visualization (time-based activity)
    - Gauge: Progress toward goal
    - Table: Detailed data with sorting/filtering
```

### Components

```yaml
core_components:
  - DashboardGrid: Responsive grid container
  - KPICard: Metric display with trend (↑5.2% from last month)
  - ChartWidget: Chart with title, legend, export
  - TableView: Sortable, filterable data table
  - FilterPanel: Date range, segments, filters
  - RefreshButton: Manual data refresh
  - ExportButton: Download CSV/PDF
  - WidgetMenu: Edit, remove, resize widgets

interactive:
  - DateRangePicker: Custom date selection
  - SegmentSelector: Compare segments
  - DrillDownModal: Click metric to see details
  - TooltipHover: Hover charts for exact values
```

### Interaction Patterns

```yaml
interactions:
  drill_down: Click KPI → see detailed breakdown
  time_range: Select date range → all charts update
  real_time: WebSocket updates every 5s
  export: Download current view as CSV/PDF
  customize: Drag-drop widgets, resize, hide/show
```

### Example Implementations

- **Google Analytics** - Web analytics dashboard
- **Stripe Dashboard** - Payment metrics
- **Datadog** - Infrastructure monitoring
- **Tableau** - BI dashboards

---

## 2. Marketplace

**Product listings, filters, transactions, multi-vendor**

### Use Cases

- E-commerce platforms (Etsy, eBay)
- Freelance marketplaces (Upwork, Fiverr)
- Real estate listings (Zillow, Airbnb)
- Job boards (Indeed, LinkedIn)
- Service booking (TaskRabbit, Thumbtack)

### Layout Structure

```yaml
layout:
  type: filtered-grid
  structure:
    left_sidebar: 240px (filters)
    main_content: flex-grow (product grid)
    right_sidebar: optional (cart/saved items)

  product_grid:
    columns:
      mobile: 1-2
      tablet: 2-3
      desktop: 3-4
    card_aspect: 3:4 (portrait for products)
```

**Layout Example:**
```
┌─────────────┬──────────────────────────────────┐
│   FILTERS   │   PRODUCT GRID                   │
│             │  ┌───┬───┬───┬───┐               │
│ Category    │  │ 1 │ 2 │ 3 │ 4 │               │
│ Price       │  ├───┼───┼───┼───┤               │
│ Brand       │  │ 5 │ 6 │ 7 │ 8 │               │
│ Rating      │  ├───┼───┼───┼───┤               │
│ Features    │  │ 9 │10 │11 │12 │               │
│             │  └───┴───┴───┴───┘               │
└─────────────┴──────────────────────────────────┘
```

### Navigation

```yaml
navigation:
  type: category-menu
  structure:
    - Mega menu on hover (desktop)
    - Hamburger menu (mobile)
    - Search prominent in header
    - Breadcrumbs below header

  search:
    autocomplete: true
    suggestions: products + categories
    filters_in_search: true
```

### Components

```yaml
discovery:
  - ProductCard: Image, title, price, rating, seller
  - SearchBar: Autocomplete with category suggestions
  - FilterPanel: Faceted search (category, price, brand, rating)
  - SortDropdown: Sort by relevance, price, rating, date
  - PaginationControls: Load more / page numbers
  - BreadcrumbNav: Home > Category > Subcategory

product_detail:
  - ProductGallery: Image carousel with zoom
  - PriceDisplay: Current price, original price, discount
  - SellerInfo: Seller name, rating, response time
  - AddToCartButton: Large, prominent CTA
  - WishlistButton: Save for later
  - ShareButton: Share product link
  - ReviewsSection: Customer reviews with photos
  - RelatedProducts: "Similar items" carousel

transaction:
  - CartWidget: Mini cart in header with item count
  - CheckoutFlow: Multi-step (cart → shipping → payment)
  - PaymentMethods: Credit card, PayPal, Apple Pay
  - OrderTracking: Shipment status timeline
  - MessageSeller: Direct communication
  - DisputeCenter: Refund/return management
```

### Interaction Patterns

```yaml
browse:
  - Infinite scroll OR pagination
  - Filter without page reload (AJAX)
  - Sort updates instantly
  - Back button preserves filters

purchase:
  - Add to cart → Cart icon animates
  - Guest checkout option
  - Save cart for later
  - 1-click purchase (for registered users)

social_proof:
  - "X people viewing this now"
  - "Only 3 left in stock"
  - "Best seller" badges
  - Recent purchase notifications
```

### Example Implementations

- **Amazon** - Product listings and filters
- **Airbnb** - Property search and booking
- **Etsy** - Handmade marketplace
- **eBay** - Auction and buy-now

---

## 3. CRM

**Contact management, sales pipeline, customer activities**

### Use Cases

- Sales CRM (leads, opportunities, deals)
- Customer support (tickets, conversations)
- Real estate (clients, properties, showings)
- Recruiting (candidates, interviews, hiring)

### Layout Structure

```yaml
layout:
  type: master-detail
  structure:
    sidebar: 200px (navigation)
    master_list: 320px (contacts/deals list)
    detail_pane: flex-grow (selected contact details)

  responsive:
    desktop: 3-column (sidebar + list + detail)
    tablet: list overlays detail on selection
    mobile: full-screen navigation
```

**Layout Example:**
```
┌────┬─────────────┬──────────────────────────┐
│NAV │ CONTACT LIST│   CONTACT DETAILS        │
│    │             │  ┌────────────────────┐  │
│ 🏠 │ ● Alice Co. │  │  Alice Corporation │  │
│ 👤 │ ● Bob Inc.  │  │  alice@corp.com    │  │
│ 📊 │ ○ Charlie   │  ├────────────────────┤  │
│ ⚙️ │ ○ Diana LLC │  │  Recent Activity   │  │
│    │             │  │  📧 Email sent...  │  │
│    │             │  │  📞 Call logged... │  │
└────┴─────────────┴──────────────────────────┘
```

### Navigation

```yaml
navigation:
  type: sidebar + tabs
  sidebar:
    - Contacts
    - Deals
    - Activities
    - Reports
  tabs: (within each section)
    - All
    - My items
    - Recent
    - Starred
```

### Components

```yaml
contacts:
  - ContactCard: Name, company, email, phone, tags
  - ContactList: Searchable, filterable list
  - ContactDetail: Full contact information
  - CompanyCard: Company name, domain, employees
  - TagSelector: Categorize contacts

pipeline:
  - PipelineView: Kanban board (Lead → Qualified → Proposal → Closed)
  - DealCard: Deal name, value, stage, probability
  - ActivityTimeline: Chronological activity feed
  - NextStepsWidget: Upcoming tasks/calls
  - WinProbability: AI-predicted win chance

communication:
  - EmailThread: Email conversation view
  - CallLogger: Log phone calls with notes
  - MeetingScheduler: Calendar integration
  - NotesEditor: Rich text notes
  - FileAttachments: Document uploads

automation:
  - WorkflowBuilder: If-then automation rules
  - EmailTemplates: Saved email templates
  - TaskAutomation: Auto-create follow-up tasks
  - LeadScoring: Auto-prioritize leads
```

### Interaction Patterns

```yaml
efficiency:
  - Quick add (Cmd+N): Create contact without leaving page
  - Bulk actions: Select multiple → assign, tag, delete
  - Keyboard navigation: Arrow keys, Enter to select
  - Global search: Cmd+K to search everything

collaboration:
  - @mentions: Tag teammates in notes
  - Activity feed: See who did what
  - Assignment: Assign contacts to team members
  - Shared views: Saved filters for team
```

### Example Implementations

- **Salesforce** - Sales CRM (pipeline view)
- **HubSpot** - Marketing + sales CRM
- **Pipedrive** - Visual sales pipeline
- **Zendesk** - Customer support CRM

---

## 4. Analytics

**Charts, reports, data exploration, business intelligence**

### Use Cases

- Web analytics (Google Analytics)
- Product analytics (Mixpanel, Amplitude)
- Business intelligence (Tableau, Looker)
- Marketing analytics (Facebook Ads Manager)

### Layout Structure

```yaml
layout:
  type: chart-focused
  structure:
    top_bar: Filters, date range, export
    main_area: Charts + KPIs (2-column grid)
    bottom_section: Data table (optional)

  hierarchy:
    - KPIs at top (above the fold)
    - Trends in large charts
    - Detailed data in tables below
```

### Data Visualization

```yaml
chart_types:
  time_series:
    - LineChart: Trends over time
    - AreaChart: Volume over time
    - ColumnChart: Period comparisons

  categorical:
    - BarChart: Horizontal comparisons
    - PieChart: Proportions (use sparingly)
    - Donut: Proportions with center label

  advanced:
    - Heatmap: Time + category patterns
    - Scatter: Correlation between 2 metrics
    - Funnel: Conversion funnels
    - Cohort: Retention analysis
```

### Components

```yaml
display:
  - KPICard: Large number with sparkline
  - InteractiveChart: Hover for tooltips, click to drill down
  - DataTable: Sortable, exportable tabular data
  - ComparisonMode: Compare time periods side-by-side
  - SegmentBreakdown: Break down by channel, device, geo

controls:
  - DateRangePicker: Preset ranges (7d, 30d, 90d) + custom
  - SegmentSelector: Filter by user type, geography, etc.
  - MetricSelector: Choose metrics to display
  - VisualizationPicker: Switch between chart types
  - ExportButton: CSV, PDF, image export

insights:
  - AnomalyDetection: Highlight unusual spikes/drops
  - TrendIndicator: ↑12% vs last period
  - GoalProgress: Progress toward target
  - Forecast: Predicted future trend
  - Recommendation: AI-suggested insights
```

### Interaction Patterns

```yaml
exploration:
  - Drill down: Click chart → see breakdown
  - Zoom: Select time range on chart
  - Filter: Apply filters → all charts update
  - Segment: Compare segments side-by-side

sharing:
  - Share link: URL with current filters
  - Schedule reports: Email daily/weekly
  - Dashboard embedding: Embed in other apps
  - Export data: Download for offline analysis
```

### Example Implementations

- **Google Analytics** - Web analytics
- **Tableau** - BI dashboards
- **Mixpanel** - Product analytics
- **Looker** - Data exploration

---

## 5. Onboarding

**User activation, guided setup, trial flows**

### Use Cases

- SaaS product tours
- Account setup wizards
- Feature activation flows
- Trial-to-paid conversion

### Layout Structure

```yaml
layout:
  type: wizard-steps
  structure:
    progress_bar: Top of page (Step 1 of 5)
    main_content: Centered (max-width 640px)
    navigation: Next/back buttons at bottom

  step_pattern:
    - Title + description
    - Form or content
    - CTA (Next, Skip, or Complete)
```

### Components

```yaml
progress:
  - ProgressBar: Visual step indicator
  - Checklist: Onboarding tasks with checkmarks
  - CompletionBadge: "80% complete" motivator

guidance:
  - WizardSteps: Multi-step flow
  - TooltipGuide: Contextual help tooltips
  - VideoTutorial: Embedded walkthrough video
  - InteractiveTour: Highlight UI elements
  - HelpArticleLink: Link to docs

engagement:
  - WelcomeMessage: Personalized greeting
  - SuccessCelebration: Confetti on completion
  - RewardsUnlock: "You've unlocked X feature!"
  - InviteTeammates: Invite colleagues
  - IntegrationSetup: Connect tools
```

### Interaction Patterns

```yaml
progression:
  - Linear steps: Can't skip ahead
  - Optional steps: "Skip for now" option
  - Resume: Save progress, continue later
  - Time estimate: "5 min to complete"

motivation:
  - Progress indicators: Show how far along
  - Quick wins: Easy tasks first
  - Social proof: "10,000 users have completed this"
  - Incentives: "Complete setup → unlock premium features"
```

### Example Implementations

- **Notion** - Workspace setup wizard
- **Slack** - Team onboarding flow
- **Duolingo** - Learning path onboarding
- **Stripe** - Account activation checklist

---

## 6. API Service

**Developer portals, documentation, API keys**

### Layout Structure

```yaml
layout:
  type: documentation-focused
  structure:
    left_sidebar: 240px (nav tree)
    main_content: 720px (docs)
    right_sidebar: 240px (table of contents)
```

### Components

```yaml
documentation:
  - CodeBlock: Syntax-highlighted examples
  - EndpointCard: Method, path, description
  - ParameterTable: Request params documentation
  - ResponseExample: Sample JSON responses
  - TryItPanel: Interactive API testing

developer_tools:
  - APIKeyManager: Generate and revoke keys
  - UsageDashboard: API calls, rate limits
  - WebhookSettings: Configure webhooks
  - SDKDownload: Client libraries
  - PlaygroundTool: Test API without code
```

---

## 7. Admin Panel

**System configuration, user management, settings**

### Layout Structure

```yaml
layout:
  type: settings-sidebar
  structure:
    sidebar: Settings navigation
    main: Forms and tables
```

### Components

```yaml
management:
  - DataTable: Users, roles, permissions
  - FormBuilder: Configuration forms
  - RoleManager: Permission assignment
  - AuditLog: System activity log
  - BackupRestore: Data backup controls
```

---

## 8. Mobile App

**Mobile-first layouts, gestures, native feel**

### Layout Structure

```yaml
layout:
  type: mobile-native
  navigation:
    top_bar: Title + actions
    bottom_tabs: Primary navigation (4-5 tabs)

  gestures:
    - Swipe right: Go back
    - Pull down: Refresh
    - Long press: Context menu
    - Swipe left: Delete/archive
```

### Components

```yaml
mobile_specific:
  - SwipeCard: Swipeable cards (Tinder-style)
  - PullToRefresh: Refresh data gesture
  - BottomSheet: Modal from bottom
  - FloatingActionButton: Primary action
  - TabBar: Bottom navigation
  - StatusBar: Native status bar styling
```

---

## Pattern Structure

Each use case pattern includes:

```yaml
name: string
display_name: string
description: string

layout:
  type: string
  structure: object
  responsive: object

navigation:
  type: string
  items: array

components: array
interactions: object
examples: array
```

---

## Customization Guide

### Override Layout

```yaml
# .buildrunner/config.yaml
design:
  use_case: dashboard
  overrides:
    layout:
      columns: 16  # Override 12-column default
```

### Add Custom Components

```yaml
design:
  use_case: marketplace
  custom_components:
    - NFTCard
    - CryptoWallet
```

---

## Related Documentation

- **[Design System](DESIGN_SYSTEM.md)** - Overview and merging
- **[Industry Profiles](INDUSTRY_PROFILES.md)** - Industry-specific patterns
- **[PRD Wizard](PRD_WIZARD.md)** - Integration with PROJECT_SPEC

---

**Use Case Patterns** - Proven UX patterns for every application type 🎯
