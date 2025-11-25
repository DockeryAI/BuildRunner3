"""RLS Documentation Awareness for BR3

When BR3 encounters SQL or RLS issues, it automatically references
the comprehensive RLS documentation in the project.
"""

from pathlib import Path
from typing import List, Optional


class RLSDocumentationGuide:
    """Provides RLS documentation references for SQL/RLS issues"""

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.rls_docs = self._find_rls_docs()

    def _find_rls_docs(self) -> List[Path]:
        """Find all RLS documentation files"""
        docs = []

        # Primary RLS documentation directory
        rls_dir = self.project_root / "RLS Documentation"
        if rls_dir.exists():
            docs.extend(rls_dir.glob("*.md"))
            docs.extend(rls_dir.glob("*.sql"))

        # Root-level RLS files
        docs.extend(self.project_root.glob("*RLS*.md"))
        docs.extend(self.project_root.glob("*RLS*.sql"))
        docs.extend(self.project_root.glob("*rls*.sql"))

        return sorted(docs)

    def get_help_for_issue(self, issue_type: str) -> str:
        """Get relevant RLS documentation for a specific issue type"""

        if not self.rls_docs:
            return ""

        help_text = "\n📚 RLS Documentation Available:\n"

        # Map issue types to relevant docs
        relevant_docs = {
            "rls_policy": ["RLS_Encyclopedia", "DEFINITIVE_RLS_FIX"],
            "sql_injection": ["RLS_Troubleshooting", "PROPER_RLS_POLICIES"],
            "postgres": ["RLS_Encyclopedia", "Ultimate_RLS_Fix"],
            "supabase": ["RLS_CRITICAL_CORRECTIONS", "RLS_Challenge"]
        }

        # Get relevant docs for this issue
        keywords = relevant_docs.get(issue_type, ["RLS"])

        shown = []
        for doc in self.rls_docs:
            doc_name = doc.name
            if any(kw in doc_name for kw in keywords):
                rel_path = doc.relative_to(self.project_root)
                help_text += f"  • {rel_path}\n"
                shown.append(doc)

        # If no specific matches, show all
        if not shown and self.rls_docs:
            help_text += "\nAll RLS Documentation:\n"
            for doc in self.rls_docs[:5]:  # Show first 5
                rel_path = doc.relative_to(self.project_root)
                help_text += f"  • {rel_path}\n"

        help_text += "\n💡 BR3 will reference these docs when analyzing SQL/RLS issues\n"

        return help_text

    def get_rls_context(self) -> str:
        """Get full RLS context for Claude"""
        if not self.rls_docs:
            return ""

        context = "# RLS Documentation Context\n\n"
        context += f"This project has {len(self.rls_docs)} RLS documentation files:\n\n"

        for doc in self.rls_docs:
            rel_path = doc.relative_to(self.project_root)
            context += f"- {rel_path}\n"

        context += "\nWhen encountering SQL or RLS issues, refer to these docs.\n"
        context += "Key files:\n"
        context += "- RLS_Encyclopedia_Robust.md - Complete RLS reference\n"
        context += "- RLS_Troubleshooting_Guide.md - Common issues & fixes\n"
        context += "- PROPER_RLS_POLICIES.sql - Correct policy examples\n"

        return context


def inject_rls_awareness():
    """Inject RLS awareness into BR3 globally"""
    # This will be called on attach/init to make BR3 aware of RLS docs
    try:
        from pathlib import Path
        project_root = Path.cwd()

        guide = RLSDocumentationGuide(project_root)

        if guide.rls_docs:
            print("\n📚 RLS Documentation Detected")
            print("=" * 50)
            print(f"Found {len(guide.rls_docs)} RLS documentation files")
            print("\nBR3 will reference these when analyzing SQL/RLS issues:")
            for doc in guide.rls_docs[:3]:
                print(f"  ✓ {doc.name}")
            if len(guide.rls_docs) > 3:
                print(f"  ... and {len(guide.rls_docs) - 3} more")
            print()

            return guide
    except Exception:
        pass

    return None
