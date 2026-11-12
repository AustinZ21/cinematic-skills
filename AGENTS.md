# Instructions for AI agents

This repository contains two agent skills in `skills/`: `shot-director` and `still-to-film`. Each is a folder with a `SKILL.md` entry point.

## If the user asks you to install these skills

1. Clone the repository (or use this checkout).
2. Copy each folder in `skills/` into the user's skills directory. Use the cross-agent location `~/.agents/skills/` (Windows: `%USERPROFILE%\.agents\skills\`) unless your harness only discovers skills in its own directory (for example `~/.claude/skills/`, `~/.codex/skills/`, `~/.cursor/skills/`). Install to one location only.
3. If the target folder already exists, ask before overwriting, unless the user asked to update.
4. Tell the user which folders you copied and where.

`still-to-film` scripts need local tools (Python 3.10+, PyTorch, Transformers, OpenCV, FFmpeg, Node 18+). Do not install those unless the user asks; list them instead.

## If your harness does not support skills

Read `skills/shot-director/SKILL.md` before planning, prompting or reviewing any video, and `skills/still-to-film/SKILL.md` before turning still images into a film. Open the files under each skill's `references/` only when the SKILL.md points you to them.
