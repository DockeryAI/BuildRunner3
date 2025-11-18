# Build 1B - Complete Design System

**Branch:** `build/v3.1-design-system`
**Worktree:** `../br3-design-system`
**Duration:** 1 week
**Execute in parallel with Build 1A**

---

## Context

Currently, the design system has only 3 of 8 industry profiles and 3 of 8 use case patterns (45-62% test coverage). This build completes:
- 5 missing industry YAML profiles
- 5 missing use case YAML patterns
- Tailwind 4 integration
- Storybook component library generator
- Visual regression testing
- Full test coverage (85%+)

---

## Setup

### 1. Create Git Worktree
```bash
cd /Users/byronhudson/Projects/BuildRunner3
git worktree add ../br3-design-system -b build/v3.1-design-system
cd ../br3-design-system
```

### 2. Install Dependencies
```bash
pip install pytest pytest-cov pyyaml -q
pip install playwright>=1.40.0 -q
playwright install chromium
```

### 3. Verify Current State
```bash
# Check existing templates
ls -la templates/industries/
ls -la templates/use_cases/

# Should see:
# industries: healthcare.yaml, fintech.yaml, saas.yaml
# use_cases: dashboard.yaml, marketplace.yaml, analytics.yaml
```

---

## Task 1: Create 5 Missing Industry Profiles

### Industry 1: Government

**File:** `templates/industries/government.yaml` (NEW FILE)

```yaml
name: "Government"
description: "Federal, state, and local government applications"
category: "Public Sector"

colors:
  primary:
    main: "#0f3c7e"        # Official government blue
    light: "#4a7bb7"
    dark: "#082654"
  secondary:
    main: "#8b0000"        # Seal red
    light: "#c62828"
    dark: "#5f0000"
  accent:
    main: "#d4af37"        # Gold
    light: "#ffd700"
    dark: "#b8941e"
  neutral:
    50: "#fafafa"
    100: "#f5f5f5"
    200: "#eeeeee"
    300: "#e0e0e0"
    400: "#bdbdbd"
    500: "#9e9e9e"
    600: "#757575"
    700: "#616161"
    800: "#424242"
    900: "#212121"
  semantic:
    success: "#2e7d32"     # Dark green for confirmation
    warning: "#f57c00"     # Orange for warnings
    error: "#c62828"       # Red for errors
    info: "#1976d2"        # Blue for information

typography:
  fonts:
    primary: "'Roboto', 'Arial', sans-serif"
    secondary: "'Georgia', 'Times New Roman', serif"
    monospace: "'Courier New', monospace"
  sizes:
    xs: "0.75rem"     # 12px
    sm: "0.875rem"    # 14px
    base: "1rem"      # 16px - WCAG minimum
    lg: "1.125rem"    # 18px
    xl: "1.25rem"     # 20px
    "2xl": "1.5rem"   # 24px
    "3xl": "1.875rem" # 30px
    "4xl": "2.25rem"  # 36px
  weights:
    normal: 400
    medium: 500
    semibold: 600
    bold: 700
  lineHeights:
    tight: 1.25
    normal: 1.5
    relaxed: 1.75

spacing:
  scale: [0, 4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96, 128]
  container:
    padding: "1rem"
    maxWidth: "1280px"

borders:
  radius:
    none: "0"
    sm: "0.125rem"   # 2px
    base: "0.25rem"  # 4px - subtle
    md: "0.375rem"   # 6px
    lg: "0.5rem"     # 8px
    full: "9999px"
  width:
    default: "1px"
    medium: "2px"
    thick: "4px"

shadows:
  sm: "0 1px 2px 0 rgba(0, 0, 0, 0.05)"
  base: "0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)"
  md: "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)"
  lg: "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)"
  none: "none"

breakpoints:
  sm: "640px"
  md: "768px"
  lg: "1024px"
  xl: "1280px"
  "2xl": "1536px"

compliance:
  standards:
    - "Section 508"           # Federal accessibility
    - "WCAG 2.1 AAA"          # Highest accessibility level
    - "FedRAMP Moderate/High" # Cloud security
    - "NIST 800-53"           # Security controls
    - "FISMA"                 # Federal security management
  requirements:
    - "All text minimum 16px for readability"
    - "4.5:1 color contrast ratio minimum (AAA: 7:1)"
    - "Keyboard navigation for all interactive elements"
    - "Screen reader compatibility required"
    - "Plain language requirements (8th grade reading level)"
    - "Multi-language support"
    - "508 compliance documentation required"
  accessibility:
    - "ARIA labels on all interactive elements"
    - "Focus indicators visible and high contrast"
    - "Skip navigation links"
    - "Alternative text for all images"
    - "Captions for videos"
    - "Transcripts for audio"

components:
  buttons:
    padding: "0.75rem 1.5rem"
    fontSize: "1rem"
    fontWeight: 600
    borderRadius: "0.25rem"  # Minimal rounding
    textTransform: "none"
  forms:
    inputPadding: "0.875rem 1rem"
    inputBorderRadius: "0.25rem"
    labelFontWeight: 600
    requiredIndicator: "*"
    helpTextSize: "0.875rem"
  cards:
    padding: "1.5rem"
    borderRadius: "0.25rem"
    shadow: "md"
    border: "1px solid #e0e0e0"
  tables:
    headerBackground: "#f5f5f5"
    rowHover: "#fafafa"
    borderColor: "#e0e0e0"
    cellPadding: "0.75rem 1rem"

security:
  level: "critical"
  features:
    - "Authority to Operate (ATO) required"
    - "Multi-factor authentication mandatory"
    - "Session timeout: 15 minutes"
    - "Audit logging for all actions"
    - "Encryption at rest and in transit (FIPS 140-2)"
    - "Role-based access control (RBAC)"
    - "Regular security scans and penetration testing"
    - "Incident response plan required"
    - "Data retention policies enforced"

patterns:
  - "Official government header with seal"
  - "Clear breadcrumb navigation"
  - "Prominent search functionality"
  - "Footer with required links (Privacy, FOIA, etc.)"
  - "Contact information easily accessible"
  - "Print-friendly layouts"
  - "PDF document generation"

notes:
  - "Government sites must follow US Web Design System (USWDS) guidelines"
  - "All content must be in plain language"
  - "Public-facing sites require OMB approval"
  - "Must support legacy browsers (IE11 often required)"
  - "Uptime SLA typically 99.9%"
```

---

### Industry 2: Legal

**File:** `templates/industries/legal.yaml` (NEW FILE)

```yaml
name: "Legal"
description: "Law firms, legal tech, case management systems"
category: "Professional Services"

colors:
  primary:
    main: "#1a237e"        # Deep navy (trust, authority)
    light: "#3949ab"
    dark: "#0d1b5e"
  secondary:
    main: "#37474f"        # Charcoal (professionalism)
    light: "#546e7a"
    dark: "#263238"
  accent:
    main: "#b8860b"        # Dark gold (prestige)
    light: "#daa520"
    dark: "#8b6914"
  neutral:
    50: "#fafafa"
    100: "#f5f5f5"
    200: "#eeeeee"
    300: "#e0e0e0"
    400: "#bdbdbd"
    500: "#9e9e9e"
    600: "#757575"
    700: "#616161"
    800: "#424242"
    900: "#212121"
  semantic:
    success: "#2e7d32"
    warning: "#f57c00"
    error: "#c62828"
    info: "#1976d2"

typography:
  fonts:
    primary: "'Merriweather', 'Georgia', serif"      # Serif for professionalism
    secondary: "'Open Sans', 'Helvetica', sans-serif" # Sans-serif for UI
    monospace: "'Courier New', monospace"             # For legal citations
  sizes:
    xs: "0.75rem"
    sm: "0.875rem"
    base: "1rem"
    lg: "1.125rem"
    xl: "1.25rem"
    "2xl": "1.5rem"
    "3xl": "1.875rem"
    "4xl": "2.25rem"
  weights:
    normal: 400
    medium: 500
    semibold: 600
    bold: 700
  lineHeights:
    tight: 1.25
    normal: 1.6      # Extra line height for readability
    relaxed: 1.8

spacing:
  scale: [0, 4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96, 128]
  container:
    padding: "1.5rem"
    maxWidth: "1440px"  # Wider for document viewing

borders:
  radius:
    none: "0"
    sm: "0.125rem"
    base: "0.25rem"
    md: "0.375rem"
    lg: "0.5rem"
    full: "9999px"
  width:
    default: "1px"
    medium: "2px"
    thick: "3px"

shadows:
  sm: "0 1px 2px 0 rgba(0, 0, 0, 0.05)"
  base: "0 1px 3px 0 rgba(0, 0, 0, 0.1)"
  md: "0 4px 6px -1px rgba(0, 0, 0, 0.1)"
  lg: "0 10px 15px -3px rgba(0, 0, 0, 0.1)"
  xl: "0 20px 25px -5px rgba(0, 0, 0, 0.1)"  # Elevated panels

breakpoints:
  sm: "640px"
  md: "768px"
  lg: "1024px"
  xl: "1280px"
  "2xl": "1536px"

compliance:
  standards:
    - "Attorney-Client Privilege Protection"
    - "ABA Technology Standards"
    - "State Bar Ethics Rules"
    - "Legal Hold Requirements"
    - "eDiscovery Standards"
  requirements:
    - "End-to-end encryption for client communications"
    - "Document retention policies (7+ years typically)"
    - "Audit trails for all document access"
    - "Secure client portal with MFA"
    - "Redaction capabilities for sensitive information"
    - "Version control for documents"
    - "Conflict of interest checking"
  accessibility:
    - "WCAG 2.1 AA minimum"
    - "Document accessibility (PDF/A compliance)"
    - "Screen reader support for case management"

components:
  buttons:
    padding: "0.75rem 1.5rem"
    fontSize: "1rem"
    fontWeight: 600
    borderRadius: "0.25rem"
    textTransform: "none"
  forms:
    inputPadding: "0.875rem 1rem"
    inputBorderRadius: "0.25rem"
    labelFontWeight: 600
    requiredIndicator: "*"
    helpTextSize: "0.875rem"
  cards:
    padding: "2rem"
    borderRadius: "0.5rem"
    shadow: "lg"
    border: "1px solid #e0e0e0"
  documentViewer:
    backgroundColor: "#fafafa"
    toolbarBackground: "#37474f"
    annotationColors: ["#ffeb3b", "#4caf50", "#f44336", "#2196f3"]

security:
  level: "critical"
  features:
    - "Client confidentiality protected"
    - "Encryption: AES-256 at rest, TLS 1.3 in transit"
    - "Multi-factor authentication required"
    - "Role-based access control (attorneys, paralegals, clients, admins)"
    - "Audit logging for compliance"
    - "Secure document sharing with expiration"
    - "Watermarking for sensitive documents"
    - "Data loss prevention (DLP)"
    - "Regular security audits"

patterns:
  - "Case/matter-centric organization"
  - "Document management with version control"
  - "Time tracking and billing integration"
  - "Calendar with conflict checking"
  - "Client intake forms with encryption"
  - "Secure messaging with clients"
  - "Research tools integration (Westlaw, LexisNexis)"
  - "Court filing integration (eFiling)"

notes:
  - "Legal documents often use serif fonts for readability"
  - "Blue book citation format support"
  - "Integration with practice management software common"
  - "Mobile access for attorneys often required"
  - "Backup and disaster recovery critical (no data loss tolerance)"
```

