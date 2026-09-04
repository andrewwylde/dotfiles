# Niagara In-Engine MCP Tool Calling Reference (`NiagaraMCPBridge`)

The `NiagaraMCPBridge` in-editor plugin and `unreal-niagara-mcp` server expose structured mutation and diagnostic tools for controlling Niagara systems and emitters over JSON-RPC.

## Subsystem Tool Capabilities

### 1. Module Stack Management
| Tool Name | Parameters | Description | Risk Tier |
| :--- | :--- | :--- | :--- |
| `add_module` | `system_path`, `emitter_name`, `stage`, `module_name`, `index` | Inserts a module (e.g. `AddVelocity`, `GravityForce`, `ScaleColor`) into the designated stage stack. | Tier 2 (Sandboxed) |
| `remove_module` | `system_path`, `emitter_name`, `stage`, `module_name` | Removes a module from the emitter stage. | Tier 2 (Sandboxed) |
| `reorder_modules` | `system_path`, `emitter_name`, `stage`, `ordered_module_names` | Reorders module execution sequence (crucial for top-to-bottom data flow). | Tier 2 (Sandboxed) |
| `set_module_input` | `system_path`, `emitter_name`, `module_name`, `input_name`, `value` | Updates input values (floats, linear colors, vector curves, expressions). | Tier 2 (Sandboxed) |

### 2. System & Emitter Assembly
| Tool Name | Parameters | Description | Risk Tier |
| :--- | :--- | :--- | :--- |
| `add_emitter` | `system_path`, `emitter_preset_path`, `new_emitter_name` | Instantiates a new emitter from a template (e.g. Sprite Burst, Ribbon, Mesh). | Tier 2 (Sandboxed) |
| `remove_emitter` | `system_path`, `emitter_name` | Deletes an emitter from the system asset. | Tier 2 (Sandboxed) |
| `set_emitter_property`| `system_path`, `emitter_name`, `property_name`, `value` | Configures sim target (`CPUSim` vs `GPUComputeSim`), fixed bounds, or lifetime. | Tier 2 (Sandboxed) |
| `add_renderer` | `system_path`, `emitter_name`, `renderer_type`, `material_path` | Adds/configures Sprite, Mesh, Ribbon, or Light renderer with assigned material. | Tier 2 (Sandboxed) |

### 3. Procedural Shader Generation & Math
| Tool Name | Parameters | Description | Risk Tier |
| :--- | :--- | :--- | :--- |
| `generate_module_hlsl`| `system_path`, `emitter_name`, `module_name`, `hlsl_source` | Compiles custom dynamic HLSL expression inputs inside a Custom HLSL module. | Tier 2 (Sandboxed) |
| `create_particle_distribution` | `distribution_type`, `parameters` | Mathematically computes vector/curve distributions for initial velocity/spawn. | Tier 1 (Autonomous) |
| `create_procedural_system` | `target_path`, `system_definition_json` | Synthesizes an entire multi-emitter Niagara system from structured JSON schema. | Tier 2 (Sandboxed) |

### 4. Diagnostics & Auditing
| Tool Name | Parameters | Description | Risk Tier |
| :--- | :--- | :--- | :--- |
| `audit_niagara_system` | `system_path` | Audits parameter bindings, unlinked User parameters, and compilation status. | Tier 1 (Autonomous) |
| `audit_pooling` | `system_path` | Verifies whether pooling method is set to `AutoRelease` or `Manual` for high-frequency effects. | Tier 1 (Autonomous) |
| `audit_scalability` | `system_path` | Validates distance culling, max particle counts across Epic/High/Medium scalability tiers. | Tier 1 (Autonomous) |
| `preview_particle_count`| `system_path`, `duration_seconds` | Simulates particle counts and returns peak CPU/GPU memory footprint metrics. | Tier 1 (Autonomous) |
