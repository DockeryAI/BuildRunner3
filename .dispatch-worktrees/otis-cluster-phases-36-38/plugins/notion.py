"""
Notion Plugin for BuildRunner 3.0

Pushes STATUS.md to Notion and syncs documentation.
Because Notion is apparently where all the cool kids keep their docs now.
"""

import os
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path

try:
    from notion_client import Client

    NOTION_AVAILABLE = True
except ImportError:
    NOTION_AVAILABLE = False
    Client = None

from dotenv import load_dotenv


class NotionPlugin:
    """
    Notion integration plugin.

    Optional plugin - docs work fine in markdown without it.
    When enabled, syncs STATUS.md and docs to Notion for that sweet, sweet UI.
    """

    def __init__(self, token: Optional[str] = None, database_id: Optional[str] = None):
        """
        Initialize Notion plugin.

        Args:
            token: Notion integration token (or uses NOTION_TOKEN env var)
            database_id: Notion database ID (or uses NOTION_DATABASE_ID env var)
        """
        load_dotenv()

        self.enabled = NOTION_AVAILABLE
        self.token = token or os.getenv("NOTION_TOKEN")
        self.database_id = database_id or os.getenv("NOTION_DATABASE_ID")
        self.client: Optional[Any] = None

        if not NOTION_AVAILABLE:
            print("ℹ️  Notion plugin disabled: notion-client not installed")
            print("   Install with: pip install notion-client")
            return

        if not self.token:
            print("ℹ️  Notion plugin disabled: NOTION_TOKEN not set")
            print("   Create integration at https://www.notion.so/my-integrations")
            self.enabled = False
            return

        if not self.database_id:
            print("ℹ️  Notion plugin disabled: NOTION_DATABASE_ID not set")
            print("   Set database ID: export NOTION_DATABASE_ID=xxxxx")
            self.enabled = False
            return

        try:
            self.client = Client(auth=self.token)
            # Test connection
            self.client.databases.retrieve(database_id=self.database_id)
            print(f"✅ Notion plugin enabled")
        except Exception as e:
            print(f"⚠️  Notion plugin initialization failed: {e}")
            self.enabled = False

    def is_enabled(self) -> bool:
        """Check if plugin is enabled and configured"""
        return self.enabled and self.client is not None

    def push_status(self, status_file: Path) -> bool:
        """
        Push STATUS.md to Notion.

        Args:
            status_file: Path to STATUS.md file

        Returns:
            True if successful
        """
        if not self.is_enabled():
            print("Notion plugin not enabled - skipping status push")
            return False

        if not status_file.exists():
            print(f"⚠️  Status file not found: {status_file}")
            return False

        try:
            # Read STATUS.md
            with open(status_file, "r") as f:
                content = f.read()

            # Parse status content
            title = "BuildRunner Status"
            if content.startswith("# "):
                first_line = content.split("\n")[0]
                title = first_line.replace("# ", "").strip()

            # Convert markdown to Notion blocks
            blocks = self._markdown_to_blocks(content)

            # Check if page exists
            page_id = self._find_status_page()

            if page_id:
                # Update existing page
                self.client.blocks.children.append(block_id=page_id, children=blocks)
                print(f"✅ Updated Notion status page")
            else:
                # Create new page
                self.client.pages.create(
                    parent={"database_id": self.database_id},
                    properties={"title": {"title": [{"text": {"content": title}}]}},
                    children=blocks,
                )
                print(f"✅ Created Notion status page")

            return True

        except Exception as e:
            print(f"⚠️  Failed to push status to Notion: {e}")
            return False

    def sync_documentation(self, docs_dir: Path) -> Dict[str, bool]:
        """
        Sync documentation directory to Notion.

        Args:
            docs_dir: Path to docs directory

        Returns:
            Dictionary mapping filenames to sync success
        """
        if not self.is_enabled():
            print("Notion plugin not enabled - skipping doc sync")
            return {}

        if not docs_dir.exists():
            print(f"⚠️  Docs directory not found: {docs_dir}")
            return {}

        results = {}

        try:
            # Find all markdown files
            md_files = list(docs_dir.glob("*.md"))

            for md_file in md_files:
                try:
                    results[md_file.name] = self._sync_doc_file(md_file)
                except Exception as e:
                    print(f"⚠️  Failed to sync {md_file.name}: {e}")
                    results[md_file.name] = False

            successful = sum(1 for v in results.values() if v)
            print(f"✅ Synced {successful}/{len(md_files)} docs to Notion")

            return results

        except Exception as e:
            print(f"⚠️  Failed to sync documentation: {e}")
            return results

    def create_feature_page(self, feature: Dict[str, Any]) -> Optional[str]:
        """
        Create a Notion page for a feature.

        Args:
            feature: Feature dictionary

        Returns:
            Page URL if successful
        """
        if not self.is_enabled():
            return None

        try:
            # Build page content
            content = f"""# {feature['name']}

## Description
{feature.get('description', 'No description')}

## Details
- **Status:** {feature.get('status', 'unknown')}
- **Priority:** {feature.get('priority', 'medium')}
- **Version:** {feature.get('version', '1.0.0')}

## Progress
- Created: {datetime.now().strftime('%Y-%m-%d')}
"""

            if "week" in feature:
                content += f"- Week: {feature['week']}\n"

            if "build" in feature:
                content += f"- Build: {feature['build']}\n"

            blocks = self._markdown_to_blocks(content)

            page = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties={
                    "title": {"title": [{"text": {"content": feature["name"]}}]},
                    "Status": {"select": {"name": feature.get("status", "planned")}},
                    "Priority": {"select": {"name": feature.get("priority", "medium")}},
                },
                children=blocks,
            )

            print(f"✅ Created Notion page for {feature['name']}")
            return page["url"]

        except Exception as e:
            print(f"⚠️  Failed to create Notion page: {e}")
            return None

    def _sync_doc_file(self, doc_file: Path) -> bool:
        """Sync a single documentation file to Notion"""
        with open(doc_file, "r") as f:
            content = f.read()

        title = doc_file.stem.replace("_", " ").replace("-", " ").title()

        # Check if page exists
        page_id = self._find_doc_page(title)

        blocks = self._markdown_to_blocks(content)

        try:
            if page_id:
                # Update existing
                # First, delete old content
                children = self.client.blocks.children.list(block_id=page_id)
                for block in children.get("results", []):
                    self.client.blocks.delete(block_id=block["id"])

                # Add new content
                self.client.blocks.children.append(block_id=page_id, children=blocks)
            else:
                # Create new
                self.client.pages.create(
                    parent={"database_id": self.database_id},
                    properties={"title": {"title": [{"text": {"content": title}}]}},
                    children=blocks,
                )

            return True

        except Exception as e:
            print(f"⚠️  Error syncing {doc_file.name}: {e}")
            return False

    def _markdown_to_blocks(self, markdown: str) -> List[Dict[str, Any]]:
        """
        Convert markdown to Notion blocks.

        Basic conversion - headers, paragraphs, lists, code blocks.
        """
        blocks = []
        lines = markdown.split("\n")

        i = 0
        while i < len(lines):
            line = lines[i]

            # Skip empty lines
            if not line.strip():
                i += 1
                continue

            # Headers
            if line.startswith("# "):
                blocks.append(
                    {
                        "object": "block",
                        "type": "heading_1",
                        "heading_1": {"rich_text": [{"text": {"content": line[2:].strip()}}]},
                    }
                )
            elif line.startswith("## "):
                blocks.append(
                    {
                        "object": "block",
                        "type": "heading_2",
                        "heading_2": {"rich_text": [{"text": {"content": line[3:].strip()}}]},
                    }
                )
            elif line.startswith("### "):
                blocks.append(
                    {
                        "object": "block",
                        "type": "heading_3",
                        "heading_3": {"rich_text": [{"text": {"content": line[4:].strip()}}]},
                    }
                )

            # Bullet lists
            elif line.strip().startswith("- "):
                blocks.append(
                    {
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [{"text": {"content": line.strip()[2:]}}]
                        },
                    }
                )

            # Code blocks
            elif line.strip().startswith("```"):
                code_lines = []
                i += 1
                while i < len(lines) and not lines[i].strip().startswith("```"):
                    code_lines.append(lines[i])
                    i += 1

                code = "\n".join(code_lines)
                blocks.append(
                    {
                        "object": "block",
                        "type": "code",
                        "code": {
                            "rich_text": [{"text": {"content": code}}],
                            "language": "plain text",
                        },
                    }
                )

            # Regular paragraphs
            else:
                blocks.append(
                    {
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {"rich_text": [{"text": {"content": line.strip()}}]},
                    }
                )

            i += 1

        return blocks

    def _find_status_page(self) -> Optional[str]:
        """Find existing status page in database"""
        try:
            results = self.client.databases.query(
                database_id=self.database_id,
                filter={"property": "title", "title": {"contains": "Status"}},
            )

            if results.get("results"):
                return results["results"][0]["id"]

        except Exception:
            pass

        return None

    def _find_doc_page(self, title: str) -> Optional[str]:
        """Find existing doc page by title"""
        try:
            results = self.client.databases.query(
                database_id=self.database_id,
                filter={"property": "title", "title": {"equals": title}},
            )

            if results.get("results"):
                return results["results"][0]["id"]

        except Exception:
            pass

        return None


# Global plugin instance
_notion_plugin: Optional[NotionPlugin] = None


def get_notion_plugin() -> NotionPlugin:
    """
    Get global Notion plugin instance.

    Returns:
        NotionPlugin instance
    """
    global _notion_plugin
    if _notion_plugin is None:
        _notion_plugin = NotionPlugin()
    return _notion_plugin