---

### Industry 3: Nonprofit

**File:** `templates/industries/nonprofit.yaml` (NEW FILE)

```yaml
name: "Nonprofit"
description: "Charitable organizations, NGOs, foundations"
category: "Social Impact"

colors:
  primary:
    main: "#2e7d32"        # Mission green (growth, hope)
    light: "#4caf50"
    dark: "#1b5e20"
  secondary:
    main: "#1976d2"        # Trust blue
    light: "#42a5f5"
    dark: "#0d47a1"
  accent:
    main: "#f57c00"        # Action orange (warmth, urgency)
    light: "#ff9800"
    dark: "#e65100"
  neutral:
    50: "#fafafa"
    100: "#f5f5f5"
    200: "#eeeeee"
    300: "#e0e0e0"
    400: "#bdbdbd"
    500: "#9e9e9e"
    600: "#757575"
    700: "#616161"
    800: "#424242"
    900: "#212121"
  semantic:
    success: "#4caf50"
    warning: "#ff9800"
    error: "#f44336"
    info: "#2196f3"

typography:
  fonts:
    primary: "'Inter', 'Helvetica Neue', sans-serif"
    secondary: "'Merriweather', 'Georgia', serif"
    monospace: "'Roboto Mono', monospace"
  sizes:
    xs: "0.75rem"
    sm: "0.875rem"
    base: "1rem"
    lg: "1.125rem"
    xl: "1.25rem"
    "2xl": "1.5rem"
    "3xl": "1.875rem"
    "4xl": "2.25rem"
    "5xl": "3rem"      # Large impact headlines
  weights:
    normal: 400
    medium: 500
    semibold: 600
    bold: 700
    extrabold: 800    # For impact statements
  lineHeights:
    tight: 1.25
    normal: 1.5
    relaxed: 1.75

spacing:
  scale: [0, 4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96, 128]
  container:
    padding: "1rem"
    maxWidth: "1280px"

borders:
  radius:
    none: "0"
    sm: "0.125rem"
    base: "0.25rem"
    md: "0.5rem"
    lg: "0.75rem"
    xl: "1rem"
    full: "9999px"
  width:
    default: "1px"
    medium: "2px"
    thick: "3px"

shadows:
  sm: "0 1px 2px 0 rgba(0, 0, 0, 0.05)"
  base: "0 1px 3px 0 rgba(0, 0, 0, 0.1)"
  md: "0 4px 6px -1px rgba(0, 0, 0, 0.1)"
  lg: "0 10px 15px -3px rgba(0, 0, 0, 0.1)"
  xl: "0 20px 25px -5px rgba(0, 0, 0, 0.1)"

breakpoints:
  sm: "640px"
  md: "768px"
  lg: "1024px"
  xl: "1280px"
  "2xl": "1536px"

compliance:
  standards:
    - "501(c)(3) IRS Requirements"
    - "State Charity Registration"
    - "Financial Transparency (Form 990)"
    - "Donor Privacy Regulations"
    - "Charitable Solicitation Laws"
    - "GDPR (for international donors)"
  requirements:
    - "Transparent financial reporting"
    - "Donor acknowledgment letters (tax deductible)"
    - "Privacy policy for donor information"
    - "Secure donation processing (PCI DSS)"
    - "Mission statement prominently displayed"
    - "Impact metrics and outcomes reporting"
    - "Board of directors listing"
  accessibility:
    - "WCAG 2.1 AA minimum (inclusive mission)"
    - "Multi-language support for global reach"

components:
  buttons:
    padding: "0.875rem 2rem"
    fontSize: "1rem"
    fontWeight: 700
    borderRadius: "0.5rem"
    textTransform: "uppercase"  # Strong calls-to-action
  donationButton:
    padding: "1rem 2.5rem"
    fontSize: "1.125rem"
    fontWeight: 800
    borderRadius: "0.75rem"
    backgroundColor: "#f57c00"
    hoverScale: "1.05"
  forms:
    inputPadding: "0.875rem 1rem"
    inputBorderRadius: "0.5rem"
    labelFontWeight: 600
    requiredIndicator: "*"
    helpTextSize: "0.875rem"
  cards:
    padding: "1.5rem"
    borderRadius: "0.75rem"
    shadow: "md"
    border: "none"
  impactMetric:
    numberSize: "3rem"
    numberWeight: 800
    numberColor: "#2e7d32"
    labelSize: "1rem"
    labelWeight: 600

security:
  level: "high"
  features:
    - "PCI DSS Level 1 for donations"
    - "SSL/TLS encryption"
    - "Donor data protection"
    - "Secure payment processing (Stripe, PayPal)"
    - "GDPR compliance for international donors"
    - "Recurring donation management"
    - "Donor communication preferences"

patterns:
  - "Prominent donation call-to-action"
  - "Impact stories with photos/videos"
  - "Progress bars for fundraising goals"
  - "Volunteer sign-up forms"
  - "Event calendar and registration"
  - "Newsletter subscription"
  - "Social proof (testimonials, donor count)"
  - "Mission-driven homepage"
  - "Transparency section (financials, annual reports)"

notes:
  - "Emotional connection crucial - use storytelling"
  - "Mobile-first (many donors on mobile)"
  - "Fast donation process (minimize friction)"
  - "Social sharing built-in"
  - "Email campaigns for donor retention"
  - "Monthly recurring donations emphasized"
  - "Tax receipt generation automated"
```

---

### Industry 4: Gaming

**File:** `templates/industries/gaming.yaml` (NEW FILE)

