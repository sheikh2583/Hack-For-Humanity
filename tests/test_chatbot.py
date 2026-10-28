"""Test chatbot routing.

Input schema: synthetic district names and user utterances. Output schema: asserted
ChatResponse navigation fields.
"""

from app import chatbot


def test_known_district_returns_community_navigation() -> None:
    """A supplied district name should map to the existing Community view."""
    response = chatbot.respond("Show Dhaka", ["Dhaka"], lang="en")

    assert response.navigate_to == "community"
    assert response.district == "Dhaka"


def test_faq_question_returns_curated_answer_without_navigation() -> None:
    """FAQ wording is answered from the active catalogue, not an external model."""
    response = chatbot.respond("What does candidate mean?", [], lang="en")

    assert response.navigate_to is None
    assert "satellite model" in response.text


def test_bangla_faq_question_returns_bangla_answer() -> None:
    """Bangla FAQ retrieval uses the matching translated answer."""
    response = chatbot.respond("প্রার্থী মানে কী?", [], lang="bn")

    assert "প্রার্থী" in response.text


def test_faq_retrieval_maps_english_paraphrases_to_known_answer() -> None:
    """Different wording retrieves the same curated Dhoa FAQ content."""
    response = chatbot.respond("What does Dhoa actually do?", [], lang="en")
    nearby = chatbot.respond("Can I check kilns around my neighborhood?", [], lang="en")

    assert "public map" in response.text
    assert "Kilns near me" in nearby.text


def test_faq_retrieval_maps_bangla_paraphrase_to_known_answer() -> None:
    """Bangla paraphrases retrieve the approved nearby search guidance."""
    response = chatbot.respond("আমার বাড়ির পাশে ভাটা খুঁজব কীভাবে?", [], lang="bn")

    assert "কাছের ভাটা" in response.text


def test_short_bangla_dhoa_question_matches_faq_spelling_variant() -> None:
    """The alternate Bangla spelling still retrieves the Dhoa FAQ."""
    response = chatbot.respond("ধোঁয়া কী?", [], lang="bn")

    assert "মানচিত্র" in response.text


def test_question_about_finding_kilns_answers_faq_without_losing_place_search() -> None:
    """A how-to question answers the FAQ while a named district still navigates."""
    faq = chatbot.respond("How can I find kilns by my village?", [], lang="en")
    place = chatbot.respond("Find kilns in Dhaka", ["Dhaka"], lang="en")

    assert faq.navigate_to is None
    assert "Kilns near me" in faq.text
    assert place.navigate_to == "community" and place.district == "Dhaka"


def test_report_followup_paraphrase_matches_report_faq() -> None:
    """Different report-submission wording retrieves the known follow-up answer."""
    response = chatbot.respond("What happens after I submit a report?", [], lang="en")

    assert "Inspector Portal" in response.text


def test_uncovered_emissions_question_does_not_match_generic_dhoa_faq() -> None:
    """A topic absent from the FAQ must not retrieve a merely overlapping answer."""
    response = chatbot.respond("Can Dhoa measure current emissions?", [], lang="en")

    assert "Try a question" in response.text


def test_unknown_question_uses_guided_positive_fallback() -> None:
    """Unknown questions get a useful next step instead of a dead-end reply."""
    response = chatbot.respond("Can it predict next year's air quality?", [], lang="en")

    assert "Try a question" in response.text
