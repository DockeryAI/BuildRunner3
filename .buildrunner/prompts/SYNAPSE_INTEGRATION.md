# Worktree A: Synapse Integration (4-6 hours)

## Connection Info
- **Synapse Path**: `/Users/byronhudson/Projects/Synapse/src/data/`
- **NAICS Database**: `complete-naics-codes.ts` (400 codes, 140 with full profiles)
- **Profiles**: `industries/*.profile.ts` (5 TypeScript files)
- **Format**: TypeScript with psychology profiles, power words, themes

## Tasks

### 1. Create SynapseConnector (2 hours)
**File**: `core/design_system/synapse_connector.py`

```python
class SynapseConnector:
    """Connect to Synapse industry database"""

    def __init__(self, synapse_path: Path):
        self.synapse_path = Path(synapse_path)
        self.naics_file = synapse_path / "complete-naics-codes.ts"
        self.industries_dir = synapse_path / "industries"

    def load_naics_codes(self) -> List[Dict]:
        """Parse complete-naics-codes.ts, extract 140 profiles where has_full_profile: true"""

    def load_profile(self, naics_code: str) -> Dict:
        """Load full profile from industries/*.profile.ts, parse TypeScript"""

    def export_to_yaml(self, output_dir: Path) -> int:
        """Export all 140 profiles to YAML in templates/industries/"""
```

### 2. Export to templates/ (1 hour)
Create directory structure:
```
templates/industries/
├── restaurant/profile.yaml
├── msp/profile.yaml
... (140 total)
```

YAML format:
```yaml
id: restaurant
name: Restaurant
naics_code: "722511"
psychology:
  primary_triggers: [scarcity, social_proof]
  power_words: [fresh, authentic, local]
content_themes: [seasonal_menus, behind_scenes]
```

### 3. Create ProfileLoader (1 hour)
**File**: `core/design_system/profile_loader.py`

```python
class ProfileLoader:
    def load_profile(self, industry_id: str) -> IndustryProfile
    def list_available(self) -> List[str]  # Returns 140 industries
    def search(self, query: str) -> List[IndustryProfile]
```

### 4. CLI Commands (1 hour)
**File**: `cli/design_commands.py`

```python
@design_app.command("list")
def list_profiles():
    """List all 140 industry profiles"""

@design_app.command("profile")
def show_profile(industry: str):
    """Show industry profile with Rich formatting"""

@design_app.command("generate")
def generate_config(industry: str, use_case: str):
    """Generate tailwind.config.js for industry + use case"""
```

### 5. Tests (1 hour)
**File**: `tests/test_synapse_integration.py`

- Test SynapseConnector parses TypeScript
- Test profile export to YAML (140 files created)
- Test ProfileLoader loads from templates/
- Test CLI commands
- 90%+ coverage

## Acceptance Criteria
- [ ] SynapseConnector parses TypeScript files correctly
- [ ] All 140 profiles exported to templates/industries/
- [ ] `br design list` shows 140 industries
- [ ] `br design profile restaurant` displays full profile
- [ ] `br design generate restaurant dashboard` creates tailwind.config.js
- [ ] 90%+ test coverage
- [ ] `br quality check --threshold 85` passes

## Notes
- Parse TypeScript with regex (no need for full TS parser)
- Convert camelCase to snake_case for Python
- Use Rich for terminal output
- Follow existing patterns in core/routing/, core/security/
