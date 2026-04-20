"""Test that coding restraints are properly encoded as non-empty strings."""


def test_coding_restraints():
    """Test that three key coding restraints are encoded as non-empty strings."""

    # Restraint 1: Notion allowlist/index must be under memory/users/.../notion/, never ~/
    notion_path_restraint = (
        "Notion allowlists and page index must live under memory/users/<user_key>/notion/ "
        "for allowlist.json and discovered_page_index.json. Paths under ~/ are not "
        "acceptable for product state."
    )

    # Restraint 2: LLM is Bedrock-only, reject ANTHROPIC_API_KEY/direct Anthropic API
    bedrock_only_restraint = (
        "This application uses Amazon Bedrock only (get_default_model()). "
        "Never assume or instruct ANTHROPIC_API_KEY or direct Anthropic API paths."
    )

    # Restraint 3: Web facts via neuuf_researcher specialist tool
    web_research_restraint = (
        "The neuuf_researcher tool should handle web research instead of "
        "reimplementing it in python_repl. Use specialists for web or cited external facts."
    )

    # Assert all restraints are encoded as non-empty strings
    assert isinstance(notion_path_restraint, str) and len(notion_path_restraint) > 0
    assert isinstance(bedrock_only_restraint, str) and len(bedrock_only_restraint) > 0
    assert isinstance(web_research_restraint, str) and len(web_research_restraint) > 0

    # Verify key concepts are present in each restraint
    assert "memory/users/" in notion_path_restraint and "~/" in notion_path_restraint
    assert "Bedrock" in bedrock_only_restraint and "ANTHROPIC_API_KEY" in bedrock_only_restraint
    assert "neuuf_researcher" in web_research_restraint and "web" in web_research_restraint
