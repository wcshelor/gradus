# Descriptive difficulty model v1

A descriptor is a direct score measurement. A factor is a reviewed descriptor
chosen for the overview. A profile is its sequence over regions. A peak is a
selected high relative value. A candidate section consolidates peak regions.
Contribution records describe score signals, not causes of learner difficulty.

## Values and comparisons

The public profile preserves each factor's raw units and applies within-piece
min-max normalization. The default composite is an equal-weight mean across
available selected factors. Missing values are excluded, not converted to zero.
Constant tracks normalize to zero and produce no distinct local peak.
Consequently a uniformly demanding piece can have no candidate sections.

Factor ordering uses the average normalized value over windows, multiplied by
its configured weight. It indicates sustained contribution to this chosen
profile, not a comparison of absolute demands across factors or pieces. The
same caution applies to the separately normalized left/right profiles: their
normalized values cannot establish which hand is absolutely harder.

The small default registry chooses one descriptor for each covered demand family.
It excludes overlapping density/span variants from the composite. Weights are
descriptive defaults and have no empirical pedagogical calibration.

## Locations and hands

ScoreRegion in temporal/windows.py is canonical. Positions are exact Fraction
values internally and fraction strings in JSON; printed measure numbers and
stable measure indices are both retained. Beat sizes count quarter notes.

Overview selection includes attacks in [start,end). Measure contexts are clipped
to the interval for rate denominators; written durations remain unchanged.
Notes sustaining into a region are not counted as attacks. Pairs spanning a
window start are omitted. This is an analysis view, not an exportable excerpt.
For hand views, event streams are filtered before extraction. Coordination is
computed only on the combined view. Hand-only descriptors use the maximum of
the two hands in the combined overview. Hand-specific profiles preserve their
separate values. Legacy Dynamics retains its documented mean-of-hands policy.

## Peaks and sections

The existing top-N, percentile and local-maxima implementations remain available
to experiments. The public default keeps the top positive normalized windows per
factor and composite (N is top_sections), suppressing zero/constant peaks.
Ties are resolved by score order. Overlapping or touching peak windows merge,
including transitive overlap. This can produce broad sections; original
support windows and peaks remain available for inspection.

Sections rank by the highest composite value among their supporting windows,
then distinct factor support, then score order. Contributions and their shares
refer to the named representative window, not an aggregate over the merged
section. Composite support is not counted as another independent factor.

## Evidence and limits

region_evidence lists the written/logical/source note IDs supplied to each
window computation. These are input provenance, not exact extrema attribution
or semantic explanations. Pitch transitions use closest pitch-set distance;
spans consider simultaneous attacks, not all sounding pitches. Performance
tempo, fingering, personal hand span, musical interpretation and learner data
are not incorporated in the selected v1 factors.

Source/parser warnings, method settings and registry/schema versions accompany
the report. Synthetic verification demonstrates stated calculations; teacher
agreement and learning benefit remain separate research questions.
