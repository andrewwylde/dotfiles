# PCG Graph Rules & Architectural Supervision

Combining Large Language Models with Unreal Engine's PCG framework provides controlled spatial generation while avoiding the mesh artifacting common to direct 3D synthesis. The LLM serves as the high-level **architectural supervisor**, outputting structured node graphs, spatial constraints, and density rules.

## Core Node Graph Hierarchy

```
[Spatial Sampler (Surface / Mesh / Spline)]
    │  Generates initial point grid over terrain or bounding volume.
    ▼
[Density Filter / Noise Multiplier]
    │  Applies Perlin/Simplex noise or mathematical curve distribution.
    ▼
[Spatial Transform / Randomize]
    │  Applies yaw rotation (0-360), non-uniform scale variance (0.8x - 1.2x).
    ▼
[Difference / Collision Pruning]
    │  Subtracts roads, water bodies, or building exclusion bounds.
    ▼
[Static Mesh Spawner / HISM]
       Instantiates Hierarchical Instanced Static Meshes with weighted mesh variants.
```

---

## Standard PCG Spatial Rule Schemas

### 1. Forest & Foliage Distribution
- **Sampling Mode**: `Surface Sampler` with `PointsPerSquaredMeter = 0.05`
- **Slope Mask**: `NormalToDensity` filter (steepness < 35 degrees)
- **Scale Variance**: Min `(0.7, 0.7, 0.7)`, Max `(1.3, 1.3, 1.4)`
- **Self-Pruning**: Collision radius = 150 units

### 2. Urban / Roadside Scatter
- **Sampling Mode**: `Spline Sampler` (Subdivision distance = 400 units)
- **Offset Bounds**: Point Offset `Y = +/- 250 units` (along roadside curb)
- **Mesh Spawner**: Streetlamps, road barriers, trash bins with weighted mesh entries