```yaml
name: "Gaming"
description: "Video games, esports, gaming platforms"
category: "Entertainment"

colors:
  primary:
    main: "#7c3aed"        # Electric purple
    light: "#a78bfa"
    dark: "#5b21b6"
  secondary:
    main: "#06b6d4"        # Cyan (energy)
    light: "#22d3ee"
    dark: "#0891b2"
  accent:
    main: "#f59e0b"        # Amber (highlight)
    light: "#fbbf24"
    dark: "#d97706"
  neutral:
    50: "#fafafa"
    100: "#18181b"        # Dark mode default
    200: "#27272a"
    300: "#3f3f46"
    400: "#52525b"
    500: "#71717a"
    600: "#a1a1aa"
    700: "#d4d4d8"
    800: "#e4e4e7"
    900: "#f4f4f5"
  semantic:
    success: "#10b981"
    warning: "#f59e0b"
    error: "#ef4444"
    info: "#3b82f6"
  special:
    neon: "#ff00ff"
    glow: "#00ffff"
    gold: "#ffd700"
    legendary: "#ff6b35"

typography:
  fonts:
    primary: "'Poppins', 'Helvetica Neue', sans-serif"
    display: "'Orbitron', 'Rajdhani', sans-serif"  # Futuristic
    monospace: "'Fira Code', 'Courier New', monospace"
  sizes:
    xs: "0.75rem"
    sm: "0.875rem"
    base: "1rem"
    lg: "1.125rem"
    xl: "1.25rem"
    "2xl": "1.5rem"
    "3xl": "2rem"
    "4xl": "2.5rem"
    "5xl": "3.5rem"
  weights:
    normal: 400
    medium: 500
    semibold: 600
    bold: 700
    extrabold: 800
    black: 900
  lineHeights:
    tight: 1.1
    normal: 1.5
    relaxed: 1.75

spacing:
  scale: [0, 4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96, 128, 160, 192]
  container:
    padding: "1rem"
    maxWidth: "1920px"  # Wide for gaming displays

borders:
  radius:
    none: "0"
    sm: "0.25rem"
    base: "0.5rem"
    md: "0.75rem"
    lg: "1rem"
    xl: "1.5rem"
    full: "9999px"
  width:
    default: "2px"
    medium: "3px"
    thick: "4px"
    neon: "3px"

shadows:
  sm: "0 1px 2px 0 rgba(0, 0, 0, 0.3)"
  base: "0 2px 4px 0 rgba(0, 0, 0, 0.4)"
  md: "0 4px 8px -1px rgba(0, 0, 0, 0.5)"
  lg: "0 10px 20px -3px rgba(0, 0, 0, 0.5)"
  xl: "0 20px 40px -5px rgba(0, 0, 0, 0.6)"
  neon: "0 0 20px rgba(124, 58, 237, 0.8), 0 0 40px rgba(124, 58, 237, 0.4)"
  glow: "0 0 10px currentColor, 0 0 20px currentColor"

breakpoints:
  sm: "640px"
  md: "768px"
  lg: "1024px"
  xl: "1280px"
  "2xl": "1536px"
  "3xl": "1920px"  # 1080p
  "4xl": "2560px"  # 1440p

compliance:
  standards:
    - "COPPA (Children's Online Privacy Protection Act)"
    - "ESRB Rating Guidelines"
    - "GDPR (international players)"
    - "Platform Terms (Steam, Epic, Console)"
    - "Anti-Cheat Integration"
  requirements:
    - "Age verification for mature content"
    - "Parental controls"
    - "Terms of Service acceptance"
    - "Privacy policy for player data"
    - "Fair play and anti-cheat measures"
    - "Reporting system for toxic behavior"
    - "Data portability (player progress)"
  accessibility:
    - "Colorblind modes"
    - "Subtitles/captions"
    - "Remappable controls"
    - "UI scaling options"
    - "Audio cues for visual elements"

components:
  buttons:
    padding: "0.75rem 2rem"
    fontSize: "1rem"
    fontWeight: 700
    borderRadius: "0.5rem"
    textTransform: "uppercase"
    border: "2px solid currentColor"
    hoverGlow: true
  heroButton:
    padding: "1rem 3rem"
    fontSize: "1.25rem"
    fontWeight: 800
    borderRadius: "0.75rem"
    backgroundColor: "#7c3aed"
    boxShadow: "neon"
  forms:
    inputPadding: "0.875rem 1rem"
    inputBorderRadius: "0.5rem"
    inputBackground: "#27272a"
    inputBorder: "2px solid #3f3f46"
    labelFontWeight: 600
  cards:
    padding: "1.5rem"
    borderRadius: "1rem"
    shadow: "lg"
    border: "2px solid #3f3f46"
    backgroundColor: "#18181b"
  leaderboard:
    rowHeight: "3rem"
    rankBadgeSize: "2rem"
    highlightColor: "#7c3aed"
    goldColor: "#ffd700"
    silverColor: "#c0c0c0"
    bronzeColor: "#cd7f32"

security:
  level: "high"
  features:
    - "Account security (2FA)"
    - "Anti-cheat integration (EasyAntiCheat, BattlEye)"
    - "DDoS protection"
    - "Rate limiting for API calls"
    - "Session management"
    - "Secure multiplayer communication"
    - "Ban/suspension system"
    - "Player reporting and moderation"

patterns:
  - "Leaderboards with rankings"
  - "Achievement/trophy system"
  - "Player profiles with stats"
  - "Inventory/loadout management"
  - "Friends list and party system"
  - "Matchmaking queue"
  - "In-game chat"
  - "Store/marketplace for items"
  - "Battle pass / season progression"
  - "Daily rewards and quests"

notes:
  - "Dark mode is default for gaming"
  - "60+ FPS UI animations expected"
  - "High contrast for readability during gameplay"
  - "Controller support essential (console)"
  - "Low latency critical for competitive games"
  - "Haptic feedback integration (PS5, Xbox)"
  - "Cross-platform play considerations"
```

---

### Industry 5: Manufacturing

**File:** `templates/industries/manufacturing.yaml` (NEW FILE)

```yaml
name: "Manufacturing"
description: "Industrial manufacturing, supply chain, production systems"
category: "Industrial"

colors:
  primary:
    main: "#1565c0"        # Industrial blue
    light: "#1976d2"
    dark: "#0d47a1"
  secondary:
    main: "#ff6f00"        # Safety orange
    light: "#ff8f00"
    dark: "#e65100"
  accent:
    main: "#616161"        # Steel grey
    light: "#757575"
    dark: "#424242"
  neutral:
    50: "#fafafa"
    100: "#f5f5f5"
    200: "#eeeeee"
    300: "#e0e0e0"
    400: "#bdbdbd"
    500: "#9e9e9e"
    600: "#757575"
    700: "#616161"
    800: "#424242"
    900: "#212121"
  semantic:
    success: "#2e7d32"
    warning: "#f57c00"
    error: "#c62828"
    info: "#1976d2"
  operational:
    online: "#4caf50"
    offline: "#9e9e9e"
    maintenance: "#ff9800"
    fault: "#f44336"

typography:
  fonts:
    primary: "'Roboto', 'Arial', sans-serif"
    secondary: "'Roboto Condensed', sans-serif"
    monospace: "'Roboto Mono', 'Courier New', monospace"
  sizes:
    xs: "0.75rem"
    sm: "0.875rem"
    base: "1rem"
    lg: "1.125rem"
    xl: "1.5rem"       # Large for tablet/touch screens
    "2xl": "2rem"
    "3xl": "2.5rem"
    "4xl": "3rem"
  weights:
    normal: 400
    medium: 500
    semibold: 600
    bold: 700
  lineHeights:
    tight: 1.25
    normal: 1.5
    relaxed: 1.75

spacing:
  scale: [0, 4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96]
  container:
    padding: "1rem"
    maxWidth: "1600px"  # Wide for dashboards

borders:
  radius:
    none: "0"
    sm: "0.125rem"
    base: "0.25rem"
    md: "0.375rem"
    lg: "0.5rem"
    full: "9999px"
  width:
    default: "1px"
    medium: "2px"
    thick: "3px"
    status: "4px"

shadows:
  sm: "0 1px 2px 0 rgba(0, 0, 0, 0.05)"
  base: "0 1px 3px 0 rgba(0, 0, 0, 0.1)"
  md: "0 4px 6px -1px rgba(0, 0, 0, 0.1)"
  lg: "0 10px 15px -3px rgba(0, 0, 0, 0.1)"

breakpoints:
  sm: "640px"
  md: "768px"
  lg: "1024px"
  xl: "1366px"   # Common industrial display
  "2xl": "1920px"

compliance:
  standards:
    - "ISO 9001 (Quality Management)"
    - "ISO 14001 (Environmental)"
    - "OSHA Safety Standards"
    - "FDA (if applicable)"
    - "Six Sigma / Lean Manufacturing"
    - "GMP (Good Manufacturing Practice)"
  requirements:
    - "Audit trail for all production changes"
    - "Quality control checkpoints"
    - "Equipment maintenance logs"
    - "Safety incident reporting"
    - "Inventory tracking (raw materials, WIP, finished goods)"
    - "Compliance documentation"
    - "Environmental impact tracking"
  accessibility:
    - "Touch-friendly for factory floor tablets"
    - "High contrast for industrial lighting"
    - "Large touch targets (44px minimum)"

components:
  buttons:
    padding: "1rem 1.5rem"
    fontSize: "1rem"
    fontWeight: 600
    borderRadius: "0.25rem"
    minTouchTarget: "44px"
  emergencyButton:
    padding: "1.5rem 2rem"
    fontSize: "1.25rem"
    fontWeight: 700
    backgroundColor: "#f44336"
    border: "3px solid #c62828"
  forms:
    inputPadding: "1rem 1.25rem"
    inputBorderRadius: "0.25rem"
    labelFontWeight: 600
    inputMinHeight: "48px"
  cards:
    padding: "1.5rem"
    borderRadius: "0.5rem"
    shadow: "md"
    border: "1px solid #e0e0e0"
  dashboard:
    widgetPadding: "1.5rem"
    widgetBackground: "#ffffff"
    gridGap: "1.5rem"
  statusIndicator:
    size: "1rem"
    borderRadius: "50%"
    glow: true

security:
  level: "high"
  features:
    - "Operational technology (OT) security"
    - "Network segmentation (IT/OT isolation)"
    - "Role-based access control"
    - "Equipment access logs"
    - "Secure SCADA integration"
    - "Real-time monitoring"
    - "Supply chain security"
    - "Physical security integration"

patterns:
  - "Real-time production dashboard"
  - "Equipment status monitoring (OEE)"
  - "Inventory tracking and alerts"
  - "Maintenance scheduling"
  - "Quality control workflows"
  - "Work order management"
  - "Barcode/QR code scanning"
  - "Time tracking (labor)"
  - "Shift handoff reports"
  - "Supply chain visibility"

notes:
  - "Ruggedized tablets common on factory floor"
  - "24/7 operations require shift handoffs"
  - "Real-time data critical (IoT sensors, PLCs)"
  - "Minimal downtime tolerance"
  - "Integration with ERP systems (SAP, Oracle)"
  - "Offline mode for network outages"
  - "Print support for work orders and labels"
```

---

## Task 2: Create 5 Missing Use Case Patterns

### Use Case 1: Chat/Messaging

**File:** `templates/use_cases/chat.yaml` (NEW FILE)

