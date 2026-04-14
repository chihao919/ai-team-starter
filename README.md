# AI Team Starter Kit

A ready-to-use framework for building an AI agent team with Claude Code.

## What's inside

```
├── CLAUDE.md                    ← Your AI team leader's guide (auto-loaded every conversation)
├── .claude/
│   ├── skills/
│   │   ├── CATALOG.md           ← Overview of all skills
│   │   ├── ai-team-architecture/← 3-layer architecture design + multi-model routing
│   │   ├── ogsm-framework/     ← OGSM strategic planning (with validators + scripts)
│   │   ├── ai-collab/          ← Multi-model task router (Claude/Gemini/Codex)
│   │   ├── ai-fallback/        ← Quota-aware fallback chain
│   │   ├── content-scout/      ← Blog idea extraction from technical content
│   │   ├── writing-guide/      ← Article writing standards
│   │   ├── security-check/     ← Pre-push secret scanner
│   │   ├── agent-builder/      ← Create/modify agent roles
│   │   └── example-skill/      ← Template for building your own skills
│   └── memory/
│       └── MEMORY.md            ← Lean index template
└── README.md                    ← You're reading it
```

## Skills included

| Category | Skills | Purpose |
|----------|--------|---------|
| **Architecture** | ai-team-architecture, ogsm-framework | Design agent teams with OGSM goals + 3-layer setup |
| **Multi-model** | ai-collab, ai-fallback | Route tasks to Claude/Gemini/Codex with fallback chains |
| **Content** | content-scout, writing-guide | Find article topics + enforce writing standards |
| **Utility** | security-check, agent-builder | Secret scanning + agent role management |

## Quick Start (5 minutes)

1. **Fork this repo**
2. **Open Claude Code** in the forked directory
3. Claude reads CLAUDE.md automatically and asks: *"Would you like to give me a name?"*
4. Tell it about your project — it sets up the team for you
5. Start working. Say what you need in plain language.

## How it works

You talk to ONE AI (your team leader). It dispatches a team of specialized agents:

```
You: "Write an article about X"
Team Leader: dispatches researchers + writers + reviewers (in parallel)
             → integrates results → delivers finished article
```

## Customize for your project

- **CLAUDE.md**: Edit the intent detection table for your workflows
- **Skills**: Add domain-specific skills using example-skill/ as a template
- **MEMORY.md**: Add your behavior preferences and skill pointers
- **CATALOG.md**: List your skills as you build them

## Based on

[How to Build an Effective AI Agent Team](https://watersonusa.ai/blog/claude-code-memory-skill-architecture/) — the methodology behind this starter kit.

## License

MIT — use it however you want.
