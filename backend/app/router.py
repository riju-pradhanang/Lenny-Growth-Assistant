import re
from typing import Literal

IntentType = Literal["grounded_qa", "essay", "artifact"]


def classify_intent(text: str) -> IntentType:
    """
    Classifies user intent into one of:
    - 'essay': requests for Ship 30 for 30 / atomic essays or structured long-form essays
    - 'artifact': requests to produce HTML/Markdown documents or interactive snippets as artifacts
    - 'grounded_qa': general questions answering grounded in transcripts
    """
    normalized = text.strip().lower()

    # Check for artifact generation intent
    artifact_patterns = [
        r"\bartifact\b",
        r"\b(?:create|generate|make|build|export|turn\s+(?:this|it|the\s+conversation|the\s+answer)\s+into)\s+(?:an?\s+)?(?:html|markdown|md|css)\s+(?:snippet|document|doc|card|table|widget|component|page|view)\b",
        r"\b(?:html|markdown|md)\s+(?:snippet|card|document|component|widget)\b",
        r"\bgenerate\s+(?:an?\s+)?(?:html(?:\/css)?|markdown)\s+(?:file|document|snippet|view)\b",
    ]
    for pattern in artifact_patterns:
        if re.search(pattern, normalized):
            return "artifact"

    # Check for Ship 30 for 30 / Essay intent
    essay_patterns = [
        r"\bship\s*30(?:\s*for\s*30)?\b",
        r"\batomic\s+essay\b",
        r"\b(?:write|generate|draft|create|produce)\s+(?:an?\s+)?(?:1250[-\s]*word\s+)?(?:essay|long-form\s+post|deep\s+dive\s+essay|newsletter\s+essay)\b",
        r"\b(?:turn|convert)\s+(?:this|the\s+above|the\s+transcript|these\s+insights)\s+into\s+(?:an?\s+)?essay\b",
        r"\bessay\s+(?:about|on|covering|exploring)\b",
    ]
    for pattern in essay_patterns:
        if re.search(pattern, normalized):
            return "essay"

    # Default to grounded Q&A
    return "grounded_qa"