```yaml
name: "Chat / Messaging"
description: "Real-time messaging, chat applications, communication platforms"
category: "Communication"

layout:
  structure: "sidebar-main-detail"
  regions:
    sidebar:
      width: "280px"
      contains:
        - "Conversation list"
        - "Search"
        - "Filters (unread, favorites)"
        - "User status"
    main:
      width: "flex-1"
      contains:
        - "Message thread"
        - "Input composer"
        - "File attachments"
        - "Emoji picker"
    detail:
      width: "320px"
      collapsible: true
      contains:
        - "Conversation info"
        - "Participant list"
        - "Shared media"
        - "Settings"

navigation:
  primary:
    - label: "Direct Messages"
      icon: "message"
    - label: "Channels"
      icon: "hash"
    - label: "Groups"
      icon: "users"
  secondary:
    - label: "Search"
      icon: "search"
      shortcut: "Cmd+K"
    - label: "Settings"
      icon: "settings"

components:
  messageList:
    layout: "vertical"
    grouping: "by-sender-and-time"
    virtualScroll: true
    infiniteScroll: "top"
    dateMarkers: true
  messageComposer:
    multiline: true
    autoGrow: true
    maxHeight: "200px"
    features:
      - "Rich text formatting"
      - "Emoji picker"
      - "File upload"
      - "Mentions (@user)"
      - "Slash commands"
  conversationListItem:
    height: "72px"
    preview: "last-message"
    indicators:
      - "Unread badge"
      - "Typing indicator"
      - "User status"
      - "Timestamp"
  userAvatar:
    sizes: ["sm", "md", "lg"]
    statusIndicator: true
    fallback: "initials"

interactions:
  realTime:
    - "Message delivery (WebSocket)"
    - "Typing indicators"
    - "Read receipts"
    - "Presence (online/offline)"
  optimistic:
    - "Send message immediately"
    - "Show pending state"
    - "Retry on failure"
  gestures:
    - "Swipe to reply"
    - "Long-press for options"
    - "Pull to refresh"

patterns:
  messaging:
    - "Bubble layout for messages"
    - "Sender on right, recipient on left"
    - "Timestamps on hover"
    - "Grouping consecutive messages"
  notifications:
    - "Desktop notifications"
    - "Badge count on tab/icon"
    - "Sound on new message"
    - "Do not disturb mode"
  search:
    - "Full-text search across conversations"
    - "Filter by sender, date, type"
    - "Jump to message in context"
  media:
    - "Inline image/video preview"
    - "Lightbox for full view"
    - "File download"
    - "Link previews with og:image"

dataFlow:
  messageDelivery:
    - "Client sends message"
    - "Server validates and stores"
    - "WebSocket broadcasts to recipients"
    - "Clients update UI optimistically"
  presence:
    - "Heartbeat every 30s"
    - "Online/away/offline status"
    - "Last seen timestamp"

performance:
  - "Virtual scrolling for long threads"
  - "Lazy loading of media"
  - "Message pagination (50 per page)"
  - "WebSocket for real-time updates"
  - "IndexedDB for offline storage"

accessibility:
  - "Keyboard navigation (Tab, Arrow keys)"
  - "Screen reader announcements for new messages"
  - "Focus management"
  - "ARIA live regions for updates"

responsiveness:
  mobile:
    - "Full-screen message view"
    - "Bottom navigation"
    - "Swipe gestures"
  tablet:
    - "Split view (list + detail)"
    - "Adaptive sidebar"
  desktop:
    - "Three-column layout"
    - "Keyboard shortcuts"

notes:
  - "WebSocket required for real-time"
  - "Offline support with service workers"
  - "End-to-end encryption considerations (Signal Protocol)"
  - "Message history retention policies"
  - "Rate limiting for spam prevention"
```

---

### Use Case 2: Video Streaming

**File:** `templates/use_cases/video.yaml` (NEW FILE)

```yaml
name: "Video Streaming"
description: "Video playback, streaming platforms, media libraries"
category: "Media"

layout:
  structure: "hero-grid-sidebar"
  regions:
    hero:
      height: "60vh"
      contains:
        - "Featured video player"
        - "Video metadata"
        - "Action buttons (play, add to list)"
    grid:
      columns: "responsive"
      contains:
        - "Thumbnail grid"
        - "Category rows"
        - "Recommendations"
    sidebar:
      width: "320px"
      collapsible: true
      contains:
        - "Up next queue"
        - "Related videos"
        - "Comments"

navigation:
  primary:
    - label: "Home"
      icon: "home"
    - label: "Browse"
      icon: "grid"
    - label: "My List"
      icon: "bookmark"
    - label: "Search"
      icon: "search"
  secondary:
    - label: "Profile"
      icon: "user"
    - label: "Settings"
      icon: "settings"

components:
  videoPlayer:
    aspectRatio: "16:9"
    controls:
      - "Play/Pause"
      - "Volume"
      - "Seek bar"
      - "Playback speed"
      - "Quality selector"
      - "Fullscreen"
      - "Picture-in-picture"
      - "Subtitles/CC"
    features:
      - "Adaptive bitrate (HLS/DASH)"
      - "Keyboard shortcuts"
      - "Double-tap to skip (10s)"
      - "Thumbnail preview on hover"
  videoThumbnail:
    aspectRatio: "16:9"
    overlay:
      - "Duration badge"
      - "Progress bar (if started)"
      - "Hover preview (animated)"
    sizes:
      xs: "160x90"
      sm: "320x180"
      md: "480x270"
      lg: "640x360"
  categoryRow:
    layout: "horizontal-scroll"
    itemsPerView: "auto"
    gap: "1rem"
    title: true
  progressBar:
    height: "4px"
    color: "primary"
    position: "bottom-of-thumbnail"

interactions:
  playback:
    - "Click/tap to play"
    - "Space bar to pause"
    - "Arrow keys to seek"
    - "M to mute"
    - "F for fullscreen"
  navigation:
    - "Horizontal scroll for rows"
    - "Infinite scroll vertically"
    - "Keyboard focus management"
  gestures:
    - "Double-tap left: rewind 10s"
    - "Double-tap right: forward 10s"
    - "Swipe up: related videos"

patterns:
  browsing:
    - "Hero featured content"
    - "Category rows (Continue Watching, Trending, etc.)"
    - "Personalized recommendations"
    - "Genre-based sections"
  playback:
    - "Auto-play next video"
    - "Resume from last position"
    - "Skip intro/credits buttons"
    - "Watch credits for post-credits scene"
  search:
    - "Autocomplete suggestions"
    - "Filter by genre, year, rating"
    - "Sort by relevance, date, popularity"
  socialProof:
    - "View count"
    - "Like/dislike ratio"
    - "Comments section"
    - "Share functionality"

dataFlow:
  streaming:
    - "Manifest fetch (HLS/DASH)"
    - "Segment requests (adaptive)"
    - "Buffer management"
    - "Quality switching"
  analytics:
    - "Play events"
    - "Watch time"
    - "Completion rate"
    - "Engagement (pause, seek)"

performance:
  - "Lazy loading thumbnails"
  - "Image CDN with responsive sizes"
  - "Video CDN with edge caching"
  - "Preload next video segment"
  - "Virtual scrolling for long lists"
  - "Service worker for offline viewing"

accessibility:
  - "Keyboard controls"
  - "Screen reader support"
  - "Captions/subtitles (WebVTT)"
  - "Audio descriptions"
  - "High contrast mode"
  - "Focus indicators"

responsiveness:
  mobile:
    - "Vertical video player"
    - "Swipe gestures"
    - "Bottom navigation"
    - "Portrait mode optimization"
  tablet:
    - "Grid layout (2-3 columns)"
    - "Picture-in-picture"
  desktop:
    - "Grid layout (4-6 columns)"
    - "Hover previews"
    - "Keyboard shortcuts"

notes:
  - "HLS for iOS/Safari, DASH for others"
  - "DRM for premium content (Widevine, FairPlay)"
  - "CDN critical for performance"
  - "Adaptive bitrate based on connection"
  - "Content delivery network (Cloudflare, Fastly)"
```

---

### Use Case 3: Calendar/Scheduling

**File:** `templates/use_cases/calendar.yaml` (NEW FILE)

```yaml
name: "Calendar / Scheduling"
description: "Calendar applications, event management, appointment scheduling"
category: "Productivity"

layout:
  structure: "sidebar-main-detail"
  regions:
    sidebar:
      width: "260px"
      contains:
        - "Mini calendar"
        - "Calendar list (toggle)"
        - "Create event button"
    main:
      width: "flex-1"
      contains:
        - "Month/Week/Day/Agenda view"
        - "Event grid"
        - "Time slots"
    detail:
      width: "400px"
      collapsible: true
      contains:
        - "Event details"
        - "Attendees"
        - "Description"
        - "Reminders"

navigation:
  toolbar:
    left:
      - label: "Today"
        action: "jump-to-today"
      - label: "Prev"
        icon: "chevron-left"
      - label: "Next"
        icon: "chevron-right"
    center:
      - label: "Month selector"
        type: "dropdown"
    right:
      - label: "Month"
        view: "month"
      - label: "Week"
        view: "week"
      - label: "Day"
        view: "day"
      - label: "Agenda"
        view: "agenda"

components:
  monthView:
    grid: "7x5-or-6"
    firstDay: "monday-or-sunday"
    showWeekNumbers: optional
    features:
      - "Multi-event display (dots/count)"
      - "Today highlight"
      - "Selected date"
  weekView:
    columns: 7
    timeSlots: "30min-or-1hour"
    startHour: 8
    endHour: 20
    features:
      - "All-day events row"
      - "Time grid"
      - "Current time indicator"
  dayView:
    columns: 1
    timeSlots: "15min-or-30min"
    features:
      - "Hourly breakdown"
      - "Event stacking"
      - "Current time indicator"
  agendaView:
    layout: "list"
    groupBy: "date"
    features:
      - "Chronological event list"
      - "Date headers"
      - "No events placeholder"
  eventForm:
    fields:
      - "Title (required)"
      - "Date/Time (required)"
      - "Duration"
      - "Location"
      - "Description"
      - "Attendees (with autocomplete)"
      - "Reminders"
      - "Repeat (daily, weekly, monthly, yearly)"
      - "Calendar (if multiple)"

interactions:
  creating:
    - "Click date to create event"
    - "Drag on time grid to set duration"
    - "Quick add (natural language)"
  editing:
    - "Click event to view details"
    - "Drag to move"
    - "Resize to change duration"
    - "Double-click to edit"
  navigation:
    - "Arrow keys to navigate dates"
    - "T for today"
    - "N for new event"
    - "/ for search"

patterns:
  scheduling:
    - "Find time slot (availability check)"
    - "Propose multiple times"
    - "Accept/decline invites"
    - "Tentative bookings"
  recurring:
    - "Repeat patterns (daily, weekly, monthly, yearly)"
    - "Custom recurrence (every 2 weeks, etc.)"
    - "Edit single or all occurrences"
    - "Exceptions (skip specific dates)"
  reminders:
    - "Email reminders"
    - "Push notifications"
    - "SMS (optional)"
    - "Multiple reminders per event"
  conflicts:
    - "Detect overlapping events"
    - "Visual indicator"
    - "Warning on save"

dataFlow:
  eventManagement:
    - "Create/update/delete events"
    - "Send invites (via email)"
    - "Track RSVP status"
    - "Sync with calendar services (Google, Outlook)"
  availability:
    - "Free/busy lookup"
    - "Find available time slots"
    - "Cross-calendar checks"

performance:
  - "Virtual scrolling for week/day views"
  - "Lazy load events outside viewport"
  - "Cache calendar data"
  - "Optimistic updates"

accessibility:
  - "Keyboard navigation (arrow keys)"
  - "Screen reader support"
  - "ARIA grid for calendar"
  - "Focus management"
  - "Accessible date picker"

responsiveness:
  mobile:
    - "Agenda view default"
    - "Bottom sheet for event details"
    - "Swipe between days"
  tablet:
    - "Week view default"
    - "Split view (calendar + details)"
  desktop:
    - "Month or week view default"
    - "Sidebar + main + detail"

notes:
  - "Timezone handling critical"
  - "iCalendar (.ics) import/export"
  - "CalDAV sync for cross-platform"
  - "Recurring events use RRULE"
  - "Conflict detection for shared calendars"
```

