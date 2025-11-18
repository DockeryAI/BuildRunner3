"""
Supabase client for BuildRunner 3.0

Manages database connections and operations.
Optional integration because not everyone wants cloud databases.
"""

import os
from typing import Optional
from dotenv import load_dotenv


class SupabaseClient:
    """
    Wrapper for Supabase database operations.

    Optional feature - if credentials aren't configured, operations are no-ops.
    Because local-first is always better than cloud-first.
    """

    def __init__(self):
        """Initialize Supabase client with environment variables."""
        load_dotenv()

        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        self.enabled = bool(self.url and self.key)
        self.client = None

        if self.enabled:
            try:
                from supabase import create_client, Client
                self.client: Client = create_client(self.url, self.key)
            except ImportError:
                print("Warning: supabase package not installed. Database features disabled.")
                self.enabled = False
            except Exception as e:
                print(f"Warning: Failed to initialize Supabase client: {e}")
                self.enabled = False

    def is_enabled(self) -> bool:
        """Check if Supabase integration is enabled."""
        return self.enabled

    async def sync_feature(self, feature_data: dict) -> bool:
        """
        Sync feature to Supabase.

        Args:
            feature_data: Feature data to sync

        Returns:
            True if sync succeeded, False otherwise
        """
        if not self.enabled:
            return False

        try:
            # Upsert feature to database
            result = self.client.table("features").upsert(feature_data).execute()
            return bool(result.data)
        except Exception as e:
            print(f"Error syncing feature to Supabase: {e}")
            return False

    async def get_features(self) -> list[dict]:
        """
        Get all features from Supabase.

        Returns:
            List of feature dictionaries
        """
        if not self.enabled:
            return []

        try:
            result = self.client.table("features").select("*").execute()
            return result.data or []
        except Exception as e:
            print(f"Error fetching features from Supabase: {e}")
            return []

    async def delete_feature(self, feature_id: str) -> bool:
        """
        Delete feature from Supabase.

        Args:
            feature_id: ID of feature to delete

        Returns:
            True if deletion succeeded, False otherwise
        """
        if not self.enabled:
            return False

        try:
            result = self.client.table("features").delete().eq("id", feature_id).execute()
            return bool(result.data)
        except Exception as e:
            print(f"Error deleting feature from Supabase: {e}")
            return False

    async def log_event(self, event_type: str, data: dict) -> bool:
        """
        Log event to Supabase.

        Args:
            event_type: Type of event
            data: Event data

        Returns:
            True if logging succeeded, False otherwise
        """
        if not self.enabled:
            return False

        try:
            event = {
                "event_type": event_type,
                "data": data
            }
            result = self.client.table("events").insert(event).execute()
            return bool(result.data)
        except Exception as e:
            print(f"Error logging event to Supabase: {e}")
            return False


# Global client instance - because singletons are still a thing
_supabase_client: Optional[SupabaseClient] = None


def get_supabase_client() -> SupabaseClient:
    """
    Get global Supabase client instance.

    Returns:
        SupabaseClient instance
    """
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = SupabaseClient()
    return _supabase_client
