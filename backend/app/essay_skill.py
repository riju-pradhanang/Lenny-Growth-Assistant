import re
from dataclasses import dataclass
from typing import Any

from app.retrieval import RetrievedChunk, context_prompt


@dataclass
class ValidationResult:
    is_valid: bool
    word_count: int
    has_headings: bool
    has_bullets: bool
    has_bold: bool
    has_takeaway: bool
    feedback: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "word_count": self.word_count,
            "has_headings": self.has_headings,
            "has_bullets": self.has_bullets,
            "has_bold": self.has_bold,
            "has_takeaway": self.has_takeaway,
            "feedback": self.feedback,
        }


def validate_essay_structure(
    text: str, min_words: int = 1050, max_words: int = 1450
) -> ValidationResult:
    """
    Validates that a Ship 30 for 30 style essay satisfies key structural rules:
    - Target word count roughly ~1,250 words (acceptable 1,050 - 1,450 words)
    - Presence of clear headings (## or ###)
    - Presence of bulleted / numbered lists
    - Presence of selective bold emphasis
    - Presence of a single explicit, specific takeaway
    """
    words = len(re.findall(r"\b\w+(?:'\w+)?\b", text))
    has_headings = bool(re.search(r"^#{1,4}\s+.+", text, re.MULTILINE))
    has_bullets = bool(re.search(r"^[\*\-\+]\s+.+", text, re.MULTILINE) or re.search(r"^\d+\.\s+.+", text, re.MULTILINE))
    has_bold = bool(re.search(r"\*\*[^*]+\*\*", text))
    has_takeaway = bool(
        re.search(
            r"(?:takeaway|key\s+takeaway|core\s+takeaway|bottom\s+line|actionable\s+insight|the\s+one\s+thing)",
            text,
            re.IGNORECASE,
        )
    )

    feedback: list[str] = []
    if words < min_words:
        feedback.append(f"Word count is {words}, which is below the minimum of {min_words} words. Expand the discussion and supporting examples.")
    elif words > max_words:
        feedback.append(f"Word count is {words}, which exceeds the maximum of {max_words} words. Make it more concise.")

    if not has_headings:
        feedback.append("Missing section headings (use '## Heading Title').")
    if not has_bullets:
        feedback.append("Missing bulleted or numbered lists for skimmability.")
    if not has_bold:
        feedback.append("Missing bold emphasis on key concepts.")
    if not has_takeaway:
        feedback.append("Missing an explicit, dedicated 'Core Takeaway' section near the close.")

    is_valid = len(feedback) == 0
    return ValidationResult(
        is_valid=is_valid,
        word_count=words,
        has_headings=has_headings,
        has_bullets=has_bullets,
        has_bold=has_bold,
        has_takeaway=has_takeaway,
        feedback=feedback,
    )


def build_essay_system_prompt(chunks: list[RetrievedChunk], revision_feedback: list[str] | None = None) -> str:
    """
    Builds the specialized Ship 30 for 30 essay generation system prompt.
    """
    context_str = context_prompt(chunks) if chunks else "No transcript chunks available."
    prompt = f"""You are an expert product and growth essayist trained in the Ship 30 for 30 writing framework.
Your task is to write a comprehensive, deeply insightful, ~1,250-word essay strictly grounded in the supplied Lenny's Podcast and Newsletter transcript excerpts.

### Ship 30 for 30 Structural Principles:
1. **The Hook**: Open with a compelling 1-2 sentence hook paragraph that grabs attention and poses the core problem.
2. **Short, Punchy Paragraphs**: Write in concise paragraphs (1-3 sentences maximum). Avoid walls of text.
3. **Skimmable Structure**: Use clear Markdown headings (`## `) and bullet points (`- `) so the reader can absorb the structure in 10 seconds.
4. **Selective Bold Emphasis**: Bold key terms, counter-intuitive insights, and operator rules of thumb.
5. **Single Specific Takeaway**: Conclude with an explicit section titled `## The Core Takeaway` featuring a single, high-impact, actionable action item.
6. **Strict Grounding & Length**: Target length is approximately 1,250 words (between 1,050 and 1,450 words). Every claim, strategy, or quote must be directly grounded in the supplied context, citing the guest or episode naturally in prose.

### Source Excerpts:
{context_str}
"""
    if revision_feedback:
        prompt += f"""
### MANDATORY CORRECTIONS (Previous draft failed structural validation):
Please fix these specific structural issues in your revision:
{chr(10).join(f"- {f}" for f in revision_feedback)}
"""
    return prompt
