# Feature Definitions and Status

| Feature | Formula (if known) | Status | Known ambiguity | MIDI Toolbox required |
|---|---|---|---|---|
| mean pitch | mean(note MIDI pitch) | partial | exact preprocessing/windowing | no |
| pitch deviation | std(note MIDI pitch) | todo | population vs sample std | no |
| pitch range | max(pitch)-min(pitch) | partial | note filtering rules | no |
| pitch entropy | entropy of pitch-class/pitch distribution | todo | binning/base/log base | no |
| hand displacement rate | unknown exact formula | todo | hand assignment and displacement definition | maybe |
| hand stretch | unknown exact formula | todo | hand span definition | maybe |
| deviation from middle C/C4 | likely mean(abs(pitch-60)) or signed dev | todo | absolute vs signed | no |
| black key rate | ratio of black-key notes | todo | enharmonic mapping assumptions | no |
| mean note duration | mean(duration) | todo | quantization and ties | no |
| note-duration deviation | std(duration) | todo | population vs sample std | no |
| playing speed | likely notes per time unit | todo | time unit and tempo handling | no |
| polyphony rate | likely multi-note-onset ratio | todo | onset tolerance | no |
| distinct stroke rate | unknown exact formula | todo | stroke/event definition | maybe |
| irregular rhythm | unknown exact formula | todo | rhythm irregularity metric choice | maybe |
| length | piece length | todo | in beats or seconds | no |
| tempo | tempo marking / derived BPM | todo | multi-tempo handling | no |
| key signature | key estimate/signature | todo | extraction method | maybe |
| CN chord number | count(chords) | todo | what qualifies as chord | no |
| ND note density | notes per unit time | partial | beats vs seconds | no |
| PVE pressing velocity entropy | entropy(velocity) | todo | velocity availability in MIDI | no |
| PV pitch variability | variability metric on pitch | todo | std/entropy/other | no |
| NDV note-duration variability | variability metric on duration | todo | metric definition | no |
| PVV pressing velocity variability | variability metric on velocity | todo | missing velocity values | no |
| PSV playing-speed variation | speed variability over segments | todo | segmentation strategy | no |
| SR staccato rate | ratio of staccato notes | todo | MIDI articulation inference quality | maybe |
| DNR dotted-note rate | ratio of dotted notes | todo | tuplet/tie handling | no |
| MC1 melody complexity | not fully specified | blocked | depends on expectancy model implementation | yes (likely) |
| MC2 melodic originality | not fully specified | blocked | depends on MIDI Toolbox expectancy outputs | yes (likely) |
| MC3 degree of melodiousness | not fully specified | blocked | depends on MIDI Toolbox expectancy outputs | yes (likely) |
