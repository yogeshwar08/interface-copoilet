from app.agents.graph import validate_citations


def test_valid_citations():
    sources = [
        {"page": 1},
        {"page": 2},
        {"page": 3},
    ]

    response = "The criteria are listed in the guideline [Source 1]."

    cleaned, citations = validate_citations(response, sources)

    assert cleaned == "The criteria are listed in the guideline [Source 1]."
    assert citations == [1]


def test_normalizes_source_format():
    sources = [
        {"page": 1},
        {"page": 2},
    ]

    response = "The criteria are listed here [Source4]."

    cleaned, citations = validate_citations(response, sources)

    assert cleaned == "The criteria are listed here [Source 4]."
    assert citations == []


def test_multiple_valid_citations():
    sources = [
        {"page": 1},
        {"page": 2},
        {"page": 3},
    ]

    response = (
        "The guideline discusses diagnosis [Source 1] "
        "and confirmation [Source 3]."
    )

    cleaned, citations = validate_citations(response, sources)

    assert citations == [1, 3]