import pytest
from app.essay_skill import build_essay_system_prompt, validate_essay_structure
from app.retrieval import RetrievedChunk
from uuid import uuid4


def generate_mock_essay(word_count: int = 1150, include_headings: bool = True, include_bullets: bool = True, include_bold: bool = True, include_takeaway: bool = True) -> str:
    lines = []
    lines.append("Most product leaders believe growth is about adding features, but that's a fatal illusion.")
    lines.append("The highest-performing companies obsess over activation and retention.")
    
    if include_headings:
        lines.append("## Why Activation Is The Real Growth Lever")
    
    if include_bold:
        lines.append("According to **Elena Verna**, growth without retention is just pouring water into a **leaky bucket**.")
    else:
        lines.append("According to Elena Verna, growth without retention is just pouring water into a leaky bucket.")
        
    if include_bullets:
        lines.append("- Setup moment: When the user sets up their profile.")
        lines.append("- Aha moment: When the user first experiences the core value.")
        lines.append("- Habit moment: When the product becomes part of their workflow.")
        
    if include_takeaway:
        lines.append("## The Core Takeaway")
        lines.append("Focus 80% of your growth experiments on tightening time-to-value before spending a single dollar on paid acquisition.")

    # Fill words to reach target count
    current_words = len(" ".join(lines).split())
    padding_needed = max(0, word_count - current_words)
    filler_sentence = "Operators must continuously measure cohort retention curves to understand user drop-off and optimize onboarding friction. "
    filler = (filler_sentence * (padding_needed // len(filler_sentence.split()) + 1))
    filler_words = filler.split()[:padding_needed]
    lines.insert(len(lines) - 2 if include_takeaway else len(lines), " ".join(filler_words))

    return "\n\n".join(lines)


def test_validate_compliant_essay():
    essay = generate_mock_essay(word_count=1200)
    result = validate_essay_structure(essay, min_words=1050, max_words=1450)
    assert result.is_valid is True
    assert result.has_headings is True
    assert result.has_bullets is True
    assert result.has_bold is True
    assert result.has_takeaway is True
    assert len(result.feedback) == 0


def test_validate_short_essay_fails_word_count():
    essay = generate_mock_essay(word_count=400)
    result = validate_essay_structure(essay, min_words=1050, max_words=1450)
    assert result.is_valid is False
    assert any("below the minimum" in f for f in result.feedback)


def test_validate_missing_structural_elements():
    # Essay missing headings, bullets, bold, and takeaway
    raw_text = "Word " * 1200
    result = validate_essay_structure(raw_text, min_words=1050, max_words=1450)
    assert result.is_valid is False
    assert result.has_headings is False
    assert result.has_bullets is False
    assert result.has_bold is False
    assert result.has_takeaway is False
    assert len(result.feedback) == 4


def test_build_essay_prompt_with_feedback():
    chunk = RetrievedChunk(
        id=uuid4(),
        text="Product-led growth thrives when end-users discover value self-serve.",
        episode_title="How Figma Scales",
        guest_name="Amanda Kleha",
        source_url="https://lenny.com/figma",
        distance=0.15,
    )
    prompt = build_essay_system_prompt([chunk], revision_feedback=["Missing section headings", "Word count too low"])
    assert "Ship 30 for 30" in prompt
    assert "MANDATORY CORRECTIONS" in prompt
    assert "Missing section headings" in prompt
    assert "How Figma Scales" in prompt
