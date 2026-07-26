# Reusable Custom Tools

Propose a custom tool only when repeated, fragile, multi-step, or deterministic work justifies it. Before creation, obtain the user-approved runtime, location, dependencies, side effects, and purpose unless settings already approve them.

Each tool must accept explicit parameters, validate input, provide `--help`, return clear status, avoid hard-coded paths/data, be safe to rerun when possible, include tests, and be registered in a manifest. Document purpose, prerequisites, commands, parameters, output/error behaviour, safety limits, and examples. Never install its runtime or dependencies without explicit user instruction.

Generic tools belong in this source folder; project-specific tools belong in the approved project location.