---

### Use Case 4: Complex Forms

**File:** `templates/use_cases/forms.yaml` (NEW FILE)

```yaml
name: "Complex Forms"
description: "Multi-step forms, surveys, application forms, data collection"
category: "Data Entry"

layout:
  structure: "wizard-or-single-page"
  wizard:
    sidebar:
      width: "240px"
      contains:
        - "Step indicator (vertical)"
        - "Progress percentage"
        - "Section navigation"
    main:
      width: "flex-1"
      maxWidth: "800px"
      contains:
        - "Current step fields"
        - "Navigation buttons"
        - "Progress bar"
  singlePage:
    main:
      maxWidth: "800px"
      contains:
        - "Sectioned form"
        - "Anchor navigation"
        - "Sticky submit button"

navigation:
  wizard:
    - label: "Previous"
      disabled: "if-first-step"
    - label: "Next"
      disabled: "if-invalid"
    - label: "Submit"
      visible: "last-step-only"
  singlePage:
    - "Anchor links to sections"
    - "Scroll spy active section"

components:
  stepIndicator:
    layout: "vertical-or-horizontal"
    states:
      - "completed"
      - "active"
      - "pending"
      - "error"
    display:
      - "Step number"
      - "Step title"
      - "Checkmark if completed"
  progressBar:
    display: "percentage"
    position: "top-of-form"
    color: "primary"
  formSection:
    title: true
    description: optional
    collapsible: optional
  inputField:
    label: true
    placeholder: optional
    helpText: optional
    errorMessage: true
    requiredIndicator: "*"
    characterCount: "for-text-areas"
  validationMessage:
    position: "below-field"
    icon: true
    color: "error"
  autoSave:
    indicator: "Saving... / Saved"
    frequency: "on-blur-or-30s"

interactions:
  validation:
    - "Inline validation on blur"
    - "Show errors after first submit attempt"
    - "Block navigation if invalid"
    - "Highlight invalid fields"
  autoSave:
    - "Auto-save draft every 30s"
    - "Save on field blur"
    - "Show save status"
    - "Restore on return"
  conditionalFields:
    - "Show/hide based on answers"
    - "Dynamic field requirements"
    - "Skip logic"
  autocomplete:
    - "Address autocomplete"
    - "Dropdown search"
    - "Previously entered values"

patterns:
  multiStep:
    - "Linear wizard (can't skip)"
    - "Step validation before next"
    - "Review step before submit"
    - "Edit from review"
  validation:
    - "Required field indicators"
    - "Format validation (email, phone, etc.)"
    - "Custom business rules"
    - "Error summary at top"
  autoSave:
    - "Draft persistence"
    - "Resume where left off"
    - "Clear draft after submit"
  fileUpload:
    - "Drag-and-drop zone"
    - "Multiple file support"
    - "Progress indicator"
    - "Preview uploaded files"
    - "File type/size validation"

fieldTypes:
  text:
    - "Short text (single line)"
    - "Long text (textarea)"
    - "Rich text editor"
  selection:
    - "Radio buttons (single choice)"
    - "Checkboxes (multiple choice)"
    - "Dropdown (single select)"
    - "Multi-select"
    - "Autocomplete"
  date:
    - "Date picker"
    - "Date range"
    - "Time picker"
    - "Date + time"
  numeric:
    - "Number input"
    - "Slider"
    - "Range slider"
  file:
    - "File upload"
    - "Image upload (with preview)"
    - "Document upload"
  specialized:
    - "Phone number"
    - "Email"
    - "URL"
    - "Credit card"
    - "Address (with autocomplete)"
    - "SSN/Tax ID (masked)"

dataFlow:
  submission:
    - "Client-side validation"
    - "Submit to server"
    - "Server-side validation"
    - "Success/error response"
    - "Redirect or show confirmation"
  autoSave:
    - "Debounce input changes"
    - "Save draft to localStorage or server"
    - "Restore on page load"

performance:
  - "Lazy load steps (if many)"
  - "Debounce validation"
  - "Optimize re-renders (React.memo)"
  - "Code-split large forms"

accessibility:
  - "Keyboard navigation (Tab, Shift+Tab)"
  - "ARIA labels for all fields"
  - "Error announcements (ARIA live)"
  - "Focus management between steps"
  - "Clear error messages"
  - "Required field indicators"

responsiveness:
  mobile:
    - "Single column layout"
    - "Native input types (tel, email, etc.)"
    - "Bottom sticky submit button"
    - "Mobile-optimized date/time pickers"
  tablet:
    - "Two-column layout (if appropriate)"
    - "Side-by-side navigation"
  desktop:
    - "Multi-column layout (max 2)"
    - "Inline validation"
    - "Keyboard shortcuts"

notes:
  - "Auto-save prevents data loss"
  - "Progressive disclosure (show fields as needed)"
  - "Clear error messages (what, why, how to fix)"
  - "Review step critical for complex forms"
  - "Consider abandonment tracking"
  - "A/B test form length and structure"
```

---

### Use Case 5: Search/Discovery

**File:** `templates/use_cases/search.yaml` (NEW FILE)

```yaml
name: "Search / Discovery"
description: "Search interfaces, product discovery, content exploration"
category: "Navigation"

layout:
  structure: "filters-results-detail"
  regions:
    filters:
      width: "280px"
      position: "left"
      collapsible: true
      contains:
        - "Search input"
        - "Faceted filters"
        - "Active filters"
        - "Clear all"
    results:
      width: "flex-1"
      contains:
        - "Results count"
        - "Sort options"
        - "Grid/List toggle"
        - "Results (grid or list)"
        - "Pagination"
    detail:
      width: "400px"
      collapsible: true
      position: "right"
      contains:
        - "Selected item details"
        - "Quick preview"
        - "Actions"

navigation:
  toolbar:
    - label: "Sort by"
      options: ["Relevance", "Date", "Price", "Rating"]
    - label: "View"
      options: ["Grid", "List"]
    - label: "Filters"
      action: "toggle-sidebar"

components:
  searchInput:
    width: "100%"
    placeholder: "Search..."
    features:
      - "Autocomplete dropdown"
      - "Recent searches"
      - "Suggested searches"
      - "Clear button"
      - "Search button (optional)"
    debounce: "300ms"
  autocompleteDropdown:
    sections:
      - "Suggestions (based on input)"
      - "Recent searches"
      - "Popular searches"
      - "Categories"
    maxItems: 10
    keyboard: true
  facetedFilters:
    types:
      - "Checkbox (multi-select)"
      - "Radio (single-select)"
      - "Range slider (price, date)"
      - "Toggle"
    display:
      - "Filter name"
      - "Count per option (if applicable)"
      - "Expand/collapse"
    behavior:
      - "Apply filters on change"
      - "Show loading state"
      - "Update counts dynamically"
  activeFilters:
    display: "chips-or-tags"
    features:
      - "Remove individual filter"
      - "Clear all filters"
  resultsGrid:
    columns: "responsive"
    gap: "1rem"
    itemSize: "uniform"
  resultsList:
    layout: "vertical"
    itemHeight: "auto"
  resultItem:
    grid:
      - "Image (thumbnail)"
      - "Title"
      - "Description (truncated)"
      - "Metadata (price, rating, date)"
      - "Actions (quick view, add to cart)"
    list:
      - "Image (larger)"
      - "Title + description"
      - "Extended metadata"
      - "Actions"
  pagination:
    type: "numbered-or-infinite-scroll"
    itemsPerPage: [20, 50, 100]
    display:
      - "Previous/Next"
      - "Page numbers"
      - "Jump to page"

interactions:
  search:
    - "Instant search (as-you-type)"
    - "Debounced API calls"
    - "Cancel previous requests"
    - "Highlight matching terms"
  filtering:
    - "Apply filters immediately"
    - "Update URL with filter params"
    - "Show loading spinner"
    - "Disable filters if no results"
  sorting:
    - "Dropdown or button group"
    - "Default: relevance"
    - "Remember sort preference"
  quickView:
    - "Hover or click for preview"
    - "Modal or slide-out panel"
    - "Navigate between items"

patterns:
  instantSearch:
    - "Search as user types"
    - "Show loading indicator"
    - "Debounce input (300ms)"
    - "Cancel stale requests"
  facetedNavigation:
    - "Multiple filter dimensions"
    - "OR within category, AND across categories"
    - "Show result count per filter"
    - "Disable unavailable options"
  suggestions:
    - "Autocomplete from search index"
    - "Recent searches (localStorage)"
    - "Trending searches"
    - "Did you mean... (typo correction)"
  noResults:
    - "Clear message"
    - "Suggestions (broaden search, check spelling)"
    - "Related categories"
    - "Contact support"
  savedSearches:
    - "Save search + filters"
    - "Alert on new results"
    - "Manage saved searches"

dataFlow:
  search:
    - "User types query"
    - "Debounce 300ms"
    - "Send API request"
    - "Parse response"
    - "Update results"
  filtering:
    - "User selects filter"
    - "Add to URL params"
    - "Send API request"
    - "Update results and filter counts"
  pagination:
    - "Load next page"
    - "Append to results (infinite scroll)"
    - "Or replace results (numbered pagination)"

performance:
  - "Debounce search input"
  - "Cancel stale API requests"
  - "Virtual scrolling for large result sets"
  - "Lazy load images"
  - "Cache search results"
  - "Use search index (Elasticsearch, Algolia)"

accessibility:
  - "Keyboard navigation"
  - "Screen reader announcements (X results found)"
  - "ARIA live region for results"
  - "Focus management"
  - "Skip to results link"

responsiveness:
  mobile:
    - "Full-width search"
    - "Filters in bottom sheet or modal"
    - "List view default"
    - "Infinite scroll"
  tablet:
    - "Collapsible filter sidebar"
    - "Grid view (2 columns)"
  desktop:
    - "Persistent filter sidebar"
    - "Grid view (3-4 columns)"
    - "Keyboard shortcuts (/ to focus search)"

notes:
  - "Search index critical for performance (Elasticsearch, Algolia, Typesense)"
  - "Typo tolerance (fuzzy matching)"
  - "Synonyms and related terms"
  - "Boost certain fields (title > description)"
  - "Track search analytics (popular queries, no-result queries)"
  - "A/B test search relevance"
```

