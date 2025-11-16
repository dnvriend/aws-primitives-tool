"""
Documentation generator for kvstore primitives.

AI agent-optimized documentation with computer science semantics,
guarantees, and composability examples.

Note: This code was generated with assistance from AI coding tools
and has been reviewed and tested by a human.
"""



def generate_doc(
    name: str,
    synopsis: str,
    description: str,
    properties: dict[str, str],
    guarantees: list[str],
    when_to_apply: list[str],
    examples: list[dict[str, str]],
    composability: list[dict[str, str]],
    failure_modes: list[str],
    performance: dict[str, str],
    see_also: list[str],
) -> str:
    """
    Generate AI agent-optimized documentation in markdown format.

    Args:
        name: Command name and brief description
        synopsis: Command syntax
        description: Detailed description with CS properties
        properties: Computer science properties dict
        guarantees: List of guarantees (atomicity, consistency, etc.)
        when_to_apply: List of use cases
        examples: List of practical examples with title and code
        composability: List of composition patterns
        failure_modes: List of possible failures
        performance: Performance characteristics dict
        see_also: Related commands

    Returns:
        Markdown-formatted documentation string
    """
    doc = f"# {name}\n\n"

    # Synopsis
    doc += "## SYNOPSIS\n```bash\n"
    doc += synopsis
    doc += "\n```\n\n"

    # Description
    doc += "## DESCRIPTION\n"
    doc += description + "\n\n"

    # Computer Science Properties
    if properties:
        doc += "### Computer Science Properties\n"
        for key, value in properties.items():
            doc += f"- **{key}**: {value}\n"
        doc += "\n"

    # Guarantees
    if guarantees:
        doc += "## GUARANTEES\n"
        for guarantee in guarantees:
            doc += f"- **{guarantee}**\n"
        doc += "\n"

    # When to Apply
    if when_to_apply:
        doc += "## WHEN TO APPLY\n"
        for use_case in when_to_apply:
            doc += f"- **{use_case}**\n"
        doc += "\n"

    # Practical Examples
    if examples:
        doc += "## PRACTICAL EXAMPLES\n\n"
        for idx, example in enumerate(examples, 1):
            doc += f"### Example {idx}: {example['title']}\n"
            doc += "```bash\n"
            doc += example['code']
            doc += "\n```\n\n"

    # Composability
    if composability:
        doc += "## COMPOSABILITY\n\n"
        doc += (
            "_Primitives are composable building blocks. "
            "Below are common patterns (not exhaustive):_\n\n"
        )
        for idx, comp in enumerate(composability, 1):
            doc += f"### Composition {idx}: {comp['title']}\n"
            doc += "```bash\n"
            doc += comp['code']
            doc += "\n```\n"
            if 'note' in comp:
                doc += f"_{comp['note']}_\n"
            doc += "\n"

    # Failure Modes
    if failure_modes:
        doc += "## FAILURE MODES\n"
        for mode in failure_modes:
            doc += f"- `{mode}`\n"
        doc += "\n"

    # Performance
    if performance:
        doc += "## PERFORMANCE CHARACTERISTICS\n"
        for key, value in performance.items():
            doc += f"- **{key}**: {value}\n"
        doc += "\n"

    # See Also
    if see_also:
        doc += "## SEE ALSO\n"
        doc += ", ".join(see_also)
        doc += "\n"

    return doc


def display_doc(doc_content: str) -> None:
    """
    Display documentation using pager or direct print.

    Args:
        doc_content: Markdown documentation content
    """
    import sys

    # For AI agents, direct print is better than pager
    print(doc_content, file=sys.stderr)
    sys.exit(0)
