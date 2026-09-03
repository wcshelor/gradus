# Core Feature Registry

This file tracks the first stable feature families that the repository should
support before pedagogy-weighted scoring enters the picture.

## Direct feature families for v0

### Metadata and score context

- measure count
- note count
- pitch range
- tempo change count
- key change count
- meter change count

### Rhythm

- note density
- attack density
- shortest written duration
- tuplet count

### Pitch geometry

- per-hand maximum simultaneity span
- mean simultaneity span
- per-hand register range

### Leaps

- mean melodic leap by hand
- maximum melodic leap by hand
- leap threshold counts

### Texture

- notes per onset
- simultaneity density
- vertical density proxy

### Coordination

- aligned versus asynchronous hand onsets
- simple subdivision mismatch proxy

### Notation and reading

- accidental density
- clef change count
- cross-staff note count
- ledger-line burden

### Expression and written control

- articulated-note ratio
- common articulation ratios such as staccato, accent, and tenuto
- explicit dynamic-mark counts and changes
- crescendo and diminuendo wedge counts

## Feature contract

Each feature should eventually be emitted with:

- `feature_id`
- `scope`
- `scope_ref`
- `value`
- `units`
- `reliability`
- `source_span`
- `diagnostics`

This registry should stay focused on directly observable descriptors. Any
weighted scoring, pedagogical ranking, or interpretive proxy layer should be
added on top of these facts rather than mixed into them.
