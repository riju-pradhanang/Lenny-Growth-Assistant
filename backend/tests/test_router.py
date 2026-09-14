import pytest
from app.router import classify_intent


@pytest.mark.parametrize(
    "query",
    [
        "How does Figma approach product-led growth?",
        "What did Shreyas Doshi say about the LNO framework?",
        "Explain retention curve dynamics according to Lenny's guests",
        "What are the best practices for activation funnels?",
        "What did Brian Chesky mention about founder mode?",
    ],
)
def test_classify_grounded_qa_intent(query: str):
    assert classify_intent(query) == "grounded_qa"


@pytest.mark.parametrize(
    "query",
    [
        "Write a Ship 30 for 30 essay on product market fit",
        "Generate an atomic essay about viral loops based on the transcripts",
        "Turn this discussion into a 1250-word Ship 30 style essay",
        "Draft an essay summarizing Lenny's interview on activation funnels",
        "Produce a deep dive essay about pricing strategy from the podcast",
    ],
)
def test_classify_essay_intent(query: str):
    assert classify_intent(query) == "essay"


@pytest.mark.parametrize(
    "query",
    [
        "Create an HTML snippet artifact showing the growth checklist",
        "Generate a Markdown document artifact from this conversation",
        "Turn this into an HTML card artifact",
        "Make this conversation into a markdown artifact",
        "Generate an HTML artifact for this comparison",
    ],
)
def test_classify_artifact_intent(query: str):
    assert classify_intent(query) == "artifact"
