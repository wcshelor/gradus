# Difficulty Analysis

## Overview

- Title: Viva la Vida
- Composer: Unknown
- Source: /Users/campshelor/repos/gradus/research/learning_support/ceo_demo/data/source_scores/oktav_viva-la-vida_OK00009.xml
- Profile: difficulty_aspects (difficulty_aspects.v1)

## Difficulty Aspects

### Rhythmic demand

- Status: ready
- Features: 16
- Description: Temporal precision, subdivision variety, and density as notated.

### Pitch / movement demand

- Status: ready
- Features: 14
- Description: Distance and frequency of relocations between pitch regions between onsets.

### Hand-shape / span demand

- Status: partial
- Features: 7
- Description: Instantaneous hand extension or awkward vertical shaping within a simultaneous onset.

### Texture / polyphony demand

- Status: ready
- Features: 10
- Description: Concurrent voices/notes per unit time and vertical density.

### Coordination demand

- Status: ready
- Features: 4
- Description: Independence of the two hands in time, aligned vs asynchronous attacks and subdivision mismatch.

### Notation / reading demand

- Status: ready
- Features: 9
- Description: Decoding effort imposed by notation itself: accidentals, clef changes, cross-staff, ledger lines.

### Expression / control demand

- Status: partial
- Features: 14
- Description: Fine control of tone, articulation, and dynamics explicitly asked by written instructions.

### Structural / pattern demand

- Status: blocked
- Features: 4
- Description: Larger organization — repetition, pattern regularity, formal boundaries, predictability.

### Performance / interpretive demand

- Status: caveated
- Features: 15
- Description: Demands partly encoded in score and heavily learner-dependent: tone, velocity, voicing, timing nuance.

## Diagnostics

- Aspects are descriptive buckets, not a ranked composite.
- Aspect 8 (structural/pattern) is blocked: no pattern extractor yet; only contextual counts available.
- Aspect 9 (performance/interpretive) is caveated: partially observable from score, learner-dependent.
- All feature values reuse existing runtime extraction (extract_all); no new weights or formulas introduced.
- Temporal aspect series are mean of feature normalized traces per window; blocked aspects have no temporal signal.
- Aspect hotspots are ranked from aspect-composite demand; each hotspot lists aspect contributors with nested feature contributors.
- Blocked aspect (structural_pattern_demand) produces no temporal trace; caveated aspect (performance_interpretive_demand) uses written proxies only.
