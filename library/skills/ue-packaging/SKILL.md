---
name: ue-packaging
description: "Package, cook, and ship Unreal Engine 5 projects across desktop, console, server, and mobile. Covers Platforms packaging menu, Development vs Shipping configurations, Maps & Modes settings, and CI command-line automation via RunUAT BuildCookRun."
metadata:
  version: 2.0.0
---

# UE Packaging & Cooking (Build Automation)

Turn an Unreal Engine 5 project into a packaged, distributable build: configure platform targets, cook content into `.pak` containers, set launch maps, and automate packaging pipelines via `RunUAT BuildCookRun`.

## Context & Governance

Check project context in `.agents/ue-project-context.md` (or `docs/ue-project-context.md` / root `ue-project-context.md`).
- **Action Tiering**:
  - Auditing packaging settings, checking `GameDefaultMap` in `DefaultEngine.ini`: **Tier 1 (Autonomous Execution)**.
  - Modifying non-destructive packaging configs in ini files: **Tier 2 (Sandboxed Mutation)**.
  - Executing full `RunUAT BuildCookRun` builds or wiping build staging directories: **Tier 3 (Dual-Control Required)**.
- See [references/buildcookrun-commands.md](references/buildcookrun-commands.md) for complete CLI flag syntax for Windows, Linux, and Dedicated Servers.

---

## Core Packaging Pipeline

1. **Verify Default Map**:
   - `Config/DefaultEngine.ini` -> `[/Script/EngineSettings.GameMapsSettings] GameDefaultMap=/Game/Maps/EntryMap`.
   - Blank or invalid map paths will result in a black screen upon launching packaged builds.
2. **Select Build Configuration**:
   - **Development**: Contains developer console (`~`), profiling stats (`stat unit`), and logging. Used for internal QA testing.
   - **Shipping**: Strips console, logging, and debug symbols; applies maximum compiler optimization. Used for public distribution.
   - **Test**: Optimized like Shipping but retains profiling and telemetry tools for performance benchmarking.
3. **Packaging Execution**:
   - Run from editor: **Platforms** -> **[Target Platform]** -> **Package Project**.
   - Or run from CLI via `RunUAT.bat BuildCookRun` (see [references/buildcookrun-commands.md](references/buildcookrun-commands.md)).
4. **Post-Build Validation**:
   - Launch packaged executable outside the editor.
   - Verify log in `[PackagedFolder]/[ProjectName]/Saved/Logs/` for missing asset or shader compilation errors.
