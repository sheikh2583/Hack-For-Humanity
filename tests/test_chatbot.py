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
