---
name: rag:index
description: index source code into RAG system
---

# Purpose

Index all source code into a RAG store for use as a "Code RAG" system. This allows for natural language query of code bases.

This means:

- ./aws_primitives_tool
- ./tests
- ./references/*.md
- .pyproject.toml
- README.md
- CLAUDE.md

# Tools

The following tools provide "Agent-Friendly CLI Help" or "Self-Documenting CLI with Inline Examples".

- `gemini-file-search-tool` to search the Code RAG (Retrieval Augmented Generation) store

## Store name

The name of the store will be `aws-primitives-tool`

# Quick prompt guide for the gemini-file-search-tool

- Be Specific and Direct: Clearly state the task to be performed on the uploaded document(s).
Example: "Summarize the key findings from the 'Q3 Sales Report' attached, focusing on the growth metrics for the Alpha product line".

- Define the Desired Output Format: Specify how the information should be presented (e.g., bullet points, a table, or a specific tone).
Example: "Explain the attached technical documentation in simple terms, using bullet points for key steps."

- Provide Context: Include relevant background information or the desired persona.
Example: "You are a market analyst. Based on the attached competitor analysis, draft an email to my team outlining three strategic actions we should take."

- Use Action Verbs: Begin prompts with action verbs like "Summarize," "Extract," "Compare," "Analyze," or "Draft". 

## Important

ALWAYS USE the `gemini-file-search-tool` as it uses RAG and provides the best results AND then use Search and Glob and Read tools to check the sources, to verify the information and to get more detail as we get more context for the fragments of the RAG responses of the `gemini-file-search-tool`.

- The `gemini-file-search-tool` has OPTIONAL `--show-cost` and OPTIONAL `--verbose` and OPTIONAL `--query-grounding-metadata` flags
- The `upload` command accepts GLOB patterns

## Valid commands

The following commands are valid examples:

```
# index files
gemini-file-search-tool upload "*.pdf" --store "papers"
# query store
gemini-file-search-tool query --prompt "What is DORA?" --store "aws-primitives-tool" --query-grounding-metadata --show-cost
```

## Goal

The goal is to get the best, most accurate answer to the question of the user.

## Reporting

1. Generate a report of the upload operation

