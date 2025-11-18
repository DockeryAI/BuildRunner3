"""
Database migration system for BuildRunner

Features:
- Schema version tracking
- Forward migrations (migrate)
- Rollback support (basic)
- Migration file discovery and execution
"""

from pathlib import Path
from typing import List, Optional, Dict, Any
import logging
import re

from core.persistence.database import Database

logger = logging.getLogger(__name__)


class Migration:
    """Represents a database migration."""

    def __init__(self, version: int, name: str, sql: str, rollback_sql: Optional[str] = None):
        """
        Initialize migration.

        Args:
            version: Migration version number
            name: Migration name/description
            sql: SQL statements to execute
            rollback_sql: SQL to rollback migration (optional)
        """
        self.version = version
        self.name = name
        self.sql = sql
        self.rollback_sql = rollback_sql

    def __repr__(self):
        return f"Migration(version={self.version}, name='{self.name}')"


class MigrationManager:
    """Manages database migrations."""

    def __init__(self, db: Database, migrations_dir: Optional[Path] = None):
        """
        Initialize migration manager.

        Args:
            db: Database instance
            migrations_dir: Directory containing migration files
        """
        self.db = db
        self.migrations_dir = migrations_dir or Path(__file__).parent / "migrations"

        # Ensure migrations directory exists
        self.migrations_dir.mkdir(parents=True, exist_ok=True)

        # Initialize schema version table
        self._init_version_table()

    def _init_version_table(self):
        """Initialize schema version tracking table."""
        if not self.db.table_exists("schema_version"):
            sql = """
            CREATE TABLE schema_version (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL,
                applied_by TEXT DEFAULT 'buildrunner'
            );
            """
            self.db.execute(sql)
            logger.info("Initialized schema version table")

    def get_current_version(self) -> int:
        """
        Get current schema version.

        Returns:
            Current version number (0 if no migrations applied)
        """
        result = self.db.query_one(
            "SELECT MAX(version) as version FROM schema_version"
        )

        if result and result['version'] is not None:
            return result['version']
        return 0

    def get_applied_migrations(self) -> List[Dict[str, Any]]:
        """
        Get list of applied migrations.

        Returns:
            List of applied migration records
        """
        return self.db.query(
            "SELECT * FROM schema_version ORDER BY version"
        )

    def discover_migrations(self) -> List[Migration]:
        """
        Discover migration files in migrations directory.

        Returns:
            List of Migration objects sorted by version
        """
        migrations = []

        # Pattern: NNN_description.sql (e.g., 001_initial.sql)
        pattern = re.compile(r'^(\d{3})_(.+)\.sql$')

        for file_path in sorted(self.migrations_dir.glob("*.sql")):
            match = pattern.match(file_path.name)
            if not match:
                logger.warning(f"Skipping invalid migration file: {file_path.name}")
                continue

            version = int(match.group(1))
            name = match.group(2).replace('_', ' ').title()

            # Read migration SQL
            with open(file_path, 'r') as f:
                sql = f.read()

            # Check for rollback SQL (in comments)
            rollback_sql = self._extract_rollback_sql(sql)

            migration = Migration(version, name, sql, rollback_sql)
            migrations.append(migration)

        return sorted(migrations, key=lambda m: m.version)

    def _extract_rollback_sql(self, sql: str) -> Optional[str]:
        """
        Extract rollback SQL from migration file comments.

        Looks for block like:
        -- ROLLBACK:
        -- DROP TABLE ...;

        Args:
            sql: Migration SQL content

        Returns:
            Rollback SQL if found, None otherwise
        """
        lines = sql.split('\n')
        rollback_lines = []
        in_rollback = False

        for line in lines:
            if '-- ROLLBACK:' in line:
                in_rollback = True
                continue

            if in_rollback:
                if line.strip().startswith('--'):
                    # Remove comment prefix
                    rollback_lines.append(line.replace('--', '', 1).strip())
                else:
                    # End of rollback block
                    break

        if rollback_lines:
            return '\n'.join(rollback_lines)
        return None

    def get_pending_migrations(self) -> List[Migration]:
        """
        Get list of pending migrations.

        Returns:
            List of migrations not yet applied
        """
        current_version = self.get_current_version()
        all_migrations = self.discover_migrations()

        return [m for m in all_migrations if m.version > current_version]

    def migrate(self, target_version: Optional[int] = None) -> int:
        """
        Run pending migrations.

        Args:
            target_version: Migrate up to this version (None = latest)

        Returns:
            Number of migrations applied
        """
        pending = self.get_pending_migrations()

        if not pending:
            logger.info("No pending migrations")
            return 0

        # Filter by target version if specified
        if target_version is not None:
            pending = [m for m in pending if m.version <= target_version]

        applied_count = 0

        for migration in pending:
            try:
                logger.info(f"Applying migration {migration.version}: {migration.name}")

                # Run migration
                self.db.run_migration(migration.sql)

                # Record in schema_version
                from datetime import datetime, UTC
                self.db.insert('schema_version', {
                    'version': migration.version,
                    'name': migration.name,
                    'applied_at': datetime.now(UTC).isoformat()
                })

                applied_count += 1
                logger.info(f"✓ Applied migration {migration.version}")

            except Exception as e:
                logger.error(f"✗ Failed to apply migration {migration.version}: {e}")
                raise

        logger.info(f"Applied {applied_count} migrations")
        return applied_count

    def rollback(self, steps: int = 1) -> int:
        """
        Rollback migrations.

        Args:
            steps: Number of migrations to rollback

        Returns:
            Number of migrations rolled back
        """
        current_version = self.get_current_version()

        if current_version == 0:
            logger.info("No migrations to rollback")
            return 0

        # Get applied migrations
        applied = self.get_applied_migrations()
        applied.reverse()  # Most recent first

        # Get migration files for rollback
        all_migrations = self.discover_migrations()
        migrations_by_version = {m.version: m for m in all_migrations}

        rolled_back = 0

        for record in applied[:steps]:
            version = record['version']
            migration = migrations_by_version.get(version)

            if not migration:
                logger.warning(f"Migration file not found for version {version}")
                continue

            if not migration.rollback_sql:
                logger.warning(f"No rollback SQL for migration {version}")
                continue

            try:
                logger.info(f"Rolling back migration {version}: {migration.name}")

                # Run rollback
                self.db.run_migration(migration.rollback_sql)

                # Remove from schema_version
                self.db.delete('schema_version', 'version = ?', (version,))

                rolled_back += 1
                logger.info(f"✓ Rolled back migration {version}")

            except Exception as e:
                logger.error(f"✗ Failed to rollback migration {version}: {e}")
                raise

        logger.info(f"Rolled back {rolled_back} migrations")
        return rolled_back

    def status(self) -> Dict[str, Any]:
        """
        Get migration status.

        Returns:
            Dictionary with migration status information
        """
        current_version = self.get_current_version()
        all_migrations = self.discover_migrations()
        pending = self.get_pending_migrations()
        applied = self.get_applied_migrations()

        return {
            'current_version': current_version,
            'total_migrations': len(all_migrations),
            'applied_migrations': len(applied),
            'pending_migrations': len(pending),
            'latest_version': all_migrations[-1].version if all_migrations else 0,
            'applied': [
                {
                    'version': m['version'],
                    'name': m['name'],
                    'applied_at': m['applied_at']
                }
                for m in applied
            ],
            'pending': [
                {
                    'version': m.version,
                    'name': m.name
                }
                for m in pending
            ]
        }

    def print_status(self):
        """Print migration status to console."""
        status = self.status()

        print("\n=== Database Migration Status ===")
        print(f"Current Version: {status['current_version']}")
        print(f"Latest Version:  {status['latest_version']}")
        print(f"Applied:  {status['applied_migrations']} migrations")
        print(f"Pending:  {status['pending_migrations']} migrations")

        if status['applied']:
            print("\nApplied Migrations:")
            for migration in status['applied']:
                print(f"  ✓ {migration['version']:03d} - {migration['name']} ({migration['applied_at']})")

        if status['pending']:
            print("\nPending Migrations:")
            for migration in status['pending']:
                print(f"  ○ {migration['version']:03d} - {migration['name']}")

        print()


def create_migration_manager(db_path: Optional[Path] = None) -> MigrationManager:
    """
    Create a MigrationManager instance.

    Args:
        db_path: Path to database file

    Returns:
        MigrationManager instance
    """
    db = Database(db_path)
    return MigrationManager(db)