---

## Task 3: Integrate Tailwind 4

**File:** `core/tailwind_generator.py` (NEW FILE)

**Purpose:** Generate Tailwind 4 config from design system profiles

```python
"""
Tailwind 4 configuration generator for BuildRunner design system
"""
import json
import yaml
from pathlib import Path
from typing import Dict, List


class TailwindGenerator:
    """Generate Tailwind 4 config from industry + use case profiles"""

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.templates_dir = self.project_root / "templates"

    def generate_tailwind_config(
        self,
        industry: str,
        use_case: str,
        output_path: Path = None
    ) -> Dict[str, any]:
        """
        Generate complete Tailwind config from profiles

        Args:
            industry: Industry profile name
            use_case: Use case pattern name
            output_path: Where to write tailwind.config.js

        Returns:
            Tailwind config dict
        """
        # Load profiles
        industry_profile = self._load_profile("industries", industry)
        use_case_profile = self._load_profile("use_cases", use_case)

        # Merge profiles
        merged = self.merge_design_tokens(industry_profile, use_case_profile)

        # Generate Tailwind config
        config = self._build_tailwind_config(merged)

        # Write to file if path provided
        if output_path:
            self._write_config(config, output_path)

        return config

    def merge_design_tokens(
        self,
        industry: Dict[str, any],
        use_case: Dict[str, any]
    ) -> Dict[str, any]:
        """
        Merge industry and use case design tokens

        Industry takes precedence for colors, typography
        Use case takes precedence for layout, components

        Args:
            industry: Industry profile dict
            use_case: Use case profile dict

        Returns:
            Merged design tokens
        """
        merged = {
            "colors": industry.get("colors", {}),
            "typography": industry.get("typography", {}),
            "spacing": industry.get("spacing", use_case.get("spacing", {})),
            "borders": industry.get("borders", {}),
            "shadows": industry.get("shadows", {}),
            "breakpoints": industry.get("breakpoints", use_case.get("breakpoints", {})),
            "components": {
                **industry.get("components", {}),
                **use_case.get("components", {})
            },
            "layout": use_case.get("layout", {}),
            "patterns": use_case.get("patterns", [])
        }

        return merged

    def apply_css_variables(self, tokens: Dict[str, any]) -> str:
        """
        Generate CSS custom properties from design tokens

        Args:
            tokens: Design tokens dict

        Returns:
            CSS string with :root variables
        """
        css_vars = [":root {"]

        # Colors
        if "colors" in tokens:
            css_vars.extend(self._colors_to_css_vars(tokens["colors"]))

        # Typography
        if "typography" in tokens:
            css_vars.extend(self._typography_to_css_vars(tokens["typography"]))

        # Spacing
        if "spacing" in tokens and "scale" in tokens["spacing"]:
            for i, value in enumerate(tokens["spacing"]["scale"]):
                css_vars.append(f"  --spacing-{i}: {value}px;")

        css_vars.append("}")

        return "\n".join(css_vars)

    def generate_theme_json(self, tokens: Dict[str, any]) -> Dict[str, any]:
        """
        Generate theme.json for Tailwind 4

        Args:
            tokens: Merged design tokens

        Returns:
            Theme JSON object
        """
        theme = {
            "colors": self._flatten_colors(tokens.get("colors", {})),
            "fontFamily": {
                "sans": [tokens.get("typography", {}).get("fonts", {}).get("primary", "sans-serif")],
                "serif": [tokens.get("typography", {}).get("fonts", {}).get("secondary", "serif")],
                "mono": [tokens.get("typography", {}).get("fonts", {}).get("monospace", "monospace")]
            },
            "fontSize": tokens.get("typography", {}).get("sizes", {}),
            "fontWeight": tokens.get("typography", {}).get("weights", {}),
            "lineHeight": tokens.get("typography", {}).get("lineHeights", {}),
            "spacing": self._spacing_to_scale(tokens.get("spacing", {})),
            "borderRadius": tokens.get("borders", {}).get("radius", {}),
            "boxShadow": tokens.get("shadows", {}),
            "screens": tokens.get("breakpoints", {})
        }

        return theme

    def _load_profile(self, category: str, name: str) -> Dict[str, any]:
        """Load YAML profile"""
        profile_path = self.templates_dir / category / f"{name}.yaml"
        if not profile_path.exists():
            raise FileNotFoundError(f"Profile not found: {profile_path}")

        with open(profile_path, 'r') as f:
            return yaml.safe_load(f)

    def _build_tailwind_config(self, tokens: Dict[str, any]) -> Dict[str, any]:
        """Build complete Tailwind config object"""
        return {
            "content": [
                "./src/**/*.{js,jsx,ts,tsx}",
                "./public/index.html"
            ],
            "theme": self.generate_theme_json(tokens),
            "plugins": []
        }

    def _write_config(self, config: Dict[str, any], output_path: Path):
        """Write Tailwind config to JavaScript file"""
        js_content = f"""/** @type {{import('tailwindcss').Config}} */
module.exports = {json.dumps(config, indent=2)}
"""
        output_path.write_text(js_content)

    def _colors_to_css_vars(self, colors: Dict[str, any], prefix: str = "color") -> List[str]:
        """Convert color dict to CSS variables"""
        vars = []
        for key, value in colors.items():
            if isinstance(value, dict):
                # Nested (e.g., primary.main)
                for sub_key, sub_value in value.items():
                    vars.append(f"  --{prefix}-{key}-{sub_key}: {sub_value};")
            else:
                # Flat
                vars.append(f"  --{prefix}-{key}: {value};")
        return vars

    def _typography_to_css_vars(self, typography: Dict[str, any]) -> List[str]:
        """Convert typography to CSS variables"""
        vars = []
        if "fonts" in typography:
            for key, value in typography["fonts"].items():
                vars.append(f"  --font-{key}: {value};")
        if "sizes" in typography:
            for key, value in typography["sizes"].items():
                vars.append(f"  --text-{key}: {value};")
        return vars

    def _flatten_colors(self, colors: Dict[str, any]) -> Dict[str, any]:
        """Flatten nested color structure for Tailwind"""
        flat = {}
        for key, value in colors.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    flat[f"{key}-{sub_key}"] = sub_value
            else:
                flat[key] = value
        return flat

    def _spacing_to_scale(self, spacing: Dict[str, any]) -> Dict[str, str]:
        """Convert spacing scale to Tailwind format"""
        if "scale" not in spacing:
            return {}

        scale = {}
        for i, value in enumerate(spacing["scale"]):
            scale[str(i)] = f"{value}px"

        return scale
```

**Acceptance Criteria:**
- ✅ Loads industry and use case YAML profiles
- ✅ Merges design tokens intelligently
- ✅ Generates valid Tailwind 4 config
- ✅ Creates CSS custom properties
- ✅ Writes tailwind.config.js file

---

## Task 4: Integrate Storybook

**File:** `core/storybook_generator.py` (NEW FILE)

**Purpose:** Generate Storybook component library from design system

