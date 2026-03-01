---
name: "gitnexus"
description: "Codebase knowledge graph indexing and analysis tool. Invoke when user wants to index a repo, analyze code dependencies, or set up AI agent context."
---

# GitNexus

GitNexus is a tool that indexes any codebase into a knowledge graph — tracking every dependency, call chain, cluster, and execution flow — then exposes it through smart tools so AI agents never miss code.

## When to Use This Skill

Invoke this skill when:
- User wants to index a repository for AI agent context
- User needs to understand code dependencies and call chains
- User wants to analyze the impact of changes before making them
- User wants to set up MCP (Model Context Protocol) for AI editors like Claude Code, Cursor, or Windsurf
- User wants to generate a repository wiki from the knowledge graph
- User asks about code relationships, function calls, or architectural structure

## Quick Start

```bash
# Index your repo (run from repo root)
gitnexus analyze

# Force full re-index
gitnexus analyze --force

# Skip embedding generation (faster)
gitnexus analyze --skip-embeddings

# Configure MCP for your editor
gitnexus setup
```

## Available Commands

| Command | Description |
|---------|-------------|
| `gitnexus analyze [path]` | Index a repository (or update stale index) |
| `gitnexus analyze --force` | Force full re-index |
| `gitnexus analyze --skip-embeddings` | Skip embedding generation (faster) |
| `gitnexus setup` | Configure MCP for your editors (one-time) |
| `gitnexus mcp` | Start MCP server (stdio) — serves all indexed repos |
| `gitnexus serve` | Start local HTTP server (multi-repo) for web UI connection |
| `gitnexus list` | List all indexed repositories |
| `gitnexus status` | Show index status for current repo |
| `gitnexus clean` | Delete index for current repo |
| `gitnexus clean --all --force` | Delete all indexes |
| `gitnexus wiki [path]` | Generate repository wiki from knowledge graph |
| `gitnexus wiki --model <model>` | Wiki with custom LLM model (default: gpt-4o-mini) |
| `gitnexus wiki --base-url <url>` | Wiki with custom LLM API base URL |

## MCP Tools (7 tools exposed via MCP)

These tools are available when running `gitnexus mcp`:

| Tool | What It Does |
|------|--------------|
| `list_repos` | Discover all indexed repositories |
| `query` | Process-grouped hybrid search (BM25 + semantic + RRF) |
| `context` | 360-degree symbol view — categorized refs, process participation |
| `impact` | Blast radius analysis with depth grouping and confidence |
| `detect_changes` | Git-diff impact — maps changed lines to affected processes |
| `rename` | Multi-file coordinated rename with graph + text search |
| `cypher` | Raw Cypher graph query |

## Editor Support

| Editor | MCP | Skills | Hooks (auto-augment) |
|--------|-----|--------|---------------------|
| Claude Code | Yes | Yes | Yes (PreToolUse) |
| Cursor | Yes | Yes | — |
| Windsurf | Yes | — | — |
| OpenCode | Yes | Yes | — |

Claude Code gets the deepest integration: MCP tools + agent skills + PreToolUse hooks that automatically enrich grep/glob/bash calls with knowledge graph context.

## Usage Examples

### Analyze current repository
```bash
gitnexus analyze
```

### Analyze a specific path
```bash
gitnexus analyze /path/to/repo
```

### Setup MCP for Claude Code
```bash
gitnexus setup
# or manually:
# claude mcp add gitnexus -- npx -y gitnexus@latest mcp
```

### Check index status
```bash
gitnexus status
```

### List all indexed repos
```bash
gitnexus list
```

### Generate wiki for the repo
```bash
gitnexus wiki
```

### Clean index
```bash
gitnexus clean              # Delete index for current repo
gitnexus clean --all --force  # Delete all indexes
```

## Notes

- GitNexus stores data locally using KuzuDB (native, fast, persistent)
- Everything stays local — no network required for CLI usage
- Tree-sitter is used for parsing (native bindings)
- The knowledge graph tracks every relationship, not just descriptions
