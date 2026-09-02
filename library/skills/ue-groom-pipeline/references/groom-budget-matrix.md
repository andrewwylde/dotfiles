# Groom Strand Budget Matrix

Target strand counts and points-per-strand for real-time and cinematic groom assets exported to Unreal Engine 5 via Alembic.

## Real-Time Budgets (60 FPS Target)

| Category | Strand Count | Points/Strand | Total Points | Use Case |
|----------|-------------|---------------|-------------|----------|
| Humanoid Scalp Hair | 30,000–80,000 | 12–16 | ~960,000 | Hero character main hair |
| Humanoid Facial Hair | 10,000–30,000 | 4–8 | ~160,000 | Beard, mustache, stubble |
| Humanoid Eyebrows | 2,000–5,000 | 4–6 | ~24,000 | Brow arches |
| Humanoid Eyelashes | 500–2,000 | 4–6 | ~8,000 | Upper/lower lash line |
| Humanoid Peach Fuzz | 5,000–15,000 | 2–4 | ~40,000 | Face/arm vellus hair |
| Short Animal Fur | 50,000–150,000 | 4–6 | ~600,000 | Cat, dog, rodent body fur |
| Long Creature Mane | 20,000–50,000 | 8–12 | ~400,000 | Horse mane, lion mane, long tail |
| Creature Whiskers | 50–200 | 8–16 | ~2,000 | Cat/rodent whiskers |
| Stylized Guide Curves | 100–1,000 | 16–32 | ~16,000 | Physics simulation guides for Niagara |

## Cinematic Budgets (Offline / High-End)

| Category | Strand Count | Points/Strand | Notes |
|----------|-------------|---------------|-------|
| Hero Scalp Hair | 100,000–500,000 | 16–32 | Full strand simulation |
| Dense Fur | 200,000–1,000,000 | 4–8 | Pre-rendered close-ups |

## LOD Strategy

| LOD Level | Strand Reduction | Point Reduction | Trigger Distance |
|-----------|-----------------|-----------------|------------------|
| LOD0 (Hero) | 100% | 100% | 0–5m |
| LOD1 (Medium) | 50% | 75% | 5–15m |
| LOD2 (Far) | 25% | 50% | 15–30m |
| LOD3 (Distant) | 10% | 25% | 30m+ |

## Vertex Group Naming Convention

| Region | Vertex Group Name | Typical Character Type |
|--------|-------------------|------------------------|
| Scalp | `head_scalp` | Humanoid |
| Forehead Hairline | `head_hairline` | Humanoid |
| Beard | `face_beard` | Humanoid |
| Mustache | `face_mustache` | Humanoid |
| Eyebrows | `face_eyebrows` | Humanoid |
| Eyelashes | `face_eyelashes` | Humanoid |
| Body Fur | `body_fur` | Creature |
| Chest Fur | `chest_fur` | Creature |
| Tail Fur | `tail_fur` | Creature |
| Mane | `neck_mane` | Creature |
| Whiskers | `face_whiskers` | Creature |

## Rules

- Variable point counts per strand break physics solvers (Groom Rods, Groom Springs). Always use uniform counts within a groom group.
- Total strand count of 0 or exceeding max budget flags a parameter adjustment.
- Guide curves for Niagara physics must be a separate `groom_group_id` from render strands.