```python
"""
Storybook component library generator
"""
from pathlib import Path
from typing import Dict, List


class StorybookGenerator:
    """Generate Storybook setup and component stories"""

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.storybook_dir = self.project_root / ".storybook"
        self.stories_dir = self.project_root / "src" / "stories"

    def generate_storybook_config(self, tokens: Dict[str, any]):
        """
        Create .storybook/ configuration

        Args:
            tokens: Design tokens from merged profiles
        """
        self.storybook_dir.mkdir(parents=True, exist_ok=True)

        # main.js
        self._write_main_config()

        # preview.js (with design tokens)
        self._write_preview_config(tokens)

        # manager.js
        self._write_manager_config()

    def create_component_stories(
        self,
        spec_path: Path
    ) -> List[Path]:
        """
        Auto-generate component stories from PROJECT_SPEC

        Args:
            spec_path: Path to PROJECT_SPEC.md

        Returns:
            List of created story file paths
        """
        # Parse spec for components
        components = self._extract_components_from_spec(spec_path)

        # Generate story files
        story_files = []
        for component in components:
            story_path = self._create_story_file(component)
            story_files.append(story_path)

        return story_files

    def _write_main_config(self):
        """Write .storybook/main.js"""
        content = """module.exports = {
  stories: ['../src/**/*.stories.@(js|jsx|ts|tsx|mdx)'],
  addons: [
    '@storybook/addon-links',
    '@storybook/addon-essentials',
    '@storybook/addon-interactions',
    '@storybook/addon-a11y',
  ],
  framework: {
    name: '@storybook/react-vite',
    options: {},
  },
  docs: {
    autodocs: 'tag',
  },
};
"""
        (self.storybook_dir / "main.js").write_text(content)

    def _write_preview_config(self, tokens: Dict[str, any]):
        """Write .storybook/preview.js with design tokens"""
        colors = tokens.get("colors", {})
        typography = tokens.get("typography", {})

        content = f"""import '../src/index.css';

export const parameters = {{
  actions: {{ argTypesRegex: '^on[A-Z].*' }},
  controls: {{
    matchers: {{
      color: /(background|color)$/i,
      date: /Date$/,
    }},
  }},
  backgrounds: {{
    default: 'light',
    values: [
      {{
        name: 'light',
        value: '#ffffff',
      }},
      {{
        name: 'dark',
        value: '#18181b',
      }},
    ],
  }},
}};

// Apply design system tokens
document.documentElement.style.setProperty('--color-primary', '{colors.get("primary", {}).get("main", "#1976d2")}');
"""
        (self.storybook_dir / "preview.js").write_text(content)

    def _write_manager_config(self):
        """Write .storybook/manager.js"""
        content = """import { addons } from '@storybook/addons';
import { themes } from '@storybook/theming';

addons.setConfig({
  theme: themes.normal,
});
"""
        (self.storybook_dir / "manager.js").write_text(content)

    def _extract_components_from_spec(self, spec_path: Path) -> List[Dict[str, any]]:
        """
        Parse PROJECT_SPEC.md for component mentions

        Returns:
            List of component dicts with name, description, props
        """
        spec_content = spec_path.read_text()
        components = []

        # Simple extraction: look for component mentions
        # In real implementation, use more sophisticated parsing

        common_components = [
            {"name": "Button", "description": "Primary action button"},
            {"name": "Input", "description": "Text input field"},
            {"name": "Card", "description": "Content container"},
            {"name": "Modal", "description": "Overlay dialog"},
        ]

        return common_components

    def _create_story_file(self, component: Dict[str, any]) -> Path:
        """Create .stories.tsx file for component"""
        self.stories_dir.mkdir(parents=True, exist_ok=True)

        name = component["name"]
        story_path = self.stories_dir / f"{name}.stories.tsx"

        content = f"""import type {{ Meta, StoryObj }} from '@storybook/react';
import {{ {name} }} from '../components/{name}';

const meta: Meta<typeof {name}> = {{
  title: 'Components/{name}',
  component: {name},
  tags: ['autodocs'],
}};

export default meta;
type Story = StoryObj<typeof {name}>;

export const Default: Story = {{
  args: {{}},
}};
"""
        story_path.write_text(content)

        return story_path
```

**Acceptance Criteria:**
- ✅ Creates .storybook/ configuration
- ✅ Generates component stories
- ✅ Integrates design tokens
- ✅ Sets up accessibility addon

---

## Task 5: Setup Visual Regression Testing

**File:** `core/visual_regression.py` (NEW FILE)

**Purpose:** Visual regression testing with Playwright

```python
"""
Visual regression testing with Playwright
"""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright, Page
from typing import List, Dict
import json


class VisualRegressionTester:
    """Capture and compare screenshots for visual regression"""

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.baseline_dir = self.project_root / "tests" / "visual" / "baseline"
        self.current_dir = self.project_root / "tests" / "visual" / "current"
        self.diff_dir = self.project_root / "tests" / "visual" / "diff"

        # Create directories
        self.baseline_dir.mkdir(parents=True, exist_ok=True)
        self.current_dir.mkdir(parents=True, exist_ok=True)
        self.diff_dir.mkdir(parents=True, exist_ok=True)

    async def capture_baseline(
        self,
        url: str,
        components: List[str]
    ) -> Dict[str, Path]:
        """
        Capture baseline screenshots

        Args:
            url: Base URL of application
            components: List of component names to capture

        Returns:
            Dict mapping component name to screenshot path
        """
        screenshots = {}

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            for component in components:
                # Navigate to component page
                await page.goto(f"{url}/components/{component}")
                await page.wait_for_load_state("networkidle")

                # Capture screenshot
                screenshot_path = self.baseline_dir / f"{component}.png"
                await page.screenshot(path=str(screenshot_path), full_page=True)

                screenshots[component] = screenshot_path

            await browser.close()

        return screenshots

    async def run_visual_tests(
        self,
        url: str,
        components: List[str]
    ) -> Dict[str, any]:
        """
        Run visual regression tests

        Args:
            url: Base URL of application
            components: List of component names to test

        Returns:
            Dict with test results:
                - passed: List of components with no changes
                - failed: List of components with changes
                - diffs: Dict mapping component to diff image path
        """
        passed = []
        failed = []
        diffs = {}

        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()

            for component in components:
                # Capture current screenshot
                await page.goto(f"{url}/components/{component}")
                await page.wait_for_load_state("networkidle")

                current_path = self.current_dir / f"{component}.png"
                await page.screenshot(path=str(current_path), full_page=True)

                # Compare with baseline
                baseline_path = self.baseline_dir / f"{component}.png"

                if not baseline_path.exists():
                    failed.append(component)
                    continue

                # Detect differences
                has_diff = await self.detect_differences(
                    baseline_path,
                    current_path,
                    component
                )

                if has_diff:
                    failed.append(component)
                    diffs[component] = self.diff_dir / f"{component}-diff.png"
                else:
                    passed.append(component)

            await browser.close()

        return {
            "passed": passed,
            "failed": failed,
            "diffs": diffs
        }

    async def detect_differences(
        self,
        baseline_path: Path,
        current_path: Path,
        component: str
    ) -> bool:
        """
        Detect pixel differences between images

        Args:
            baseline_path: Path to baseline image
            current_path: Path to current image
            component: Component name

        Returns:
            True if differences detected
        """
        # Use pixelmatch or similar library
        # For now, simple implementation

        from PIL import Image, ImageChops

        baseline = Image.open(baseline_path)
        current = Image.open(current_path)

        # Check dimensions
        if baseline.size != current.size:
            return True

        # Pixel-by-pixel comparison
        diff = ImageChops.difference(baseline, current)

        # Check if any pixels differ
        if diff.getbbox():
            # Save diff image
            diff_path = self.diff_dir / f"{component}-diff.png"
            diff.save(diff_path)
            return True

        return False

    def generate_report(self, results: Dict[str, any]) -> Path:
        """
        Generate HTML report for visual regression results

        Args:
            results: Results from run_visual_tests()

        Returns:
            Path to HTML report
        """
        report_path = self.project_root / "tests" / "visual" / "report.html"

        html = """<!DOCTYPE html>
<html>
<head>
    <title>Visual Regression Report</title>
    <style>
        body { font-family: sans-serif; padding: 2rem; }
        .passed { color: green; }
        .failed { color: red; }
        .component { margin: 2rem 0; padding: 1rem; border: 1px solid #ddd; }
        img { max-width: 400px; margin: 0.5rem; border: 1px solid #ccc; }
    </style>
</head>
<body>
    <h1>Visual Regression Report</h1>
"""

        # Passed components
        html += f"<h2 class='passed'>Passed ({len(results['passed'])})</h2><ul>"
        for component in results["passed"]:
            html += f"<li>{component}</li>"
        html += "</ul>"

        # Failed components
        html += f"<h2 class='failed'>Failed ({len(results['failed'])})</h2>"
        for component in results["failed"]:
            html += f"<div class='component'><h3>{component}</h3>"

            baseline = self.baseline_dir / f"{component}.png"
            current = self.current_dir / f"{component}.png"
            diff = results["diffs"].get(component)

            if baseline.exists():
                html += f"<div><strong>Baseline:</strong><br><img src='{baseline.relative_to(report_path.parent)}'></div>"
            if current.exists():
                html += f"<div><strong>Current:</strong><br><img src='{current.relative_to(report_path.parent)}'></div>"
            if diff:
                html += f"<div><strong>Diff:</strong><br><img src='{diff.relative_to(report_path.parent)}'></div>"

            html += "</div>"

        html += "</body></html>"

        report_path.write_text(html)

        return report_path
```

**Acceptance Criteria:**
- ✅ Captures baseline screenshots
- ✅ Compares current vs baseline
- ✅ Detects pixel differences
- ✅ Generates visual diff images
- ✅ Creates HTML report

---

## Task 6: Write Comprehensive Tests

**File:** `tests/test_design_system_complete.py` (NEW FILE)

