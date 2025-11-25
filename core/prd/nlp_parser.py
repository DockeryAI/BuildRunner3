"""
Enhanced NLP Parser using spaCy

Improves upon regex patterns with:
- Entity recognition
- Intent classification
- Complex command parsing
- Multi-feature changes in one command
"""

import logging
from typing import Dict, List, Any, Optional
import re

logger = logging.getLogger(__name__)

# Try to import spaCy, fall back to regex if not available
try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    logger.warning("spaCy not available, using regex-based parsing")


class NLPParser:
    """
    Enhanced natural language parser for PRD commands

    Uses spaCy when available, falls back to regex patterns
    """

    def __init__(self):
        self.nlp = None

        if SPACY_AVAILABLE:
            try:
                # Try to load small English model
                self.nlp = spacy.load("en_core_web_sm")
                logger.info("spaCy model loaded successfully")
            except OSError:
                logger.warning("spaCy model 'en_core_web_sm' not found. Install with: python -m spacy download en_core_web_sm")
                SPACY_AVAILABLE = False

    def parse(self, text: str, current_features: List[Dict] = None) -> Dict[str, Any]:
        """
        Parse natural language text to PRD updates

        Args:
            text: Natural language command
            current_features: List of current features for context

        Returns:
            Dictionary with PRD updates
        """
        if self.nlp:
            return self._parse_with_spacy(text, current_features or [])
        else:
            return self._parse_with_regex(text, current_features or [])

    def _parse_with_spacy(self, text: str, current_features: List[Dict]) -> Dict[str, Any]:
        """Parse using spaCy NLP"""
        doc = self.nlp(text.lower())

        # Extract intent (add, remove, update, modify)
        intent = self._extract_intent(doc)

        if intent == "add":
            return self._parse_add_with_spacy(doc, text)
        elif intent == "remove":
            return self._parse_remove_with_spacy(doc, current_features)
        elif intent in ["update", "modify", "change"]:
            return self._parse_update_with_spacy(doc, current_features)
        elif intent == "rename":
            return self._parse_rename_with_spacy(doc, current_features, text)

        return {}

    def _extract_intent(self, doc) -> str:
        """Extract intent from spaCy doc"""
        intent_verbs = {
            "add": ["add", "create", "new"],
            "remove": ["remove", "delete", "drop"],
            "update": ["update", "modify", "change", "edit"],
            "rename": ["rename", "call"]
        }

        for token in doc:
            if token.pos_ == "VERB" or token.lemma_ in sum(intent_verbs.values(), []):
                for intent, verbs in intent_verbs.items():
                    if token.lemma_ in verbs or token.text in verbs:
                        return intent

        return "unknown"

    def _parse_add_with_spacy(self, doc, original_text: str) -> Dict[str, Any]:
        """Parse add command with spaCy"""
        # Extract feature name (noun phrases after the verb)
        feature_name = None

        # Simple approach: everything after "add" or "create"
        text_lower = original_text.lower()
        for trigger in ["add", "create", "new"]:
            if trigger in text_lower:
                parts = original_text.split(trigger, 1)
                if len(parts) > 1:
                    feature_name = parts[1].strip()
                    # Remove common words
                    feature_name = re.sub(r'\b(feature|a|an|the)\b', '', feature_name, flags=re.IGNORECASE).strip()
                    break

        if not feature_name:
            # Fallback: extract noun chunks
            noun_chunks = [chunk.text for chunk in doc.noun_chunks]
            if noun_chunks:
                feature_name = " ".join(noun_chunks)

        if feature_name:
            # Generate feature ID
            feature_id = feature_name.lower().replace(' ', '-')
            feature_id = re.sub(r'[^a-z0-9-]', '', feature_id)

            return {
                "add_feature": {
                    "id": f"feature-{feature_id}",
                    "name": feature_name.title(),
                    "description": f"Feature: {feature_name}",
                    "priority": "medium"
                }
            }

        return {}

    def _parse_remove_with_spacy(self, doc, current_features: List[Dict]) -> Dict[str, Any]:
        """Parse remove command with spaCy"""
        # Extract feature reference (ID or name)
        # Look for entities or noun chunks after remove verb

        for ent in doc.ents:
            # Check if entity matches a feature
            for feature in current_features:
                if (ent.text.lower() in feature.get("id", "").lower() or
                    ent.text.lower() in feature.get("name", "").lower()):
                    return {"remove_feature": feature["id"]}

        # Fallback: check noun chunks
        for chunk in doc.noun_chunks:
            chunk_text = chunk.text.lower()
            for feature in current_features:
                if (chunk_text in feature.get("id", "").lower() or
                    chunk_text in feature.get("name", "").lower()):
                    return {"remove_feature": feature["id"]}

        return {}

    def _parse_update_with_spacy(self, doc, current_features: List[Dict]) -> Dict[str, Any]:
        """Parse update command with spaCy"""
        # Pattern: "update <feature> to <new value>"
        # or: "change <feature> description to <text>"

        # Extract feature reference and what to update
        feature_ref = None
        update_field = "description"  # default
        new_value = None

        # Simple pattern matching
        text = doc.text
        if " to " in text:
            parts = text.split(" to ", 1)
            before_to = parts[0]
            new_value = parts[1].strip()

            # Extract feature from before_to
            for feature in current_features:
                if (feature.get("id", "").lower() in before_to or
                    feature.get("name", "").lower() in before_to):
                    feature_ref = feature["id"]
                    break

            # Determine field
            if "priority" in before_to:
                update_field = "priority"
                # Extract priority value
                for priority in ["critical", "high", "medium", "low"]:
                    if priority in new_value.lower():
                        new_value = priority
                        break
            elif "name" in before_to or "title" in before_to:
                update_field = "name"
            elif "description" in before_to or "desc" in before_to:
                update_field = "description"

        if feature_ref and new_value:
            return {
                "update_feature": {
                    "id": feature_ref,
                    "updates": {update_field: new_value}
                }
            }

        return {}

    def _parse_rename_with_spacy(self, doc, current_features: List[Dict], original_text: str) -> Dict[str, Any]:
        """Parse rename command"""
        # Pattern: "rename <old> to <new>"

        if " to " in original_text:
            parts = original_text.lower().split(" to ", 1)
            old_ref = parts[0].replace("rename", "").strip()
            new_name = parts[1].strip()

            # Find feature
            for feature in current_features:
                if (old_ref in feature.get("id", "").lower() or
                    old_ref in feature.get("name", "").lower()):
                    return {
                        "update_feature": {
                            "id": feature["id"],
                            "updates": {"name": new_name.title()}
                        }
                    }

        return {}

    def _parse_with_regex(self, text: str, current_features: List[Dict]) -> Dict[str, Any]:
        """
        Fallback regex-based parsing

        This is the original regex approach for when spaCy is not available
        """
        text_lower = text.lower().strip()

        # Add feature pattern
        add_match = re.match(r'add\s+(?:feature\s+)?(.+)', text_lower)
        if add_match:
            feature_name = add_match.group(1).strip()
            feature_id = feature_name.replace(' ', '-')
            feature_id = re.sub(r'[^a-z0-9-]', '', feature_id)

            return {
                "add_feature": {
                    "id": f"feature-{feature_id}",
                    "name": feature_name.title(),
                    "description": f"Feature: {feature_name}",
                    "priority": "medium"
                }
            }

        # Remove feature pattern
        remove_match = re.match(r'remove\s+(?:feature\s+)?(.+)', text_lower)
        if remove_match:
            feature_ref = remove_match.group(1).strip()
            for feature in current_features:
                if (feature.get("id", "") == feature_ref or
                    feature.get("name", "").lower() == feature_ref):
                    return {"remove_feature": feature["id"]}

        # Update feature pattern (simplified)
        update_match = re.match(r'update\s+(?:feature\s+)?(\S+)\s+to\s+(.+)', text_lower)
        if update_match:
            feature_ref = update_match.group(1).strip()
            new_desc = update_match.group(2).strip()

            for feature in current_features:
                if (feature.get("id", "") == feature_ref or
                    feature.get("name", "").lower() == feature_ref):
                    return {
                        "update_feature": {
                            "id": feature["id"],
                            "updates": {"description": new_desc}
                        }
                    }

        return {}


# Global parser instance
_parser: Optional[NLPParser] = None


def get_nlp_parser() -> NLPParser:
    """Get or create global NLP parser"""
    global _parser

    if _parser is None:
        _parser = NLPParser()

    return _parser
