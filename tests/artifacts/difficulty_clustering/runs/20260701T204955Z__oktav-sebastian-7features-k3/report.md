# oktav_sebastian_7features_k3

This run keeps the label column out of PCA and clustering. Labels are used only after clustering for interpretation.

## Dataset
- dataset: `oktav`
- input matrix: `/Users/campshelor/Desktop/github-repos/piano-difficulty/tests/fixtures/oktav_demo_feature_matrix.csv`
- usable rows: 12
- usable features: 7
- clustering method: `ward_then_kmeans`
- clusters requested: 3

## Features Used
- `speedDifficulty`
- `displacementsDifficulty`
- `chordsDifficulty`
- `harmonyDifficulty`
- `rhythmDifficulty`
- `lengthDifficulty`
- `tonalityDifficulty`

## PCA Variance
- pc_1: 0.912 (cumulative 0.912)
- pc_2: 0.044 (cumulative 0.956)

## Cluster Sizes
- cluster 1: n=6, share=0.500
- cluster 2: n=3, share=0.250
- cluster 3: n=3, share=0.250

## Label Comparison
- adjusted rand index: 0.645
- normalized mutual information: 0.857
- cluster purity: 0.750
- label summary: mean=2.500, median=2.500, min=1.000, max=4.000

Cluster x label counts:

```text
difficulty_numeric  1  2  3  4
cluster                       
1                   0  0  3  3
2                   0  3  0  0
3                   3  0  0  0
```