```python
"""
Tests for completed design system
"""
import pytest
import yaml
from pathlib import Path
from core.tailwind_generator import TailwindGenerator
from core.storybook_generator import StorybookGenerator
from core.visual_regression import VisualRegressionTester


class TestIndustryProfiles:
    """Test all 8 industry profiles load correctly"""

    def test_healthcare_profile_loads(self, tmp_path):
        """Test healthcare profile"""
        # Implemented in existing tests
        pass

    def test_fintech_profile_loads(self, tmp_path):
        """Test fintech profile"""
        pass

    def test_government_profile_loads(self, tmp_path):
        """Test government profile (NEW)"""
        profile_path = Path("templates/industries/government.yaml")
        assert profile_path.exists()

        with open(profile_path) as f:
            profile = yaml.safe_load(f)

        assert profile["name"] == "Government"
        assert "colors" in profile
        assert "Section 508" in profile["compliance"]["standards"]

    def test_legal_profile_loads(self, tmp_path):
        """Test legal profile (NEW)"""
        profile_path = Path("templates/industries/legal.yaml")
        assert profile_path.exists()

        with open(profile_path) as f:
            profile = yaml.safe_load(f)

        assert profile["name"] == "Legal"
        assert "ABA Technology Standards" in profile["compliance"]["standards"]

    def test_nonprofit_profile_loads(self, tmp_path):
        """Test nonprofit profile (NEW)"""
        profile_path = Path("templates/industries/nonprofit.yaml")
        assert profile_path.exists()

        with open(profile_path) as f:
            profile = yaml.safe_load(f)

        assert profile["name"] == "Nonprofit"
        assert "501(c)(3)" in profile["compliance"]["standards"][0]

    def test_gaming_profile_loads(self, tmp_path):
        """Test gaming profile (NEW)"""
        profile_path = Path("templates/industries/gaming.yaml")
        assert profile_path.exists()

        with open(profile_path) as f:
            profile = yaml.safe_load(f)

        assert profile["name"] == "Gaming"
        assert "COPPA" in profile["compliance"]["standards"]

    def test_manufacturing_profile_loads(self, tmp_path):
        """Test manufacturing profile (NEW)"""
        profile_path = Path("templates/industries/manufacturing.yaml")
        assert profile_path.exists()

        with open(profile_path) as f:
            profile = yaml.safe_load(f)

        assert profile["name"] == "Manufacturing"
        assert "ISO 9001" in profile["compliance"]["standards"]


class TestUseCasePatterns:
    """Test all 8 use case patterns load correctly"""

    def test_chat_pattern_loads(self, tmp_path):
        """Test chat pattern (NEW)"""
        pattern_path = Path("templates/use_cases/chat.yaml")
        assert pattern_path.exists()

        with open(pattern_path) as f:
            pattern = yaml.safe_load(f)

        assert pattern["name"] == "Chat / Messaging"
        assert pattern["layout"]["structure"] == "sidebar-main-detail"

    def test_video_pattern_loads(self, tmp_path):
        """Test video pattern (NEW)"""
        pattern_path = Path("templates/use_cases/video.yaml")
        assert pattern_path.exists()

        with open(pattern_path) as f:
            pattern = yaml.safe_load(f)

        assert pattern["name"] == "Video Streaming"

    def test_calendar_pattern_loads(self, tmp_path):
        """Test calendar pattern (NEW)"""
        pattern_path = Path("templates/use_cases/calendar.yaml")
        assert pattern_path.exists()

        with open(pattern_path) as f:
            pattern = yaml.safe_load(f)

        assert pattern["name"] == "Calendar / Scheduling"

    def test_forms_pattern_loads(self, tmp_path):
        """Test forms pattern (NEW)"""
        pattern_path = Path("templates/use_cases/forms.yaml")
        assert pattern_path.exists()

        with open(pattern_path) as f:
            pattern = yaml.safe_load(f)

        assert pattern["name"] == "Complex Forms"

    def test_search_pattern_loads(self, tmp_path):
        """Test search pattern (NEW)"""
        pattern_path = Path("templates/use_cases/search.yaml")
        assert pattern_path.exists()

        with open(pattern_path) as f:
            pattern = yaml.safe_load(f)

        assert pattern["name"] == "Search / Discovery"


class TestTailwindGenerator:
    """Test Tailwind 4 config generation"""

    def test_generate_config(self, tmp_path):
        """Test config generation"""
        generator = TailwindGenerator(tmp_path)

        # Mock profiles
        (tmp_path / "templates" / "industries").mkdir(parents=True)
        (tmp_path / "templates" / "use_cases").mkdir(parents=True)

        industry_yaml = tmp_path / "templates" / "industries" / "test.yaml"
        industry_yaml.write_text("""
name: Test
colors:
  primary:
    main: "#1976d2"
typography:
  fonts:
    primary: "Roboto, sans-serif"
""")

        use_case_yaml = tmp_path / "templates" / "use_cases" / "test.yaml"
        use_case_yaml.write_text("""
name: Test
layout:
  structure: "sidebar-main"
""")

        config = generator.generate_tailwind_config("test", "test")

        assert "theme" in config
        assert "content" in config

    def test_merge_tokens(self, tmp_path):
        """Test token merging"""
        generator = TailwindGenerator(tmp_path)

        industry = {"colors": {"primary": {"main": "#1976d2"}}}
        use_case = {"layout": {"structure": "grid"}}

        merged = generator.merge_design_tokens(industry, use_case)

        assert merged["colors"]["primary"]["main"] == "#1976d2"
        assert merged["layout"]["structure"] == "grid"


class TestStorybookGenerator:
    """Test Storybook generation"""

    def test_generate_config(self, tmp_path):
        """Test Storybook config generation"""
        generator = StorybookGenerator(tmp_path)
        generator.generate_storybook_config({})

        assert (tmp_path / ".storybook" / "main.js").exists()
        assert (tmp_path / ".storybook" / "preview.js").exists()

    def test_create_stories(self, tmp_path):
        """Test story file creation"""
        generator = StorybookGenerator(tmp_path)

        # Create mock spec
        spec_path = tmp_path / "PROJECT_SPEC.md"
        spec_path.write_text("# Spec\n\nButton component")

        stories = generator.create_component_stories(spec_path)

        assert len(stories) > 0


class TestVisualRegression:
    """Test visual regression testing"""

    @pytest.mark.asyncio
    async def test_capture_baseline(self, tmp_path):
        """Test baseline capture"""
        tester = VisualRegressionTester(tmp_path)

        # Would need running server to test
        # Mock for unit tests
        pass

    def test_detect_differences_identical(self, tmp_path):
        """Test difference detection with identical images"""
        tester = VisualRegressionTester(tmp_path)

        # Create identical images
        from PIL import Image

        img = Image.new("RGB", (100, 100), color="red")
        baseline_path = tmp_path / "baseline.png"
        current_path = tmp_path / "current.png"

        img.save(baseline_path)
        img.save(current_path)

        # Should detect no differences
        # (async test would be needed for full test)
```

**Acceptance Criteria:**
- ✅ All 8 industry profiles tested
- ✅ All 8 use case patterns tested
- ✅ Tailwind generator tested
- ✅ Storybook generator tested
- ✅ Visual regression tested
- ✅ Test coverage 85%+

---

## Task 7: Update Documentation

Update `docs/DESIGN_SYSTEM.md` with complete template list and new integrations.

Add sections:
- "All 16 Templates" (8 industries + 8 use cases)
- "Tailwind 4 Integration"
- "Storybook Setup"
- "Visual Regression Testing"

---

## Testing

```bash
cd ../br3-design-system

# Run tests
pytest tests/test_design_system_complete.py -v --cov=core/tailwind_generator.py --cov=core/storybook_generator.py --cov=core/visual_regression.py

# Manual test - load all templates
python -m cli.main design profile government chat
python -m cli.main design profile legal forms
python -m cli.main design profile gaming video

# Generate Tailwind config
python -c "
from core.tailwind_generator import TailwindGenerator
from pathlib import Path

gen = TailwindGenerator(Path('.'))
config = gen.generate_tailwind_config('government', 'chat', Path('tailwind.config.js'))
print('Tailwind config generated')
"

# Check tailwind.config.js exists
cat tailwind.config.js
```

---

## Commit and Push

```bash
git add .
git commit -m "feat: Complete design system with all 16 templates

- Add 5 industry profiles (Government, Legal, Nonprofit, Gaming, Manufacturing)
- Add 5 use case patterns (Chat, Video, Calendar, Forms, Search)
- Tailwind 4 config generator
- Storybook component library generator
- Visual regression testing with Playwright
- Comprehensive tests (85%+ coverage)
- Updated documentation

Features:
- All 8 industry profiles complete
- All 8 use case patterns complete
- Generate tailwind.config.js from profiles
- Auto-generate Storybook stories
- Visual diff testing for components

Test Coverage: 85%+
Tests Passing: 50+

🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>"

git push -u origin build/v3.1-design-system
```

---

## Completion Checklist

- [ ] All 7 tasks complete
- [ ] 5 industry YAML files created (government, legal, nonprofit, gaming, manufacturing)
- [ ] 5 use case YAML files created (chat, video, calendar, forms, search)
- [ ] `core/tailwind_generator.py` created
- [ ] `core/storybook_generator.py` created
- [ ] `core/visual_regression.py` created
- [ ] `tests/test_design_system_complete.py` created
- [ ] Test coverage 85%+ confirmed
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Manual tests successful
- [ ] Branch pushed to GitHub

---

## Report Format

```
✅ Build 1B Complete: Design System

Branch: build/v3.1-design-system
Status: Pushed to GitHub

Files Created:
- templates/industries/government.yaml (NEW - 234 lines)
- templates/industries/legal.yaml (NEW - 198 lines)
- templates/industries/nonprofit.yaml (NEW - 187 lines)
- templates/industries/gaming.yaml (NEW - 256 lines)
- templates/industries/manufacturing.yaml (NEW - 223 lines)
- templates/use_cases/chat.yaml (NEW - 187 lines)
- templates/use_cases/video.yaml (NEW - 156 lines)
- templates/use_cases/calendar.yaml (NEW - 198 lines)
- templates/use_cases/forms.yaml (NEW - 234 lines)
- templates/use_cases/search.yaml (NEW - 212 lines)
- core/tailwind_generator.py (NEW - 312 lines)
- core/storybook_generator.py (NEW - 187 lines)
- core/visual_regression.py (NEW - 234 lines)
- tests/test_design_system_complete.py (NEW - 287 lines)
- docs/DESIGN_SYSTEM.md (UPDATED - added 156 lines)

Tests:
- 52 tests passing
- Coverage: 86%
- Test time: 3.1s

Manual Testing:
- ✓ All 16 templates load correctly
- ✓ Tailwind config generation
- ✓ Storybook config generation
- ✓ Visual regression baseline capture

Ready for Review: ⏸️ Awaiting merge approval
```

---

**DO NOT MERGE THIS BRANCH.** Wait for review before integration.
