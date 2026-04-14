# Storyboard Tool Integration

The Storyboard Tool is the human-facing content editing interface that connects to the AI agent team workflow.

## What the Storyboard Tool Does

URL: [https://watersonusa.ai/tools/storyboard/](https://watersonusa.ai/tools/storyboard/)

The Storyboard Tool provides a visual, slide-by-slide editor for AIA CEU course content. It allows human editors to:

- View all course slides in sequence
- Edit slide content (text, images, interactive elements)
- Reorder slides via drag-and-drop
- Mark slides for agent review or rewrite
- Preview the final course output

This is the primary interface where human editorial decisions happen before the AI agent fleet executes the rewrite.

## How Edits Sync to Supabase

The Storyboard Tool uses Supabase as its backend database. When a user saves changes:

1. **Frontend** (Next.js) captures the edited slide data
2. **API call** writes the changes to the `course_slides` table in Supabase
3. **Timestamps** are updated (`updated_at` field) to signal which slides changed
4. **Change log** records who edited what and when

### Supabase Schema (relevant tables)

```
course_slides
├── id (uuid)
├── course_id (text, e.g., "HSW-002")
├── slide_number (int)
├── content (jsonb — slide text, images, metadata)
├── status (text — draft, review, approved, published)
├── updated_at (timestamp)
└── updated_by (text)

course_metadata
├── course_id (text)
├── title (text)
├── version (text)
├── ogsm_spec_path (text)
└── last_rewrite_at (timestamp)
```

## How /aia-rewrite Reads Changes and Dispatches the Fleet

When the user triggers `/aia-rewrite` after editing in the storyboard:

### Step 1: Detect changes
The skill queries Supabase for slides where `updated_at > last_rewrite_at`. These are the slides that need agent attention.

### Step 2: Load OGSM spec
The skill reads the course's OGSM spec (referenced in `course_metadata.ogsm_spec_path`) to get the full agent roster, Direction Seeds, and routing configuration.

### Step 3: Dispatch the 12-role fleet
The agent fleet is dispatched in waves:

| Wave | Agents | Task |
|------|--------|------|
| 1 | Investigators (2), Fact Checker | Research updated topics, verify claims |
| 2 | Persona Reviewers (3), Source Reviewer, Compliance Reviewer | Review from multiple perspectives |
| 3 | Writer, Copy Editor, Engineer (HTML), SEO Engineer, Bilingual Publisher | Rewrite, build, optimize, translate |

Each agent receives:
- The specific slides that changed (from Supabase query)
- Full Direction Seed (9 fields) from the OGSM spec
- Task-type routing configuration (which model to use)

### Step 4: Assemble and publish
The Commander reviews all agent outputs, resolves conflicts, and writes the final HTML back to the course directory.

## Integration Points with the Agent Team Workflow

```
Human Editor (Storyboard)
    │
    ▼
Supabase (course_slides table)
    │
    ▼
/aia-rewrite (detects changes)
    │
    ▼
OGSM Spec (loads agent roster)
    │
    ▼
Agent Fleet (12 roles, 3 waves)
    │
    ├── Gemini (research, verify, persona, seo)
    ├── Codex (code, review, html-build)
    └── Claude (writing, judgment, chinese)
    │
    ▼
Final HTML (written to course directory)
    │
    ▼
Vercel (auto-deploys on git push)
```

### Key design principle

Humans edit content in the storyboard. Agents execute the rewrite. The storyboard is the **intent capture layer** — it records what the human wants changed. The agent fleet is the **execution layer** — it performs research, review, and rewriting at scale.

This separation means:
- Humans don't need to understand the agent architecture
- Agents don't need to guess what the human wants
- Changes are traceable (Supabase change log -> agent dispatch log -> git commit)

## Connecting to Other References

- For OGSM spec structure: see [OGSM Quick Start](ogsm-quick-start.md)
- For model routing: see [Multi-Model Routing](multi-model-routing.md)
- For background execution during fleet dispatch: see [Background Execution](background-execution.md)
- For the 3-layer architecture that structures the agent knowledge: see [Three-Layer Setup](three-layer-setup.md)
