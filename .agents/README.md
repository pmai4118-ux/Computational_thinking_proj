# Project skills

These five skills were selected from
[wshobson/agents](https://github.com/wshobson/agents) and
[anthropics/skills](https://github.com/anthropics/skills) for development and UI
work in this project. The application's UI framework is still undecided.

| Skill | Purpose in this project |
| --- | --- |
| `python-project-structure` | Keep models, analysis, planning, storage, and interface modules understandable. |
| `python-error-handling` | Validate imported job data and handle malformed records or external-service failures. |
| `python-testing-patterns` | Verify normalization, skill-gap calculations, and learning-plan constraints using fixtures and mocks. |
| `frontend-design` | Plan visual hierarchy, typography, colors, layout, and interaction states for student-facing screens. |
| `wcag-audit-patterns` | Review keyboard access, labels, focus, contrast, and other accessibility concerns in a web interface. |

## Installation and provenance

- The Python skills use `wshobson/agents` at commit
  `46891e7e60da0e52baf1050b7b6391b64e84c6d9`, from
  `plugins/python-development/skills/`.
- `wcag-audit-patterns` uses the same repository and commit, from
  `plugins/accessibility-compliance/skills/wcag-audit-patterns/`.
- `frontend-design` uses `anthropics/skills` at commit
  `dbd4588f9e1033efb41dad4bef2f7947c8993d44`, from
  `skills/frontend-design/`.
- Installation date: `2026-10-11` (Asia/Saigon)
- Installation method: the bundled Codex skill-installer, with this repository's
  `.agents/skills` as the destination.
- Skill instructions and referenced examples were inspected. The installed
  packages contain instructions, Markdown references, and license text; they have
  no executable scripts or hooks.
- Installed upstream files are unchanged. Per-file SHA-256 hashes and exact
  source URLs are in [skills.lock.json](skills.lock.json).
- The upstream `wshobson/agents` MIT license is preserved in
  [THIRD_PARTY_LICENSES/wshobson-agents.LICENSE](THIRD_PARTY_LICENSES/wshobson-agents.LICENSE).
- The `frontend-design` Apache 2.0 license is included in
  [skills/frontend-design/LICENSE.txt](skills/frontend-design/LICENSE.txt).

## Usage

Codex discovers local skills in `.agents/skills/<name>/SKILL.md`. These skills
should be available on the next turn. If they do not appear, start a new Codex
session for this repository.

Example requests:

- "Use $python-project-structure to organize the skill-gap module."
- "Use $python-error-handling when implementing the job-data importer."
- "Use $python-testing-patterns to verify prerequisite ordering."
- "Use $frontend-design to design the student skill profile screen."
- "Use $wcag-audit-patterns to review the learning-plan screen's accessibility."

Project-specific guidance is in the root [AGENTS.md](../AGENTS.md). It explains
how to adapt the upstream examples to the actual project and dependency versions.

The earlier `.AGENT/.RULE` and `.AGENT/.SKILL` folders are placeholders. They
contain no active rules or skills; this installation uses the standard locations.

Official references:
[project instructions](https://learn.chatgpt.com/docs/agent-configuration/agents-md)
and [skill discovery](https://learn.chatgpt.com/docs/build-skills).
