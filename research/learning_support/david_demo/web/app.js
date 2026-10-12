// Demo launcher — static wrapper over stored piece manifests (catalog-driven).
// Visible graph: 6 learner-facing difficulty dimensions (gradus.front_graph_taxonomy.v2).
// Chart toggles are graph dimensions; hotspots list contributors. 9-aspect
// backend taxonomy (difficulty_aspects.v1) is shown as coverage/provenance only.
(function () {
  const CATALOG_URL_LIVE = '/api/catalog';
  const CATALOG_URL_STATIC = '../artifacts/pieces.json';
  const FALLBACK_CATALOG = [
    {
      id: 'debussy_arabesque_1',
      title: 'Arabesque No. 1',
      composer: 'Claude Debussy',
      difficultyTag: 'Henle 4',
      manifestUrl: '../artifacts/debussy_arabesque_1/demo_manifest.json',
      artifactBase: '../artifacts/debussy_arabesque_1/',
      enabled: true,
    },
  ];

  let PIECE_CATALOG = [];

  // 6 learner-facing graph dimensions — visible chart colors
  const GRAPH_DIMENSION_COLORS = {
    'finger_dexterity': '#c1121f',
    'hand_movement_position': '#9d4edd',
    'layers_coordination': '#d4a017',
    'rhythm_timing': '#4a6fa5',
    'expression_sound_control': '#2a6b8a',
    'notation_reading': '#e07a00',
  };
  // Keep 9-aspect colors for provenance panel / legacy manifests
  const ASPECT_COLORS = {
    'rhythmic_demand': '#4a6fa5',
    'pitch_movement_demand': '#c1121f',
    'hand_shape_span_demand': '#9d4edd',
    'texture_polyphony_demand': '#6a994e',
    'coordination_demand': '#d4a017',
    'notation_reading_demand': '#e07a00',
    'expression_control_demand': '#2a6b8a',
    'structural_pattern_demand': '#6b7280',
    'performance_interpretive_demand': '#9a3412',
  };
  // Legacy fallback for old manifests
  const FACTOR_COLORS = {
    'coordination.subdivision_mismatch_proxy': '#4a6fa5',
    'rhythm.attack_density': '#6a994e',
    'pitch_geometry.max_simultaneity_span': '#9d4edd',
    'leaps.max_melodic_leap': '#c1121f',
    'notation.accidental_density': '#e07a00',
  };
  const COMPOSITE_COLOR = '#1d3557';

  // ── Glossary for plain-language explanations (v0 heuristic layer) ──
  // 6 user-facing graph dimensions (visible chart) — per design brief
  const GRAPH_GLOSSARY = {
    'finger_dexterity': { plain: 'finger dexterity', label: 'Finger Dexterity' },
    'hand_movement_position': { plain: 'hand movement', label: 'Hand Movement' },
    'layers_coordination': { plain: 'coordination', label: 'Coordination' },
    'rhythm_timing': { plain: 'rhythm & timing', label: 'Rhythm & Timing' },
    'expression_sound_control': { plain: 'expression', label: 'Expression' },
    'notation_reading': { plain: 'reading', label: 'Reading' }
  };
  // 9-aspect backend taxonomy (provenance panel only)
  const ASPECT_GLOSSARY = {
    'rhythmic_demand': { plain: 'rhythm', label: 'Rhythmic demand' },
    'pitch_movement_demand': { plain: 'pitch movement', label: 'Pitch / movement demand' },
    'hand_shape_span_demand': { plain: 'hand shape and span', label: 'Hand-shape / span demand' },
    'texture_polyphony_demand': { plain: 'texture and polyphony', label: 'Texture / polyphony demand' },
    'coordination_demand': { plain: 'hand coordination', label: 'Coordination demand' },
    'notation_reading_demand': { plain: 'notation reading', label: 'Notation / reading demand' },
    'expression_control_demand': { plain: 'expression and control', label: 'Expression / control demand' },
    'structural_pattern_demand': { plain: 'structure and patterns', label: 'Structural / pattern demand' },
    'performance_interpretive_demand': { plain: 'interpretive nuance', label: 'Performance / interpretive demand' }
  };
  const FEATURE_GLOSSARY = {
    'rhythm.note_density': 'note density',
    'rhythm.attack_density': 'attack density',
    'rhythm.shortest_written_duration': 'shortest written duration',
    'rhythm.significant_shortest_value': 'shortest notable note value',
    'rhythm.tuplet_count': 'tuplet presence',
    'leaps.mean_melodic_leap': 'average melodic leap',
    'leaps.max_melodic_leap': 'largest melodic leap',
    'leaps.max_timed_difficult_displacement': 'largest harder timed displacement',
    'leaps.timed_difficult_displacement_ratio': 'share of harder timed displacements',
    'metadata.pitch_range': 'pitch range',
    'pitch_geometry.max_simultaneity_span': 'widest simultaneous span',
    'pitch_geometry.mean_simultaneity_span': 'average simultaneous span',
    'pitch_geometry.register_range': 'register range',
    'texture.notes_per_onset': 'notes per onset',
    'texture.vertical_density_proxy': 'average sounding notes',
    'texture.chord_ratio': 'share of chord onsets',
    'texture.chord_count': 'chord onsets',
    'coordination.subdivision_mismatch_proxy': 'subdivision mismatch (proxy)',
    'coordination.aligned_hand_onset_ratio': 'share of aligned hand onsets',
    'notation.accidental_density': 'accidental density',
    'notation.accidental_count': 'accidental count',
    'expression.dynamic_marking_count': 'dynamic marking count',
    'expression.crescendo_start_count': 'crescendo hairpins',
    'expression.diminuendo_start_count': 'diminuendo hairpins',
    'expression.dynamic_change_count': 'dynamic change count'
  };
  function plainAspect(id) { return (ASPECT_GLOSSARY[id] && ASPECT_GLOSSARY[id].plain) || id.replace(/_/g,' '); }
  function plainGraph(id) { return (GRAPH_GLOSSARY[id] && GRAPH_GLOSSARY[id].plain) || id.replace(/_/g,' '); }
  function resolvePlain(contrib) {
    var dim = (contrib && (contrib.dimension_id || contrib.graph_dimension_id || contrib.aspect_id || contrib.feature_id || contrib.id)) || '';
    if (GRAPH_GLOSSARY[dim]) return plainGraph(dim);
    if (ASPECT_GLOSSARY[dim]) return plainAspect(dim);
    return String(dim).replace(/_/g,' ').replace(/\//g,' / ');
  }
  function plainFeature(fid, label) { return FEATURE_GLOSSARY[fid] || (label ? label.replace(/_/g,' ').replace(/\./g,' · ') : fid.replace(/_/g,' ').replace(/\./g,' · ')); }
  function strengthLabel(v) {
    if (typeof v !== 'number' || isNaN(v)) return 'unknown';
    if (v >= 0.75) return 'very high';
    if (v >= 0.55) return 'high';
    if (v >= 0.33) return 'moderate';
    return 'low';
  }
  function roleLabel(rank) { if (rank===1) return 'primary'; if (rank===2||rank===3) return 'secondary'; return 'supporting'; }
  // Phase 1 — conservative observation builder (JS parity with hotspot_explanation.py)
  var FEATURE_OBSERVATION_MAP = {
    'coordination.asynchronous_hand_onset_count': 'the hands do not always land together',
    'coordination.asynchronous_hand_onset_ratio': 'the hands do not always land together',
    'coordination.aligned_hand_onset_count': 'the hands do not always land together',
    'coordination.aligned_hand_onset_ratio': 'the hands do not always land together',
    'coordination.subdivision_mismatch_proxy': 'the hands do not always land together',
    'texture.notes_per_onset': 'several notes need to line up cleanly',
    'texture.simultaneity_density': 'several notes need to line up cleanly',
    'texture.vertical_density_proxy': 'several notes need to line up cleanly',
    'texture.chord_count': 'several notes need to line up cleanly',
    'texture.chord_ratio': 'several notes need to line up cleanly',
    'texture.octave_chord_ratio': 'several notes need to line up cleanly',
    'leaps.mean_melodic_leap': 'the hand has to move across a wider shape',
    'leaps.max_melodic_leap': 'the hand has to move across a wider shape',
    'leaps.count_ge_5': 'the hand has to move across a wider shape',
    'leaps.count_ge_8': 'the hand has to move across a wider shape',
    'leaps.count_ge_12': 'the hand has to move across a wider shape',
    'leaps.timed_difficult_displacement_ratio': 'the hand has to move across a wider shape',
    'leaps.max_timed_difficult_displacement': 'the hand has to move across a wider shape',
    'leaps.timed_difficult_displacement_count': 'the hand has to move across a wider shape',
    'metadata.pitch_range': 'the hand has to move across a wider shape',
    'pitch_geometry.max_simultaneity_span': 'the hand has to move across a wider shape',
    'pitch_geometry.mean_simultaneity_span': 'the hand has to move across a wider shape',
    'pitch_geometry.register_range': 'the hand has to move across a wider shape',
    'rhythm.note_density': 'timing has less room for adjustment',
    'rhythm.attack_density': 'timing has less room for adjustment',
    'rhythm.shortest_written_duration': 'timing has less room for adjustment',
    'rhythm.tuplet_count': 'timing has less room for adjustment',
    'rhythm.significant_shortest_value': 'timing has less room for adjustment',
    'rhythm.asymmetric_tuplet_measure_ratio': 'timing has less room for adjustment',
    'rhythm.polyrhythm_measure_ratio': 'timing has less room for adjustment',
    'rhythm.polyrhythm_flag': 'timing has less room for adjustment',
    'rhythm.duration_value_ratio': 'timing has less room for adjustment',
    'statistics.duration_mean': 'timing has less room for adjustment',
    'statistics.duration_std': 'timing has less room for adjustment',
    'statistics.duration_variability': 'timing has less room for adjustment',
    'expression.articulated_note_ratio': 'dynamic or articulation control has to stay consistent while the notes change',
    'expression.articulation_density': 'dynamic or articulation control has to stay consistent while the notes change',
    'expression.staccato_note_ratio': 'dynamic or articulation control has to stay consistent while the notes change',
    'expression.accent_note_ratio': 'dynamic or articulation control has to stay consistent while the notes change',
    'expression.strong_accent_note_ratio': 'dynamic or articulation control has to stay consistent while the notes change',
    'expression.tenuto_note_ratio': 'dynamic or articulation control has to stay consistent while the notes change',
    'expression.dynamic_marking_count': 'dynamic or articulation control has to stay consistent while the notes change',
    'expression.dynamic_marking_rate': 'dynamic or articulation control has to stay consistent while the notes change',
    'expression.dynamic_change_count': 'dynamic or articulation control has to stay consistent while the notes change',
    'expression.dynamic_range_span': 'dynamic or articulation control has to stay consistent while the notes change',
    'expression.wedge_start_count': 'dynamic or articulation control has to stay consistent while the notes change',
    'expression.crescendo_start_count': 'dynamic or articulation control has to stay consistent while the notes change',
    'expression.diminuendo_start_count': 'dynamic or articulation control has to stay consistent while the notes change',
    'expression.staff_specific_dynamic_ratio': 'dynamic or articulation control has to stay consistent while the notes change',
    'notation.accidental_density': 'reading load may be higher because of accidentals or dense notation',
    'notation.accidental_count': 'reading load may be higher because of accidentals or dense notation',
    'notation.accidental_ratio': 'reading load may be higher because of accidentals or dense notation',
    'notation.clef_change_count': 'reading load may be higher because of accidentals or dense notation',
    'notation.cross_staff_note_count': 'reading load may be higher because of accidentals or dense notation',
    'notation.ledger_line_burden': 'reading load may be higher because of accidentals or dense notation',
    'statistics.black_key_rate': 'reading load may be higher because of accidentals or dense notation'
  };
  var DIMENSION_OBSERVATION_MAP = {
    'layers_coordination': 'the hands do not always land together',
    'hand_movement_position': 'the hand has to move across a wider shape',
    'rhythm_timing': 'timing has less room for adjustment',
    'expression_sound_control': 'dynamic or articulation control has to stay consistent while the notes change',
    'notation_reading': 'reading load may be higher because of accidentals or dense notation',
    'finger_dexterity': 'timing has less room for adjustment'
  };
  var OBSERVATION_REASON = {
    'the hands do not always land together': 'Keeping the parts together while each hand follows its own timing adds coordination pressure.',
    'several notes need to line up cleanly': 'Voicing and balancing several notes at once makes it harder to keep the sound even.',
    'the hand has to move across a wider shape': 'Covering larger intervals or wider shapes makes it harder to land accurately.',
    'timing has less room for adjustment': 'Shorter values and varied rhythms leave less time to adjust between notes.',
    'dynamic or articulation control has to stay consistent while the notes change': 'Shaping loudness and touch consistently while the notes move adds control work.',
    'reading load may be higher because of accidentals or dense notation': 'More symbols to read means extra attention before the hands can play fluently.',
    'the hands do not always land together, so coordination has to stay steady between layers': 'Keeping independent layers aligned while each hand follows its own timing adds coordination pressure.',
    'dynamic shaping happens while the notes are changing, so control has to stay consistent through the motion': 'Shaping loudness and touch while the notes move adds control work that has to stay even through the motion.',
    'the passage combines wider hand movement with timing precision': 'Large shifts combined with timing precision leave less room to recover between moves.',
    'one hand moves across a wider shape while the other keeps another layer active': 'One hand has to cover distance while the other sustains a separate layer, so balance and independence matter.',
    'the left hand moves across a wider shape while the right hand keeps another layer active': 'One hand has to cover distance while the other sustains a separate layer, so balance and independence matter.',
    'the right hand moves across a wider shape while the left hand keeps another layer active': 'One hand has to cover distance while the other sustains a separate layer, so balance and independence matter.',
    'one part sustains while another part moves, so balance and coordination matter': 'Holding one part steady while another moves asks for balance and independent control.'
  };
  // Phase 2 — semantic observation extraction (JS parity; conservative. Full hand/contour detail is Python-only when scope data missing.)
  function _dimValue(evidence, dimId) {
    var dims = (evidence && evidence.dimensions) || [];
    for (var i=0;i<dims.length;i++) if (dims[i].dimension_id===dimId && typeof dims[i].normalized_value==='number') return dims[i].normalized_value;
    return null;
  }
  function _hasMicro(evidence, idSet, threshold) {
    var micros = (evidence && evidence.micro_features) || [];
    var best=null, bestNv=-1;
    for (var i=0;i<micros.length;i++) {
      var fid=micros[i].feature_id||'';
      if (!idSet[fid]) continue;
      var nv=micros[i].normalized_value;
      var nvf=typeof nv==='number'?nv:-1;
      if (nvf>bestNv){bestNv=nvf; best=micros[i];}
      if (nvf>=threshold) return [true, micros[i]];
    }
    if (best && bestNv>=threshold) return [true, best];
    return [false, best];
  }
  function buildSemanticObservations(evidence) {
    var dims=(evidence&&evidence.dimensions)||[];
    var micros=(evidence&&evidence.micro_features)||[];
    if (!dims.length && !micros.length) return [];
    var coordAsyncIds={'coordination.asynchronous_hand_onset_count':1,'coordination.asynchronous_hand_onset_ratio':1,'coordination.aligned_hand_onset_ratio':1,'coordination.subdivision_mismatch_proxy':1};
    var textureIds={'texture.notes_per_onset':1,'texture.simultaneity_density':1,'texture.vertical_density_proxy':1,'texture.chord_count':1,'texture.chord_ratio':1,'texture.octave_chord_ratio':1};
    var leapIds={'leaps.mean_melodic_leap':1,'leaps.max_melodic_leap':1,'leaps.count_ge_5':1,'leaps.count_ge_8':1,'leaps.count_ge_12':1,'leaps.timed_difficult_displacement_ratio':1,'leaps.max_timed_difficult_displacement':1,'leaps.timed_difficult_displacement_count':1,'metadata.pitch_range':1,'pitch_geometry.max_simultaneity_span':1,'pitch_geometry.mean_simultaneity_span':1,'pitch_geometry.register_range':1};
    var rhythmIds={'rhythm.note_density':1,'rhythm.attack_density':1,'rhythm.shortest_written_duration':1,'rhythm.tuplet_count':1,'rhythm.significant_shortest_value':1,'rhythm.asymmetric_tuplet_measure_ratio':1,'rhythm.polyrhythm_measure_ratio':1,'rhythm.polyrhythm_flag':1,'rhythm.duration_value_ratio':1,'statistics.duration_mean':1,'statistics.duration_std':1,'statistics.duration_variability':1};
    var exprIds={'expression.articulated_note_ratio':1,'expression.articulation_density':1,'expression.staccato_note_ratio':1,'expression.accent_note_ratio':1,'expression.strong_accent_note_ratio':1,'expression.tenuto_note_ratio':1,'expression.dynamic_marking_count':1,'expression.dynamic_marking_rate':1,'expression.dynamic_change_count':1,'expression.dynamic_range_span':1,'expression.wedge_start_count':1,'expression.crescendo_start_count':1,'expression.diminuendo_start_count':1,'expression.staff_specific_dynamic_ratio':1};
    var handV=_dimValue(evidence,'hand_movement_position'), rhythmV=_dimValue(evidence,'rhythm_timing'), coordV=_dimValue(evidence,'layers_coordination'), exprV=_dimValue(evidence,'expression_sound_control'), fingerV=_dimValue(evidence,'finger_dexterity');
    var observations=[];
    var hasCoordAsync= _hasMicro(evidence, coordAsyncIds, 0.45), hasCoord=hasCoordAsync[0], coordMicro=hasCoordAsync[1];
    var hasLeap= _hasMicro(evidence, leapIds, 0.55), hasLeapB=hasLeap[0], leapMicro=hasLeap[1];
    var hasRhythm= _hasMicro(evidence, rhythmIds, 0.45), hasRhythmB=hasRhythm[0], rhythmMicro=hasRhythm[1];
    var hasExpr= _hasMicro(evidence, exprIds, 0.45), hasExprB=hasExpr[0], exprMicro=hasExpr[1];
    var hasTexture= _hasMicro(evidence, textureIds, 0.45), hasTextureB=hasTexture[0], textureMicro=hasTexture[1];
    // 1 coordination offset
    if (coordV!=null && coordV>=0.40 && (hasCoord || coordV>=0.55) && coordV>=0.45 && (hasCoord || coordV>=0.50)) {
      observations.push({kind:'coordination_offset', text:'the hands do not always land together, so coordination has to stay steady between layers', confidence: (coordV>=0.55&&hasCoord)?'high':'medium', support_level: hasCoord?'strong':'moderate', evidence:['layers_coordination'].concat(coordMicro? [coordMicro.feature_id]:[])});
    }
    // 2 movement+timing
    if (handV!=null && rhythmV!=null && handV>=0.45 && rhythmV>=0.35 && (hasLeapB||handV>=0.50) && (hasRhythmB||rhythmV>=0.50) && hasLeapB && hasRhythmB) {
      observations.push({kind:'movement_plus_timing', text:'the passage combines wider hand movement with timing precision', confidence: (handV>=0.55&&rhythmV>=0.45)?'high':'medium', support_level:'strong', evidence:['hand_movement_position','rhythm_timing'].concat(leapMicro?[leapMicro.feature_id]:[]).concat(rhythmMicro?[rhythmMicro.feature_id]:[])});
    }
    // 3 expression over motion
    var hasWedge=false; for(var i=0;i<micros.length;i++){var fid=micros[i].feature_id||'';if((fid==='expression.wedge_start_count'||fid==='expression.crescendo_start_count'||fid==='expression.diminuendo_start_count')&&typeof micros[i].raw_value==='number'&&micros[i].raw_value>0) hasWedge=true;}
    if (exprV!=null && exprV>=0.40 && hasExprB) {
      var motionActive=(handV!=null&&handV>=0.35)||(rhythmV!=null&&rhythmV>=0.35)||(fingerV!=null&&fingerV>=0.40);
      if (motionActive && (hasLeapB||hasRhythmB||(handV||0)>=0.45||(rhythmV||0)>=0.45)) {
        observations.push({kind:'expression_over_motion', text:'dynamic shaping happens while the notes are changing, so control has to stay consistent through the motion', confidence: exprV>=0.55?'high':'medium', support_level: hasWedge?'strong':'moderate', evidence:['expression_sound_control'].concat(exprMicro?[exprMicro.feature_id]:[]).concat(handV!=null&&handV>=0.35?['hand_movement_position']:[]).concat(rhythmV!=null&&rhythmV>=0.35?['rhythm_timing']:[])});
      }
    }
    // 4 hand layer active
    var handAttrib=null; for(var i=0;i<micros.length;i++){var fid2=micros[i].feature_id||'';if(leapIds[fid2]&&typeof micros[i].normalized_value==='number'&&micros[i].normalized_value>=0.55){var sr=micros[i].scope_ref||micros[i].hand||'';if(sr==='left'||sr==='right'){handAttrib=sr;break;}}}
    if (handV!=null && handV>=0.45 && hasLeapB) {
      var layerActive=(coordV!=null&&coordV>=0.35)||hasTextureB||hasCoord;
      if (layerActive) {
        var txt= handAttrib==='left'? 'the left hand moves across a wider shape while the right hand keeps another layer active' : handAttrib==='right'? 'the right hand moves across a wider shape while the left hand keeps another layer active' : 'one hand moves across a wider shape while the other keeps another layer active';
        observations.push({kind:'hand_layer_active', text:txt, confidence: (handAttrib&&coordV>=0.45)?'high':'medium', support_level: handAttrib?'strong':'moderate', evidence:['hand_movement_position'].concat(coordV!=null&&coordV>=0.35?['layers_coordination']:['texture']).concat(leapMicro?[leapMicro.feature_id]:[]).concat(textureMicro?[textureMicro.feature_id]:[])});
      }
    }
    // 5 sustain vs move
    if (hasTextureB && hasCoord && coordV!=null && coordV>=0.30) {
      var hasSust=false; for(var i=0;i<micros.length;i++){var f=micros[i].feature_id||'';if((f==='texture.vertical_density_proxy'||f==='texture.simultaneity_density'||f==='texture.notes_per_onset')&&typeof micros[i].normalized_value==='number'&&micros[i].normalized_value>=0.45){hasSust=true;break;}}
      if (hasSust || coordV>=0.40) observations.push({kind:'sustained_vs_moving', text:'one part sustains while another part moves, so balance and coordination matter', confidence:'medium', support_level:'moderate', evidence:['layers_coordination'].concat(textureMicro?[textureMicro.feature_id]:[]).concat(coordMicro?[coordMicro.feature_id]:[])});
    }
    // dedupe and prioritize high confidence
    var seen={}; var dedup=[]; observations.sort(function(a,b){var order={'high':0,'medium':1,'low':2}; return (order[a.confidence]||1)-(order[b.confidence]||1);});
    for(var i=0;i<observations.length;i++){var t=observations[i].text; if(!seen[t]){seen[t]=1; dedup.push(observations[i]);}}
    return dedup.slice(0,2);
  }
  function buildObservationsFromEvidence(evidence) {
    // Phase 2: prefer semantic observations when supported; fallback to Phase 1 generic map
    var semantic = buildSemanticObservations(evidence);
    if (semantic && semantic.length) {
      var texts = semantic.map(function(o){ return o.text; }).filter(function(t){ return !!t; });
      if (texts.length) return texts.slice(0,2);
    }
    var dims = (evidence && evidence.dimensions) || [];
    var micros = (evidence && evidence.micro_features) || [];
    var candidates = [];
    micros.forEach(function(m){
      var fid = m.feature_id || '';
      var phrase = FEATURE_OBSERVATION_MAP[fid];
      if (!phrase) return;
      var nv = m.normalized_value;
      var strength = typeof nv==='number' ? nv : -1;
      candidates.push({strength: strength, phrase: phrase, fid: fid});
    });
    candidates.sort(function(a,b){ return b.strength - a.strength; });
    var seen = {};
    var obs = [];
    candidates.forEach(function(c){
      if (!seen[c.phrase] && obs.length < 2) { seen[c.phrase]=true; obs.push(c.phrase); }
    });
    if (!obs.length && dims.length) {
      dims.slice(0,2).forEach(function(d){
        var did = d.dimension_id || '';
        var phrase = DIMENSION_OBSERVATION_MAP[did];
        if (phrase && !seen[phrase] && obs.length < 2) { seen[phrase]=true; obs.push(phrase); }
      });
      if (!obs.length) obs.push('control and coordination need to stay steady while the notes change');
    }
    if (!obs.length) obs.push('the musical texture shifts here, so steadiness and balance need attention');
    return obs.slice(0,2);
  }
  function buildLearnerSummaryFromEvidence(evidence, measure_range) {
    var dims = (evidence && evidence.dimensions) || [];
    var mr = measure_range || 'this passage';
    var hasStrong = dims.slice(0,2).some(function(d){ return typeof d.normalized_value==='number' && d.normalized_value>=0.5; });
    if (dims.length && !hasStrong) {
      var obsD = buildObservationsFromEvidence(evidence);
      var s1d = obsD.length===1 ? 'In measures ' + mr + ', ' + obsD[0] + '.' : 'In measures ' + mr + ', ' + obsD[0] + ' and ' + obsD[1] + '.';
      var primaryObsD = obsD[0] || 'the musical texture shifts here, so steadiness and balance need attention';
      var s2d = OBSERVATION_REASON[primaryObsD] || 'That pattern makes it harder to keep the playing steady and even.';
      if (obsD.length===2) {
        var secondObsD = obsD[1];
        var secondReasonD = OBSERVATION_REASON[secondObsD] || '';
        if (secondReasonD && secondReasonD !== s2d) {
          s2d = s2d + ' At the same time, ' + secondObsD + ' — ' + secondReasonD.charAt(0).toLowerCase() + secondReasonD.slice(1);
        }
      }
      var s3d = 'Overall the demands are fairly balanced here, so no single type dominates.';
      var summaryD = [s1d, s2d, s3d].join(' ');
      var whyD = obsD.length===1 ? (OBSERVATION_REASON[obsD[0]] || s2d) : (OBSERVATION_REASON[obsD[0]] || s2d) + ' Here it coincides with ' + obsD[1] + ', so both demands need attention at once.';
      return { summary: summaryD, why: whyD, observations: obsD };
    }
    var obs = buildObservationsFromEvidence(evidence);
    var s1 = obs.length===1 ? 'In measures ' + mr + ', ' + obs[0] + '.' : 'In measures ' + mr + ', ' + obs[0] + ' and ' + obs[1] + '.';
    var primaryObs = obs[0] || 'the musical texture shifts here, so steadiness and balance need attention';
    var s2 = OBSERVATION_REASON[primaryObs] || 'That pattern makes it harder to keep the playing steady and even.';
    if (obs.length===2) {
      var secondObs = obs[1];
      var secondReason = OBSERVATION_REASON[secondObs] || '';
      if (secondReason && secondReason !== s2) {
        s2 = s2 + ' At the same time, ' + secondObs + ' — ' + secondReason.charAt(0).toLowerCase() + secondReason.slice(1);
      }
    }
    var s3 = '';
    if (dims.length) {
      var pPlain = dims[0].plain || dims[0].dimension_id || 'unknown';
      var secondStrong = false;
      var sPlain = '';
      if (dims.length >= 2) {
        sPlain = dims[1].plain || dims[1].dimension_id || '';
        var nv = dims[1].normalized_value;
        if (typeof nv==='number' && nv >= 0.33) secondStrong = true;
        else if (dims[1].strength==='moderate' || dims[1].strength==='high' || dims[1].strength==='very high') secondStrong = true;
      }
      if (secondStrong && sPlain) s3 = 'That is why the passage is classified mainly as ' + pPlain + ', with ' + sPlain + ' also involved.';
      else s3 = 'That is why the passage is classified mainly as ' + pPlain + '.';
    }
    var parts = [s1, s2];
    if (s3) parts.push(s3);
    var summary = parts.join(' ');
    var why;
    if (obs.length===1) why = OBSERVATION_REASON[obs[0]] || s2;
    else why = (OBSERVATION_REASON[obs[0]] || s2) + ' Here it coincides with ' + obs[1] + ', so both demands need attention at once.';
    return { summary: summary, why: why, observations: obs };
  }
  function buildProvenanceSummaryFromEvidence(evidence, measure_range) {
    var mr = measure_range || 'this window';
    var dims = (evidence && evidence.dimensions) || [];
    var micro = (evidence && evidence.micro_features) || [];
    var score_value = evidence && evidence.score_value;
    var rel = (evidence && evidence.relative_strength) || 'unknown';
    var base = '';
    if (!dims.length) {
      base = 'The score-derived evidence for this window is distributed — no single dimension stands out strongly. The trace suggests a modest, shared contribution across dimensions within this piece (not a calibrated grade).';
    } else {
      var hasStrong = dims.slice(0,2).some(function(d){ return typeof d.normalized_value==='number' && d.normalized_value>=0.5; });
      if (!hasStrong) {
        var names = dims.slice(0,2).map(function(d){ return d.plain || ''; }).join(', ');
        base = 'The score-derived evidence points to a distributed pattern in measures ' + mr + ': ' + names + ' are the relatively higher signals, but all remain moderate or lower. This suggests no single demand dominates here — the window sits close to the piece average.';
      } else {
        var primary = dims[0];
        var pPlain = primary.plain || 'unknown';
        var pStrength = primary.strength || 'unknown';
        var pRole = primary.role || 'primary';
        var elevated = dims.filter(function(d){ return typeof d.normalized_value==='number' && d.normalized_value>=0.5; });
        if (dims.length>=2 && elevated.length>=2) {
          var secondary = dims[1];
          var sPlain = secondary.plain || 'unknown';
          var sStrength = secondary.strength || 'unknown';
          base = 'The score-derived evidence suggests measures ' + mr + ' stand out mainly for ' + pPlain + ' (' + pStrength + ', ' + pRole + '), with secondary support from ' + sPlain + ' (' + sStrength + '). The signal is relative within this piece, not a calibrated grade or learner diagnosis.';
        } else {
          base = 'The score-derived evidence points to ' + pPlain + ' as the primary contributor in measures ' + mr + ' (' + pStrength + '). The other dimensions are lower in this window. The signal is relative within this piece.';
        }
      }
      if (micro.length) {
        var sorted = micro.slice().sort(function(a,b){ return (b.normalized_value||0)-(a.normalized_value||0); }).slice(0,3);
        var clauses = sorted.map(function(f){
          var plain = f.plain || f.feature_id;
          var raw = f.raw_value;
          var units = f.units ? ' ' + f.units : '';
          var norm = typeof f.normalized_value==='number' ? ' (normalized ' + f.normalized_value.toFixed(2) + ', ' + (f.strength||strengthLabel(f.normalized_value)) + ')' : '';
          if (typeof raw==='number') return plain + ' — ' + fmt(raw) + units + norm;
          if (typeof f.normalized_value==='number') return plain + norm;
          return plain;
        }).join('; ');
        base += ' Supporting micro-features: ' + clauses + '.';
      }
    }
    if (typeof score_value==='number') base += ' Composite around ' + score_value.toFixed(2) + ' — ' + rel + ' (relative within this piece, normalized).';
    if (dims.length) {
      var vals = dims.slice(0,3).map(function(d){ return d.plain + ' ' + (typeof d.normalized_value==='number' ? d.normalized_value.toFixed(2) : 'n/a'); }).join(', ');
      base += ' Normalized contributors: ' + vals + '.';
    }
    return base;
  }
  function buildFallbackExplanation(h, chart) {
    var measure_range = h.measure_range || '';
    if (!measure_range || measure_range==='unknown') {
      var nums = h.measure_numbers || [];
      if (nums.length >=2) measure_range = nums[0]+'\u2013'+nums[nums.length-1];
      else if (nums.length===1) measure_range = String(nums[0]);
      else measure_range = 'this passage';
    }
    var score_value = (h.score_value!=null? h.score_value : h.score);
    var contributors = (h.dimension_contributors || h.graph_dimension_contributors || h.top_contributors || h.contributions || h.aspect_contributors || h.feature_contributions || []).slice();
    contributors.sort(function(a,b){ return (a.rank||99)-(b.rank||99); });
    var top = contributors.slice(0,3);
    var elevated = top.filter(function(c){ return typeof c.normalized_value==='number' && c.normalized_value>=0.5; });
    var hasStrong = contributors.slice(0,2).some(function(c){ return typeof c.normalized_value==='number' && c.normalized_value>=0.5; });
    var headline, score_cue, timeline_context=null;
    if (top.length) {
      var leadPlain = resolvePlain(top[0]);
      var leadStrength = strengthLabel(top[0].normalized_value);
      headline = 'Measures ' + measure_range + ' \u2014 ' + leadPlain + ' stands out (' + leadStrength + ')';
    } else {
      headline = 'Measures ' + measure_range + ' \u2014 distributed evidence';
    }
    // Phase 1: learner-facing explanation from conservative observation builder
    var evidenceForSummary = buildFallbackEvidenceBrief(h, chart, null);
    evidenceForSummary.measure_range = measure_range;
    evidenceForSummary.score_value = score_value;
    if (typeof score_value==='number' && !evidenceForSummary.relative_strength) {
      var sv2 = score_value;
      evidenceForSummary.relative_strength = sv2>=0.55? 'relatively high for this piece' : sv2>=0.42? 'above the piece average' : sv2>=0.32? 'near the piece average' : 'relatively modest for this piece';
    }
    var learner = buildLearnerSummaryFromEvidence(evidenceForSummary, measure_range);
    var summary = learner.summary;
    var aspect_interplay = learner.why;
    var provenance_summary = buildProvenanceSummaryFromEvidence(evidenceForSummary, measure_range);
    // Provenance interplay preserves old system language for debug drawer
    var provenance_interplay = (function(){
      if (!contributors.length) return 'No contributor data is available for this passage \u2014 the explanation is limited to position and overall score.';
      var hasStrongLocal = contributors.slice(0,2).some(function(c){ return typeof c.normalized_value==='number' && c.normalized_value>=0.5; });
      if (!hasStrongLocal) return 'The evidence is distributed \u2014 the score-derived signals are broadly similar across the top dimensions, so no clear interplay dominates. This passage reflects a balanced, average section.';
      var elevatedLocal = top.filter(function(c){ return typeof c.normalized_value==='number' && c.normalized_value>=0.5; });
      if (elevatedLocal.length>=2) {
        var nms = elevatedLocal.slice(0,3).map(function(c){ return resolvePlain(c); });
        if (nms.indexOf('hand shape and span')!==-1 && nms.indexOf('texture and polyphony')!==-1) return 'Two or more dimensions are elevated together \u2014 ' + nms.slice(0,2).join(', ') + ' \u2014 which suggests that multiple notes sounding together coincides with wider hand shapes here.';
        if (nms.indexOf('finger dexterity')!==-1 && nms.indexOf('hand movement')!==-1) return 'Finger dexterity and hand movement stand out together, suggesting dexterity demands coincide with larger relocations. The interplay is relative to this piece.';
        return 'More than one dimension is elevated \u2014 ' + nms.join(', ') + ' \u2014 which suggests these demands coincide here. The overlap is descriptive within the piece.';
      }
      return 'The primary signal is ' + resolvePlain(top[0]) + '; the other dimensions are lower here, so this passage is mainly shaped by that one demand. The evidence suggests a focused rather than combined pattern.';
    })();
    if (typeof score_value==='number') {
      var level = score_value>=0.55? 'relatively high for this piece' : score_value>=0.42? 'above the piece average' : score_value>=0.32? 'near the piece average' : 'relatively modest for this piece';
      score_cue = 'Overall around ' + score_value.toFixed(2) + ' \u2014 ' + level + '. Key passage #' + (h.rank||'?') + '; the value is a descriptive mean, not a grade.';
    } else {
      score_cue = 'Overall is not available for this passage \u2014 the ranking is relative within the piece, not a grade.';
    }
    if (chart && chart.regions) {
      var total = chart.regions.length;
      var rep = h.representative_region||{};
      var winIdx = (typeof rep.window_index==='number'? rep.window_index : (h.supporting_window_indices && h.supporting_window_indices[0]));
      if (typeof winIdx==='number' && total) {
        var pct = winIdx/Math.max(1,total-1);
        var where = pct<0.2? 'near the opening' : pct<0.4? 'in the early-middle' : pct<0.6? 'around the middle' : pct<0.8? 'in the late-middle' : 'toward the end';
        timeline_context = 'Part ' + (winIdx+1) + ' of ' + total + ' ' + where + ' (measures ' + measure_range + '). Position is descriptive \u2014 it does not imply a learning order.';
      }
    }
    // Phase 2: semantic observations (structured) are evidence-backed; JS fallback is conservative and mirrors Python thresholds where data exists.
    // Full hand/contour detail is Python-only when manifest lacks note-level scope data.
    var semanticStructured = buildSemanticObservations(evidenceForSummary);
    if (semanticStructured && semanticStructured.length) {
      try {
        var clauses = semanticStructured.map(function(s){ var ev=(s.evidence||[]).join(', '); return ev ? s.kind + ': \"' + s.text + '\" [' + ev + ']' : s.kind + ': \"' + s.text + '\"'; });
        provenance_summary = provenance_summary + ' Semantic observations (evidence-backed): ' + clauses.join('; ') + '.';
      } catch(e){}
    }
    return { headline: headline, summary: summary, aspect_interplay: aspect_interplay, dimension_interplay: aspect_interplay, provenance_summary: provenance_summary, provenance_interplay: provenance_interplay, learner_observations: learner.observations, semantic_observations: semanticStructured, score_cue: score_cue, timeline_context: timeline_context, confidence: 'heuristic', version: 'david_heuristic.v3' };
  }
  // ── Three-layer evidence helpers (JS parity with hotspot_explanation.py) ──
  function buildFallbackEvidenceBrief(h, chart, piece) {
    if (h.evidence || h.evidence_brief) return h.evidence || h.evidence_brief;
    var measure_range = h.measure_range || '';
    if (!measure_range || measure_range==='unknown') {
      var nums = h.measure_numbers || [];
      if (nums.length >=2) measure_range = nums[0]+'\u2013'+nums[nums.length-1];
      else if (nums.length===1) measure_range = String(nums[0]);
      else measure_range = 'this passage';
    }
    var score_value = (h.score_value!=null? h.score_value : h.score);
    var contributors = (h.dimension_contributors || h.graph_dimension_contributors || h.top_contributors || h.contributions || h.aspect_contributors || h.feature_contributions || []).slice();
    contributors.sort(function(a,b){ return (a.rank||99)-(b.rank||99); });
    var dims = contributors.slice(0,3).map(function(c){
      var dimId = c.dimension_id || c.graph_dimension_id || c.aspect_id || c.feature_id || c.id || '';
      return {
        rank: c.rank,
        dimension_id: dimId,
        plain: resolvePlain(c),
        normalized_value: c.normalized_value,
        strength: strengthLabel(c.normalized_value),
        role: roleLabel(c.rank),
        contribution_share: c.contribution_share,
        is_peak_support: !!c.is_peak_support
      };
    });
    var micro = [];
    var budgets = [3,2,1];
    contributors.slice(0,3).forEach(function(c, idx){
      var budget = budgets[idx] || 0;
      var feats = c.feature_contributors || c.supporting_feature_contributors || c.graph_contributors || [];
      feats.slice().sort(function(a,b){ return (a.rank||99)-(b.rank||99); }).slice(0,budget).forEach(function(f){
        if (micro.length < 6) micro.push({
          feature_id: f.feature_id,
          plain: plainFeature(f.feature_id, f.label || f.feature_name || ''),
          parent_dimension_id: c.dimension_id || c.graph_dimension_id || '',
          raw_value: f.raw_value,
          normalized_value: f.normalized_value,
          strength: strengthLabel(f.normalized_value),
          units: f.units,
          scope: f.scope,
          scope_ref: f.scope_ref || f.hand
        });
      });
    });
    var total = chart && chart.regions ? chart.regions.length : null;
    var rep = h.representative_region || {};
    var winIdx = typeof rep.window_index==='number' ? rep.window_index : (h.supporting_window_indices && h.supporting_window_indices[0]);
    if (typeof winIdx!=='number' && typeof h.window_index==='number') winIdx = h.window_index;
    return {
      evidence_version: 'david_evidence.v1',
      piece_identity: piece || null,
      measure_range: measure_range,
      measure_numbers: h.measure_numbers || [],
      window_index: winIdx,
      total_windows: total,
      score_value: score_value,
      dimensions: dims,
      micro_features: micro,
      peak_support_flags: contributors.filter(function(c){return c.is_peak_support;}).map(function(c){return c.dimension_id || c.graph_dimension_id;}),
      source: { taxonomy_version: (chart && (chart.taxonomy_version || chart.graph_taxonomy_version)) || 'gradus.front_graph_taxonomy.v2' }
    };
  }
  // Practice cue fallback from top dimension — conservative suggestion, not diagnosis
  function practiceCueForDimension(dimId) {
    var id = String(dimId || '').toLowerCase();
    if (id.indexOf('rhythm') !== -1) return 'Try a slow pulse, clap or count the subdivision, then play at a comfortable tempo.';
    if (id.indexOf('hand_movement') !== -1 || id.indexOf('hand position') !== -1) return 'Isolate the larger jumps or position shifts, practise the move slowly and check hand placement against the score.';
    if (id.indexOf('layers_coordination') !== -1 || id.indexOf('coordination') !== -1 || id.indexOf('layers') !== -1) return 'Try hands separately, then combine slowly — listen for alignment before adding tempo.';
    if (id.indexOf('finger_dexterity') !== -1 || id.indexOf('finger') !== -1) return 'Work in small groups (2–4 notes), slowly and evenly, then connect the groups.';
    if (id.indexOf('expression') !== -1) return 'Sing or observe the dynamic shape, then reproduce it with light, controlled touch at a slow tempo.';
    if (id.indexOf('notation') !== -1) return 'Scan the notation first — note accidentals or ledger lines — then play slowly while reading.';
    return 'Play this passage slowly at first, focusing on accuracy before tempo.';
  }
  function headlineShortPhrase(headline, measure_range) {
    if (!headline) return '';
    // Heuristic headline is "Measures X-Y — phrase (strength)" — extract phrase part
    var sep = headline.indexOf('\u2014');
    if (sep === -1) sep = headline.indexOf('—');
    if (sep === -1) sep = headline.indexOf('-');
    if (sep !== -1) {
      var tail = headline.slice(sep + 1).trim();
      // Remove leading measure repetition if present
      return tail;
    }
    return headline.replace(/^Measures\s+[^\s]+\s*[—–-]\s*/i, '').trim() || headline;
  }
  function conciseSummary(text) {
    if (!text) return '';
    // Avoid verbose raw evidence in first view — strip trailing micro-feature clause
    var idx = text.indexOf(' Supporting micro');
    if (idx !== -1) return text.slice(0, idx).trim();
    idx = text.indexOf(' Supporting micro-components');
    if (idx !== -1) return text.slice(0, idx).trim();
    idx = text.indexOf(' Supporting micro-features');
    if (idx !== -1) return text.slice(0, idx).trim();
    return text;
  }
  function getDisplayExplanation(h, chart, piece) {
    var evidence = h.evidence || h.evidence_brief || buildFallbackEvidenceBrief(h, chart, piece);
    var heuristic = h.heuristic_explanation || h.explanation || buildFallbackExplanation(h, chart);
    var llm = h.llm_explanation || null;
    var llmValid = false;
    // Prefer LLM only when hash-valid and status ready (spec: hash-valid / status ready)
    var status = (h.llm_status || (llm && llm.status) || '').toString().toLowerCase();
    var statusReady = status === 'ready' || status === 'ok';
    // If manifest explicitly marks hash_mismatch / stale, treat as not ready
    if (status && (status.indexOf('mismatch') !== -1 || status.indexOf('stale') !== -1 || status.indexOf('pending') !== -1)) statusReady = false;
    if (llm && evidence && llm.evidence_hash && evidence.evidence_hash) {
      llmValid = llm.evidence_hash === evidence.evidence_hash && statusReady;
    } else {
      llmValid = false;
    }
    if (llmValid) return { layer: 'llm', prose: heuristic, llm: llm, evidence: evidence, heuristic: heuristic };
    if (heuristic && heuristic.summary) return { layer: 'heuristic', prose: heuristic, evidence: evidence, heuristic: heuristic };
    return { layer: 'evidence', prose: null, evidence: evidence, heuristic: null };
  }

  const state = {
    manifest: null,
    manifestBase: '',
    enabled: new Set(),
    compositeEnabled: true,
    selectedId: null,
    selectedPieceId: null,
  };

  // Phase 3: grouped hard bits are learner-facing; raw hotspots are provenance
  function getPrimaryHotspots(m) {
    if (!m) return [];
    if (Array.isArray(m.hard_bits) && m.hard_bits.length) return m.hard_bits;
    if (Array.isArray(m.practice_regions) && m.practice_regions.length) return m.practice_regions;
    if (Array.isArray(m.grouped_hard_bits) && m.grouped_hard_bits.length) return m.grouped_hard_bits;
    return m.hotspots || [];
  }
  function getProvenanceHotspots(m) {
    return (m && m.hotspots) || [];
  }
  function isHardBit(h) {
    return !!(h && (h.core_region || h.display_region || h.practice_region || h.hard_bit_id));
  }

  // DOM
  const btnLoad = document.getElementById('btn-load');
  const loadError = document.getElementById('load-error');
  const viewLoad = document.getElementById('view-load');
  const viewChart = document.getElementById('view-chart');
  const pieceListEl = document.getElementById('piece-list');
  const catalogCountEl = document.getElementById('catalog-count');
  const catalogStatusEl = document.getElementById('catalog-status');
  const pieceMeta = document.getElementById('piece-meta');
  const factorToggles = document.getElementById('factor-toggles');
  const toggleComposite = document.getElementById('toggle-composite');
  const btnShowAll = document.getElementById('btn-show-all');
  const btnHideAll = document.getElementById('btn-hide-all');
  const chartSvg = document.getElementById('chart-svg');
  const chartXLabels = document.getElementById('chart-x-labels');
  const hotspotList = document.getElementById('hotspot-list');
  const detailEmpty = document.getElementById('detail-empty');
  const detailContent = document.getElementById('detail-content');
  const caveatsList = document.getElementById('caveats-list');
  const snippetGlobal = document.getElementById('snippet-global-status');
  const btnBack = document.getElementById('btn-back-to-load');
  // Open in MuseScore — secondary action near title
  const pieceHeader = document.getElementById('piece-header');
  const btnOpenScore = document.getElementById('btn-open-score');
  const openScoreStatus = document.getElementById('open-score-status');
  let openScoreLiveAvailable = null;
  // Details provenance (hidden in disclosure)
  const aspectsPanel = document.getElementById('aspects-panel');
  const aspectsGrid = document.getElementById('aspects-grid');
  const aspectsNotice = document.getElementById('aspects-notice');
  const aspectsInterpretation = document.getElementById('aspects-interpretation');
  const aspectsSchema = document.getElementById('aspects-schema');
  const aspectsCount = document.getElementById('aspects-count');
  const aspectsProfileVersion = document.getElementById('aspects-profile-version');
  const aspectsDiagnostics = document.getElementById('aspects-diagnostics');
  const aspectsWarnings = document.getElementById('aspects-warnings');

  initCatalog();

  if (btnLoad) btnLoad.addEventListener('click', loadManifest);
  if (btnBack) btnBack.addEventListener('click', function () {
    viewChart.classList.add('hidden');
    viewLoad.classList.remove('hidden');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
  toggleComposite.addEventListener('change', function () {
    state.compositeEnabled = toggleComposite.checked;
    renderChart();
  });
  if (btnShowAll) btnShowAll.addEventListener('click', function () { setAllDimensions(true); });
  if (btnHideAll) btnHideAll.addEventListener('click', function () { setAllDimensions(false); });

  function setAllDimensions(show) {
    var m = state.manifest;
    if (!m) return;
    var chartSeries = m.chart.series || {};
    var order = m.chart.graph_dimension_ids || m.chart.dimension_ids || m.chart.factor_ids || Object.keys(chartSeries);
    if (show) {
      order.forEach(function (id) {
        var s = chartSeries[id];
        if (!s) return;
        if (s.blocked) return;
        var vals = s.normalized_values || s.smoothed_values || [];
        var hasData = Array.isArray(vals) && vals.some(function (v) { return v != null && !isNaN(v); });
        if (!hasData) return;
        state.enabled.add(id);
      });
    } else {
      order.forEach(function (id) { state.enabled.delete(id); });
    }
    renderToggles(m);
    renderChart();
  }

  // ── Open in MuseScore (local demo convenience — requires live server) ──
  if (btnOpenScore) {
    btnOpenScore.addEventListener('click', handleOpenScore);
  }
  // Probe live-server availability once at startup (quietly)
  probeOpenScoreAvailability();

  async function fetchCatalogFrom(url) {
    var res = await fetch(url, { cache: 'no-cache' });
    if (!res.ok) throw new Error('HTTP ' + res.status + ' for ' + url);
    var data = await res.json();
    var pieces = data.pieces || data || [];
    if (!Array.isArray(pieces) || pieces.length === 0) throw new Error('Empty catalog at ' + url);
    return pieces;
  }

  async function initCatalog() {
    if (pieceListEl) pieceListEl.innerHTML = '<div class="small muted" style="padding:8px">Loading pieces…</div>';
    if (catalogStatusEl) { catalogStatusEl.textContent = ''; catalogStatusEl.classList.add('hidden'); }
    if (loadError) { loadError.classList.add('hidden'); loadError.textContent = ''; }
    var pieces = null;
    var source = null;
    var lastErr = null;
    // Try live API first, then static file. Missing CIPI/Oktav roots must not hide catalog.
    try {
      pieces = await fetchCatalogFrom(CATALOG_URL_LIVE);
      source = 'live';
    } catch (eLive) {
      lastErr = eLive;
      console.warn('Live catalog fetch failed, trying static:', eLive);
      try {
        pieces = await fetchCatalogFrom(CATALOG_URL_STATIC);
        source = 'static';
      } catch (eStatic) {
        lastErr = eStatic;
        console.warn('Static catalog fetch also failed:', eStatic);
      }
    }
    if (pieces) {
      PIECE_CATALOG = pieces.map(function (p) {
        var isReady = (p.status || 'ready') === 'ready';
        var title = p.title || p.id;
        var composer = p.composer || '';
        var shortLabel = '';
        if (p.difficulty_label) {
          shortLabel = p.difficulty_label.split(' (')[0].trim();
        }
        return {
          id: p.id,
          title: title,
          composer: composer,
          difficultyTag: shortLabel,
          subtitle: shortLabel || p.dataset || '',
          manifestUrl: p.manifest_url || p.manifestUrl || ('../artifacts/' + p.id + '/demo_manifest.json'),
          artifactBase: p.artifact_base || p.artifactBase || ('../artifacts/' + p.id + '/'),
          enabled: isReady,
          raw: p,
        };
      });
      if (catalogCountEl) catalogCountEl.textContent = PIECE_CATALOG.length + ' pieces';
      if (catalogStatusEl) { catalogStatusEl.textContent = ''; catalogStatusEl.classList.add('hidden'); }
      if (loadError) { loadError.classList.add('hidden'); loadError.textContent = ''; }
    } else {
      console.warn('Catalog load failed, using fallback:', lastErr);
      PIECE_CATALOG = FALLBACK_CATALOG.slice();
      if (catalogCountEl) catalogCountEl.textContent = PIECE_CATALOG.length + ' pieces';
      if (catalogStatusEl) { catalogStatusEl.textContent = ''; catalogStatusEl.classList.add('hidden'); }
      if (loadError) {
        loadError.textContent = 'Catalog not available. Please try again.';
        loadError.classList.remove('hidden');
      }
    }
    // Keep selectedPieceId for fallback compatibility but not used for selection UI
    var preferred = PIECE_CATALOG.find(function (p) { return p.id === 'debussy_arabesque_1' && p.enabled; });
    var firstEnabled = PIECE_CATALOG.find(function (p) { return p.enabled; });
    var chosen = preferred || firstEnabled || PIECE_CATALOG[0] || null;
    if (chosen) state.selectedPieceId = chosen.id;
    renderPieceList();
    // Update catalog header count even if catalog loaded via static fallback
    if (catalogCountEl && PIECE_CATALOG.length) catalogCountEl.textContent = PIECE_CATALOG.length + ' pieces';
  }

  function getSelectedPiece() {
    return PIECE_CATALOG.find(function (p) { return p.id === state.selectedPieceId; }) || null;
  }

  function renderPieceList() {
    if (!pieceListEl) return;
    pieceListEl.innerHTML = '';
    if (!PIECE_CATALOG.length) {
      pieceListEl.innerHTML = '<div class="small muted" style="padding:8px">No pieces available.</div>';
      return;
    }
    var visible = PIECE_CATALOG.filter(function (p) { return p.enabled; });
    visible.forEach(function (p) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'piece-row';
      btn.setAttribute('role', 'option');
      btn.setAttribute('data-piece-id', p.id);
      var tagHtml = p.difficultyTag ? '<span class="piece-tag">' + esc(p.difficultyTag) + '</span>' : '';
      var titleText = p.title || p.id;
      var composerText = p.composer || '';
      btn.innerHTML = '<span class="piece-row-main"><span class="piece-row-title">' + esc(titleText) + '</span>' +
        '<span class="piece-row-composer">' + esc(composerText) + '</span></span>' + tagHtml;
      btn.addEventListener('click', function () {
        state.selectedPieceId = p.id;
        loadPiece(p);
      });
      pieceListEl.appendChild(btn);
    });
    var disabled = PIECE_CATALOG.filter(function (p) { return !p.enabled; });
    disabled.forEach(function (p) {
      var row = document.createElement('button');
      row.type = 'button';
      row.className = 'piece-row';
      row.disabled = true;
      row.setAttribute('aria-disabled', 'true');
      var tagHtml = p.difficultyTag ? '<span class="piece-tag">' + esc(p.difficultyTag) + '</span>' : '';
      var titleText = p.title || p.id;
      var composerText = p.composer || '';
      row.innerHTML = '<span class="piece-row-main"><span class="piece-row-title">' + esc(titleText) + '</span>' +
        '<span class="piece-row-composer">' + esc(composerText) + '</span></span>' + tagHtml;
      pieceListEl.appendChild(row);
    });
    if (visible.length === 0 && disabled.length > 0) {
      var msg = document.createElement('div');
      msg.className = 'small muted';
      msg.style.padding = '8px';
      msg.textContent = 'No ready pieces.';
      pieceListEl.appendChild(msg);
    }
  }

  async function loadPiece(piece) {
    if (!piece) return;
    if (loadError) { loadError.classList.add('hidden'); loadError.textContent = ''; }
    var manifestUrl = piece.manifestUrl;
    state.manifestBase = piece.artifactBase || manifestUrl.slice(0, manifestUrl.lastIndexOf('/') + 1);
    if (btnLoad) { btnLoad.disabled = true; btnLoad.textContent = 'Loading\u2026'; }
    try {
      var res = await fetch(manifestUrl, { cache: 'no-cache' });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      var data = await res.json();
      if (!data.chart || !data.hotspots) {
        throw new Error('Invalid manifest: missing chart/hotspots');
      }
      var graphIds = data.chart.graph_dimension_ids || data.chart.dimension_ids || [];
      var aspectProbe = data.chart.aspect_ids || data.chart.factor_ids || [];
      if (graphIds.length !== 6) {
        console.warn('Manifest chart does not have 6 graph dimension ids, found', graphIds.length, ' (aspect_ids fallback length', aspectProbe.length, ')');
        if (graphIds.length === 0 && aspectProbe.length === 9) {
          console.error('Graph taxonomy missing: manifest has 9 aspect_ids but no graph_dimension_ids — regenerate artifacts with front_graph_taxonomy.v2');
        }
      }
      if (data.difficulty_aspects && data.difficulty_aspects.aspects && data.difficulty_aspects.aspects.length !== 9) {
        console.warn('Provenance difficulty_aspects expected 9, found', data.difficulty_aspects.aspects.length);
      }
      state.selectedPieceId = piece.id;
      applyManifest(data, state.manifestBase);
    } catch (err) {
      if (loadError) {
        var titleText = piece.title || piece.id;
        loadError.textContent = 'Could not load "' + titleText + '". Please try another piece.';
        loadError.classList.remove('hidden');
      }
      if (btnLoad) { btnLoad.disabled = false; btnLoad.textContent = 'Load selected piece'; }
      console.error(err);
    }
  }

  async function loadManifest() {
    var piece = getSelectedPiece();
    if (!piece) {
      if (loadError) {
        loadError.textContent = 'Please choose a piece.';
        loadError.classList.remove('hidden');
      }
      return;
    }
    return loadPiece(piece);
  }

  function validateManifestOrThrow(data) {
    if (!data.chart || !data.hotspots) throw new Error('Invalid manifest: missing chart/hotspots');
    var graphIds = data.chart.graph_dimension_ids || data.chart.dimension_ids || [];
    var aspectProbe = data.chart.aspect_ids || data.chart.factor_ids || [];
    if (graphIds.length !== 6) {
      console.warn('Manifest chart does not have 6 graph dimension ids, found', graphIds.length, ' (aspect_ids fallback length', aspectProbe.length, ')');
      if (graphIds.length === 0 && aspectProbe.length === 9) {
        console.error('Graph taxonomy missing: manifest has 9 aspect_ids but no graph_dimension_ids — regenerate artifacts with front_graph_taxonomy.v2');
      }
    }
    if (data.difficulty_aspects && data.difficulty_aspects.aspects && data.difficulty_aspects.aspects.length !== 9) {
      console.warn('Provenance difficulty_aspects expected 9, found', data.difficulty_aspects.aspects.length);
    }
  }

  function applyManifest(data, manifestBase) {
    validateManifestOrThrow(data);
    state.manifest = data;
    state.manifestBase = manifestBase;
    var ids = (data.chart.graph_dimension_ids && data.chart.graph_dimension_ids.length) ? data.chart.graph_dimension_ids : (data.chart.dimension_ids && data.chart.dimension_ids.length ? data.chart.dimension_ids : (data.chart.factor_ids || []));
    state.enabled = new Set();
    ids.forEach(function (id) {
      var series = data.chart.series && data.chart.series[id];
      if (series && series.blocked) return;
      state.enabled.add(id);
    });
    if (state.enabled.size === 0 && ids.length) {
      ids.slice(0,3).forEach(function (id) { state.enabled.add(id); });
    }
    state.compositeEnabled = true;
    if (toggleComposite) toggleComposite.checked = true;
    onLoaded();
  }

  function onLoaded() {
    var m = state.manifest;
    if (viewLoad) viewLoad.classList.add('hidden');
    if (viewChart) viewChart.classList.remove('hidden');
    if (btnLoad) { btnLoad.disabled = false; btnLoad.textContent = 'Load selected piece'; }
    renderMeta(m);
    renderToggles(m);
    renderCaveats(m);
    renderAspects(m);
    renderChart();
    renderHotspotList();
    var primary = getPrimaryHotspots(m);
    if (primary && primary.length) {
      selectHotspot(primary[0].id);
    }
    updateOpenScoreUI();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // ── Open in MuseScore helpers ──
  var CURATED_IDS = ['beethoven_fur_elise','beethoven_bagatelle_119_10','mozart_k545','chopin_waltz_a_minor_kk_ivb_11','chopin_prelude_e_minor_28_4','chopin_prelude_a_major_28_7','debussy_arabesque_1','debussy_clair_de_lune','satie_gymnopedie_1','oktav_le_onde','oktav_a_thousand_miles','oktav_viva_la_vida'];
  function hasResolvableLocalScorePath(piece) {
    if (!piece) return false;
    var id = piece.id || piece.piece_id || piece.demo_id || state.selectedPieceId || '';
    if (CURATED_IDS.indexOf(id) !== -1) return true;
    if (String(id).indexOf('live_') === 0) return true;
    var sp = piece.source_score_path || piece.canonical_filename || '';
    if (!sp) return false;
    if (sp.indexOf('://') !== -1 || sp.indexOf('\n') !== -1 || sp.indexOf('\r') !== -1) return false;
    if (sp.indexOf('..') !== -1) return false;
    // Curated demo scores are under data/source_scores; live pieces have absolute external path handled by server
    return !!sp;
  }
  function probePieceOpenAvailable(piece) {
    if (!piece || openScoreLiveAvailable !== true) return;
    var pieceId = piece.id || piece.piece_id || piece.demo_id || state.selectedPieceId || '';
    if (!pieceId) return;
    fetch('/api/open-score?piece_id=' + encodeURIComponent(pieceId), { cache: 'no-cache' }).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    }).then(function (j) {
      if (j && j.available === false) {
        if (btnOpenScore) {
          btnOpenScore.classList.add('hidden');
          btnOpenScore.disabled = true;
        }
        if (openScoreStatus) { openScoreStatus.textContent = 'Score not available for this piece.'; openScoreStatus.classList.remove('hidden'); }
      }
    }).catch(function () { /* keep button as-is; POST will surface error */ });
  }
  function probeOpenScoreAvailability() {
    if (!btnOpenScore) return;
    fetch('/api/health', { cache: 'no-cache' }).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    }).then(function () {
      openScoreLiveAvailable = true;
      if (state.manifest) updateOpenScoreUI();
    }).catch(function () {
      openScoreLiveAvailable = false;
      if (state.manifest) updateOpenScoreUI();
    });
  }

  function updateOpenScoreUI() {
    if (!btnOpenScore) return;
    var m = state.manifest;
    if (!m || !m.piece) {
      if (btnOpenScore) btnOpenScore.classList.add('hidden');
      if (openScoreStatus) openScoreStatus.classList.add('hidden');
      return;
    }
    var piece = m.piece;
    if (!hasResolvableLocalScorePath(piece)) {
      if (btnOpenScore) { btnOpenScore.classList.add('hidden'); btnOpenScore.disabled = true; btnOpenScore.textContent = 'Open in MuseScore'; }
      if (openScoreStatus) { openScoreStatus.textContent = 'Score not available for this piece.'; openScoreStatus.classList.remove('hidden'); }
      return;
    }
    if (btnOpenScore) btnOpenScore.classList.remove('hidden');
    if (openScoreStatus) openScoreStatus.classList.remove('hidden');
    if (openScoreLiveAvailable === false) {
      btnOpenScore.disabled = true;
      btnOpenScore.textContent = 'Open in MuseScore';
      if (openScoreStatus) { openScoreStatus.textContent = 'Available with the local demo server.'; openScoreStatus.classList.remove('hidden'); }
      return;
    }
    if (openScoreLiveAvailable === null) {
      btnOpenScore.disabled = true;
      btnOpenScore.textContent = 'Open in MuseScore';
      if (openScoreStatus) { openScoreStatus.textContent = 'Checking…'; openScoreStatus.classList.remove('hidden'); }
      return;
    }
    btnOpenScore.disabled = false;
    btnOpenScore.textContent = 'Open in MuseScore';
    if (openScoreStatus) { openScoreStatus.textContent = ''; openScoreStatus.classList.add('hidden'); }
    probePieceOpenAvailable(piece);
  }

  function handleOpenScore() {
    if (!btnOpenScore || !openScoreStatus) return;
    var m = state.manifest;
    if (!m || !m.piece) return;
    var piece = m.piece;
    var pieceId = piece.id || piece.piece_id || piece.demo_id || state.selectedPieceId || '';
    var sourceScorePath = piece.source_score_path || piece.canonical_filename || '';
    btnOpenScore.disabled = true;
    btnOpenScore.textContent = 'Opening…';
    openScoreStatus.textContent = '';
    openScoreStatus.classList.remove('hidden');
    fetch('/api/open-score', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ piece_id: pieceId, source_score_path: sourceScorePath })
    }).then(function (r) {
      return r.json().then(function (j) { return { ok: r.ok, status: r.status, body: j }; });
    }).then(function (res) {
      if (!res.ok) throw new Error(res.body.error || ('HTTP ' + res.status));
      openScoreStatus.textContent = 'Opened in MuseScore — check the app.';
      btnOpenScore.disabled = false;
      btnOpenScore.textContent = 'Open in MuseScore';
    }).catch(function (err) {
      var msg = String(err.message || err);
      if (msg.indexOf('Failed to fetch') !== -1 || msg.indexOf('404') !== -1) {
        openScoreStatus.textContent = 'Not available — please use the local demo server.';
        openScoreLiveAvailable = false;
        btnOpenScore.disabled = true;
        btnOpenScore.textContent = 'Open in MuseScore';
      } else if (msg.indexOf('403') !== -1 || msg.toLowerCase().indexOf('not in allowed') !== -1 || msg.toLowerCase().indexOf('not in approved') !== -1) {
        openScoreStatus.textContent = 'This score can’t be opened here.';
        btnOpenScore.disabled = false;
        btnOpenScore.textContent = 'Open in MuseScore';
      } else {
        openScoreStatus.textContent = 'Could not open score.';
        btnOpenScore.disabled = false;
        btnOpenScore.textContent = 'Open in MuseScore';
      }
    });
  }

  function getSourceLabel(p) {
    var entry = null;
    if (p && p.id) entry = PIECE_CATALOG.find(function (x) { return x.id === p.id; });
    if (!entry && state.selectedPieceId) entry = PIECE_CATALOG.find(function (x) { return x.id === state.selectedPieceId; });
    var tag = entry ? entry.difficultyTag : '';
    if (!tag && p && p.difficulty_label) tag = String(p.difficulty_label).split(' (')[0].trim();
    var dataset = (p.dataset || (entry && entry.raw && entry.raw.dataset) || '').toLowerCase();
    if (tag) {
      if (dataset === 'cipi') {
        if (tag.toLowerCase().indexOf('henle') === 0) return 'CIPI \u00b7 ' + tag;
        return 'CIPI \u00b7 ' + tag;
      }
      if (dataset === 'oktav') {
        // tag like "Oktav 43" -> show "Oktav \u00b7 43"
        var m = tag.match(/Oktav\s*(\d+)/i);
        if (m) return 'Oktav \u00b7 ' + m[1];
        return tag;
      }
      return tag;
    }
    if (dataset) return dataset.toUpperCase();
    return '';
  }

  function renderMeta(m) {
    var p = m.piece || {};
    var sourceLabel = getSourceLabel(p);
    var sourceHtml = sourceLabel ? '<div class="small muted" style="margin-top:4px">' + esc(sourceLabel) + '</div>' : '';
    pieceMeta.innerHTML = '<h2 style="margin:0;font-size:1.35rem">' + esc(p.title || 'Untitled') + '</h2><div class="small muted" style="margin-top:2px">' + esc(p.composer || '') + '</div>' + sourceHtml;
  }

  function renderToggles(m) {
    // Visible chart: 6 learner-facing graph dimensions (not 9-aspect)
    var chartSeries = m.chart.series || {};
    var order = m.chart.graph_dimension_ids || m.chart.dimension_ids || m.chart.factor_ids || Object.keys(chartSeries);
    // Build ordered list of graph dimension descriptors directly from chart series
    // (9-aspect taxonomy stays in aspects panel for provenance, not toggles)
    var ordered = [];
    order.forEach(function (dimId) {
      var s = chartSeries[dimId];
      if (s) ordered.push({ aspect_id: dimId, id: dimId, dimension_id: dimId, label: s.label || s.feature_name || GRAPH_GLOSSARY[dimId]?.label || dimId, readiness: s.readiness || 'ready', availability: s.availability, blocked: s.blocked, caveated: s.caveated, description: s.description });
      else if (GRAPH_GLOSSARY[dimId]) ordered.push({ aspect_id: dimId, id: dimId, dimension_id: dimId, label: GRAPH_GLOSSARY[dimId].label, readiness: 'ready' });
    });
    // Include any series not in order (fallback)
    Object.keys(chartSeries).forEach(function (dimId) {
      if (!ordered.find(function (o) { return (o.aspect_id||o.id)===dimId; })) {
        var s = chartSeries[dimId];
        ordered.push({ aspect_id: dimId, id: dimId, label: s.label || dimId, readiness: s.readiness || 'ready', availability: s.availability, blocked: s.blocked, caveated: s.caveated });
      }
    });

    factorToggles.innerHTML = '';
    ordered.forEach(function (a) {
      var aspectId = a.aspect_id || a.id;
      // Use user-facing labels per brief
      var userLabel = GRAPH_GLOSSARY[aspectId] ? GRAPH_GLOSSARY[aspectId].label : (a.label || a.name || aspectId);
      var readiness = (a.readiness || a.status || a.availability || 'unknown').toLowerCase();
      var isBlocked = readiness === 'blocked' || a.blocked;
      var isCaveated = readiness === 'caveated' || a.caveated;
      var color = GRAPH_DIMENSION_COLORS[aspectId] || ASPECT_COLORS[aspectId] || FACTOR_COLORS[aspectId] || '#64748b';
      var series = chartSeries[aspectId];
      var hasData = series && series.normalized_values && series.normalized_values.some(function (v) { return v != null; });
      var enabled = state.enabled.has(aspectId);
      var labelEl = document.createElement('label');
      labelEl.className = 'toggle' + (enabled ? ' active' : '') + (isBlocked ? ' toggle-blocked' : '') + (isCaveated ? ' toggle-caveated' : '');
      var disabledAttr = isBlocked ? ' disabled' : '';
      var checkedAttr = enabled ? 'checked' : '';
      labelEl.innerHTML = '\n        <input type="checkbox" value="' + escAttr(aspectId) + '" ' + checkedAttr + disabledAttr + ' />\n        <span class="swatch" style="background:' + color + '"></span>\n        <span>' + esc(userLabel) + '</span>\n      ';
      var cb = labelEl.querySelector('input');
      if (isBlocked) {
        labelEl.style.opacity = '0.55';
        labelEl.title = 'No data for this dimension';
      } else if (isCaveated) {
        labelEl.title = 'Limited data';
      } else if (!hasData) {
        labelEl.title = 'No data in this piece';
      }
      cb.addEventListener('change', function () {
        if (cb.checked) {
          state.enabled.add(aspectId);
          labelEl.classList.add('active');
        } else {
          state.enabled.delete(aspectId);
          labelEl.classList.remove('active');
        }
        renderChart();
      });
      factorToggles.appendChild(labelEl);
    });
    if (!ordered.length) {
      factorToggles.innerHTML = '<span class="small muted">No dimensions available.</span>';
    }
  }

  function renderCaveats(m) {
    var caveats = m.caveats || [];
    var diagnostics = m.diagnostics || [];
    var all = [].concat(caveats);
    caveatsList.innerHTML = '';
    all.forEach(function (text) {
      var li = document.createElement('li');
      li.textContent = text;
      caveatsList.appendChild(li);
    });
    if (diagnostics.length && !caveats.length) {
      diagnostics.forEach(function (t) {
        var li=document.createElement('li'); li.textContent=t; caveatsList.appendChild(li);
      });
    }
    var s = m.snippet_status || 'unknown';
    var diag = m.snippet_diagnostic || '';
    snippetGlobal.innerHTML = '<strong>Snippets:</strong> <code>' + esc(s) + '</code> \u2014 ' + esc(diag);
    if (m.warnings && m.warnings.length) {
      var w = document.createElement('div');
      w.className = 'small muted';
      w.style.marginTop = '8px';
      w.textContent = 'Warnings: ' + m.warnings.join(' \u00b7 ');
      snippetGlobal.appendChild(w);
    }
  }

  function renderAspects(m) {
    if (!aspectsGrid) return;
    var payload = (m && (m.difficulty_aspects || m.aspects)) || null;
    if (aspectsSchema) aspectsSchema.textContent = (payload && payload.schema_version) || (m.aspects_schema_version || '\u2014');
    if (aspectsCount) {
      var cnt = payload ? (payload.aspect_count || (payload.aspects||[]).length) : 0;
      aspectsCount.textContent = payload ? cnt + ' items' : 'no details';
    }
    if (aspectsProfileVersion) aspectsProfileVersion.textContent = '';
    if (aspectsInterpretation && payload && payload.interpretation) {
      aspectsInterpretation.textContent = '';
    }
    if (aspectsDiagnostics) {
      var diags = (payload && payload.diagnostics) || [];
      aspectsDiagnostics.textContent = diags.length ? 'Details: ' + diags.join(' \u00b7 ') : '';
    }
    if (aspectsWarnings) {
      var warns = (payload && payload.warnings) || [];
      aspectsWarnings.textContent = warns.length ? 'Warnings: ' + warns.join(' \u00b7 ') : '';
    }

    aspectsGrid.innerHTML = '';
    if (aspectsNotice) {
      aspectsNotice.classList.add('hidden');
      aspectsNotice.textContent = '';
    }
    if (aspectsPanel) aspectsPanel.classList.remove('hidden');

    if (!payload || !Array.isArray(payload.aspects)) {
      if (aspectsNotice) {
        aspectsNotice.textContent = 'No additional details in manifest.';
        aspectsNotice.className = 'msg msg-error small';
        aspectsNotice.classList.remove('hidden');
      }
      if (aspectsPanel) aspectsPanel.classList.add('aspects-missing');
      return;
    }

    var aspects = payload.aspects;
    if (aspects.length !== 9) {
      if (aspectsNotice) {
        aspectsNotice.textContent = 'Details incomplete.';
        aspectsNotice.className = 'msg msg-error small';
        aspectsNotice.classList.remove('hidden');
      }
    }

    // Keep notice minimal and free of technical terms
    var chartSeries = m.chart && m.chart.series ? m.chart.series : {};
    var graphCount = Object.keys(chartSeries).length;
    var chartDimIds = (m.chart.graph_dimension_ids || m.chart.dimension_ids || []);
    if (aspectsNotice) {
      if (graphCount === 6 && chartDimIds.length === 6) {
        // keep hidden by default — details are in collapsed section
        aspectsNotice.classList.add('hidden');
      }
    }

    aspects.forEach(function (a, idx) {
      var aspectId = a.aspect_id || a.id || ('aspect_' + (idx+1));
      var label = a.label || a.name || aspectId;
      var readiness = (a.readiness || a.status || a.availability || 'unknown').toLowerCase();
      var description = a.description || '';
      var included = a.included_feature_ids || a.feature_ids || [];
      var missing = a.missing_features || a.missing_feature_notes || a.future_features || [];
      var limitations = a.limitations || a.caveats || a.diagnostics || [];
      var series = chartSeries[aspectId];

      var card = document.createElement('div');
      card.className = 'aspect-card readiness-' + readiness;
      card.setAttribute('data-aspect-id', aspectId);

      var badgeClass = 'badge';
      var readinessLabel = readiness;
      if (readiness === 'ready') { badgeClass += ' badge-ready'; readinessLabel = 'ready'; }
      else if (readiness === 'partial') { badgeClass += ' badge-partial'; readinessLabel = 'partial'; }
      else if (readiness === 'blocked' || readiness === 'missing') { badgeClass += ' badge-blocked'; readinessLabel = 'blocked'; }
      else if (readiness === 'caveated') { badgeClass += ' badge-caveated'; readinessLabel = 'caveated'; }
      else { badgeClass += ' badge-unknown'; }

      var extraNote = '';
      if (aspectId === 'structural_pattern_demand') extraNote = '<span class="small muted"> \u00b7 Aspect 8 — blocked/missing: no pattern extractor yet</span>';
      if (aspectId === 'performance_interpretive_demand') extraNote = '<span class="small muted"> \u00b7 Aspect 9 — caveated/partially observable</span>';

      var includedHtml = included.length
        ? included.map(function (fid) { return '<code class="mono small">' + esc(fid) + '</code>'; }).join(' ')
        : '<span class="small muted">none — contextual only</span>';
      var missingHtml = missing.length
        ? '<ul class="small" style="margin:4px 0 0 16px">' + missing.map(function (t) { return '<li>' + esc(t) + '</li>'; }).join('') + '</ul>'
        : '<span class="small muted">\u2014</span>';
      var limitHtml = limitations.length
        ? '<ul class="small" style="margin:4px 0 0 16px">' + limitations.map(function (t) { return '<li>' + esc(t) + '</li>'; }).join('') + '</ul>'
        : '<span class="small muted">\u2014</span>';

      var num = idx + 1;

      var temporalPreview = '';
      if (series && series.normalized_values) {
        var vals = series.normalized_values;
        var definedVals = vals.filter(function (v) { return v != null; });
        if (definedVals.length) {
          var minV = Math.min.apply(null, definedVals).toFixed(2);
          var maxV = Math.max.apply(null, definedVals).toFixed(2);
          var meanV = (definedVals.reduce(function (a,b){return a+b;},0)/definedVals.length).toFixed(2);
          temporalPreview = '<div class="small muted" style="margin-top:6px">n=' + vals.length + ' \u00b7 min ' + minV + ' \u00b7 max ' + maxV + ' \u00b7 mean ' + meanV + (series.blocked ? ' \u00b7 blocked' : '') + (series.caveated ? ' \u00b7 caveated' : '') + '</div>';
        } else if (series.blocked) {
          temporalPreview = '<div class="small muted" style="margin-top:6px">No signal</div>';
        }
      }

      card.innerHTML = '\n        <div class="aspect-head">\n          <div class="aspect-title">\n            <span class="aspect-num">' + num + '</span>\n            <span class="aspect-id mono small">' + esc(aspectId) + '</span>\n            <span class="' + badgeClass + '">' + esc(readinessLabel) + '</span>\n            ' + extraNote + '\n          </div>\n          <div class="aspect-label">' + esc(label) + '</div>\n          <div class="small muted">' + esc(description) + '</div>\n          ' + temporalPreview + '\n        </div>\n        <div class="aspect-body">\n          <div class="aspect-field">\n            <div class="k">Included feature IDs <span class="small muted">(' + included.length + ')</span></div>\n            <div class="v aspect-features">' + includedHtml + '</div>\n          </div>\n          <div class="aspect-field">\n            <div class="k">Missing / future</div>\n            <div class="v">' + missingHtml + '</div>\n          </div>\n          <div class="aspect-field">\n            <div class="k">Limitations / caveats</div>\n            <div class="v">' + limitHtml + '</div>\n          </div>\n          ' + (a.features || a.feature_summaries ? '<div class="small muted" style="margin-top:8px">Sample values: ' + (a.features||a.feature_summaries).slice(0,2).map(function (f) { return esc(f.feature_id)+': '+fmt(f.value)+' '+esc(f.units||''); }).join(' \u00b7 ') + ((a.features||a.feature_summaries).length>2 ? ' \u00b7 \u2026' : '') + '</div>' : '') + '\n        </div>\n      ';
      aspectsGrid.appendChild(card);
    });
  }

  function renderChart() {
    var m = state.manifest;
    if (!m) return;
    var W = 1120, H = 460;
    var margin = { left: 44, right: 16, top: 16, bottom: 28 };
    var plotW = W - margin.left - margin.right;
    var plotH = H - margin.top - margin.bottom;
    var seriesMap = m.chart.series || {};
    var composite = m.chart.composite || null;
    var regions = m.chart.regions || [];
    var N = regions.length || (Object.values(seriesMap)[0] && Object.values(seriesMap)[0].normalized_values ? Object.values(seriesMap)[0].normalized_values.length : 0) || 1;

    while (chartSvg.firstChild) chartSvg.removeChild(chartSvg.firstChild);
    chartSvg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);

    var gGrid = svgEl('g', {});
    for (var yi = 0; yi <= 4; yi++) {
      var yVal = yi / 4;
      var y = margin.top + (1 - yVal) * plotH;
      gGrid.appendChild(svgEl('line', { x1: margin.left, y1: y, x2: W - margin.right, y2: y, class: 'gridline' }));
      gGrid.appendChild(svgEl('text', { x: margin.left - 8, y: y + 3, 'text-anchor': 'end', class: 'tick-label' }, yVal.toFixed(2)));
    }
    var step = Math.max(1, Math.round(N / 8));
    for (var i = 0; i < N; i += step) {
      var x = margin.left + (i / Math.max(1, N - 1)) * plotW;
      gGrid.appendChild(svgEl('line', { x1: x, y1: margin.top, x2: x, y2: H - margin.bottom, class: 'gridline', style: 'stroke-dasharray:3 4;opacity:.6' }));
      var region = regions[i];
      var label = region ? (region.measure_numbers ? 'm' + region.measure_numbers[0] : 's' + i) : 's' + i;
      gGrid.appendChild(svgEl('text', { x: x, y: H - margin.bottom + 14, 'text-anchor': 'middle', class: 'tick-label' }, label));
    }
    gGrid.appendChild(svgEl('rect', { x: margin.left, y: margin.top, width: plotW, height: plotH, fill: 'none', class: 'axis' }));
    chartSvg.appendChild(gGrid);

    function buildPath(values) {
      // Smooth SVG path via Catmull-Rom to cubic Bezier, with gaps as new M segments.
      // Single-point -> M, two-point -> L, >=3 -> C curves (tension 1/6, faithful to data).
      function segmentToPath(points) {
        if (!points.length) return '';
        if (points.length === 1) return 'M ' + points[0].x + ' ' + points[0].y;
        if (points.length === 2) return 'M ' + points[0].x + ' ' + points[0].y + ' L ' + points[1].x + ' ' + points[1].y;
        var d = 'M ' + points[0].x + ' ' + points[0].y;
        for (var i = 0; i < points.length - 1; i++) {
          var p0 = i > 0 ? points[i - 1] : points[0];
          var p1 = points[i];
          var p2 = points[i + 1];
          var p3 = i + 2 < points.length ? points[i + 2] : points[points.length - 1];
          var cp1x = p1.x + (p2.x - p0.x) / 6;
          var cp1y = p1.y + (p2.y - p0.y) / 6;
          var cp2x = p2.x - (p3.x - p1.x) / 6;
          var cp2y = p2.y - (p3.y - p1.y) / 6;
          d += ' C ' + cp1x + ' ' + cp1y + ', ' + cp2x + ' ' + cp2y + ', ' + p2.x + ' ' + p2.y;
        }
        return d;
      }
      var segments = [];
      var cur = [];
      values.forEach(function (v, i) {
        if (v == null || isNaN(v)) {
          if (cur.length) { segments.push(cur); cur = []; }
          return;
        }
        var x = margin.left + (i / Math.max(1, values.length - 1)) * plotW;
        var y = margin.top + (1 - clamp01(v)) * plotH;
        cur.push({ x: x, y: y });
      });
      if (cur.length) segments.push(cur);
      var parts = [];
      segments.forEach(function (seg) {
        var s = segmentToPath(seg);
        if (s) parts.push(s);
      });
      return parts.join(' ');
    }

    // 6 learner-facing graph dimensions (visible chart)
    var graphIds = m.chart.graph_dimension_ids || m.chart.dimension_ids || m.chart.factor_ids || Object.keys(seriesMap);
    graphIds.forEach(function (gid) {
      if (!state.enabled.has(gid)) return;
      var s = seriesMap[gid];
      if (!s) return;
      if (s.blocked) return;
      var vals = s.normalized_values || s.smoothed_values || [];
      // Skip if all null
      if (!vals.some(function (v){ return v!=null;})) return;
      var d = buildPath(vals);
      if (!d) return;
      var color = GRAPH_DIMENSION_COLORS[gid] || ASPECT_COLORS[gid] || FACTOR_COLORS[gid] || '#334155';
      var path = svgEl('path', { d: d, class: 'series-path series-dim', stroke: color, opacity: '0.62', 'stroke-width': '1.6' });
      path.setAttribute('data-graph-dimension', gid);
      path.setAttribute('data-aspect', gid);
      path.setAttribute('data-factor', gid);
      chartSvg.appendChild(path);
    });

    if (state.compositeEnabled && composite && composite.normalized_values) {
      var vals = composite.normalized_values;
      if (vals.some(function (v){return v!=null;})) {
        var d = buildPath(vals);
        if (d) {
          var halo = svgEl('path', { d: d, class: 'series-path series-composite-halo', stroke: '#ffffff', 'stroke-width': '8.5', opacity: '0.98', fill: 'none' });
          halo.setAttribute('data-factor', 'composite.aspect_demand');
          halo.setAttribute('data-aspect', 'composite.aspect_demand');
          chartSvg.appendChild(halo);
          var p = svgEl('path', { d: d, class: 'series-path series-composite', stroke: COMPOSITE_COLOR, 'stroke-width': '4.8', opacity: '1', fill: 'none' });
          p.setAttribute('data-factor', 'composite.aspect_demand');
          p.setAttribute('data-aspect', 'composite.aspect_demand');
          chartSvg.appendChild(p);
        }
      }
    }

    var hotspots = [].concat(getPrimaryHotspots(m) || []).sort(function (a,b) { return (a.rank||99)-(b.rank||99); });
    hotspots.forEach(function (h) {
      var winIdx = hotspotWindowIndex(h, N, regions);
      var x = margin.left + (winIdx / Math.max(1, N - 1)) * plotW;
      var yVal = typeof h.score_value === 'number' ? h.score_value : (typeof h.score === 'number' ? h.score : 0.5);
      var y = margin.top + (1 - clamp01(yVal)) * plotH;
      var g = svgEl('g', { class: 'hotspot-g', tabindex: '0', role: 'button', 'aria-label': (h.label || h.id) + ' \u2014 score ' + (yVal!=null? yVal.toFixed(3):'?') });
      g.setAttribute('data-hotspot-id', h.id);
      g.appendChild(svgEl('circle', { cx: x, cy: y, r: 16, fill: 'transparent', stroke: 'none' }));
      var star = starPoints(x, y, 11, 5.5, 5);
      var isActive = state.selectedId === h.id;
      var poly = svgEl('polygon', { points: star, class: 'hotspot-star' + (isActive ? ' active' : ''), 'stroke-linejoin': 'round' });
      g.appendChild(poly);
      var t = svgEl('text', { x: x, y: y + 3.5, 'text-anchor': 'middle', class: 'hotspot-rank' }, String(h.rank || ''));
      g.appendChild(t);
      g.addEventListener('click', function () { selectHotspot(h.id); });
      g.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); selectHotspot(h.id); } });
      chartSvg.appendChild(g);
    });

    if (regions.length) {
      var first = regions[0] && regions[0].measure_numbers ? regions[0].measure_numbers[0] : '1';
      var last = regions[regions.length-1] && regions[regions.length-1].measure_numbers ? regions[regions.length-1].measure_numbers.slice(-1)[0] : String(regions.length);
      chartXLabels.textContent = 'Measures ' + first + '\u2013' + last + '  \u00b7  ' + N + ' segments';
    }
  }

  function renderHotspotList() {
    var m = state.manifest;
    var list = getPrimaryHotspots(m);
    if (!m || !list || !list.length) return;
    hotspotList.innerHTML = '';
    [].concat(list).sort(function (a,b) { return a.rank-b.rank; }).forEach(function (h) {
      var btn = document.createElement('button');
      btn.className = 'hotspot-chip' + (state.selectedId===h.id ? ' active' : '');
      btn.setAttribute('data-hotspot-id', h.id);
      btn.innerHTML = '<span class="rank">#' + esc(String(h.rank)) + '</span> ' + esc(h.label || h.measure_range || h.id) + ' <span class="small muted">' + esc((h.score_value!=null)? h.score_value.toFixed(3): (h.score!=null? h.score.toFixed(3):'')) + '</span>';
      btn.addEventListener('click', function () { selectHotspot(h.id); });
      hotspotList.appendChild(btn);
    });
  }

  function selectHotspot(id) {
    var m = state.manifest;
    if (!m) return;
    var list = getPrimaryHotspots(m);
    var h = (list||[]).find(function (x) { return x.id===id; });
    if (!h) {
      // fallback to raw hotspots (provenance drawer may link raw ids)
      h = (m.hotspots||[]).find(function (x) { return x.id===id; });
    }
    if (!h) return;
    state.selectedId = id;
    renderChart();
    renderHotspotList();
    renderDetail(h);
  }

  function renderDetail(h) {
    detailEmpty.classList.add('hidden');
    detailContent.classList.remove('hidden');

    var aspectContribs = h.dimension_contributors || h.graph_dimension_contributors || h.top_contributors || h.contributions || h.aspect_contributors || h.feature_contributions || [];
    var snippetStatus = h.snippet_status || state.manifest.snippet_status || 'not_rendered';
    var snippetDiag = h.snippet_diagnostic || state.manifest.snippet_diagnostic || '';
    var snippetImg = h.snippet_image ? (state.manifestBase + h.snippet_image) : null;

    var snippetHtml = '';
    if (snippetImg && snippetStatus === 'rendered') {
      snippetHtml = '<div class="snippet-wrap"><img src="' + escAttr(snippetImg) + '" alt="Snippet ' + escAttr(h.measure_range||'') + '" style="max-width:100%;height:auto;border:1px solid #e2e8f0;border-radius:8px" /></div>';
    } else if (snippetStatus === 'render_failed') {
      snippetHtml = '<div class="placeholder-snippet"><div class="snippet-badge">Snippet \u2014 failed</div><div class="snippet-state small">' + esc(snippetDiag || 'Render failed') + '</div></div>';
    } else {
      snippetHtml = '<div class="placeholder-snippet"><div class="snippet-badge">Snippet</div><div class="snippet-state small">' + esc(snippetDiag || 'Not yet rendered') + '</div></div>';
    }

    // --- Three-layer explanation (evidence -> heuristic -> optional LLM polish) ---
    var manifestChart = state.manifest ? state.manifest.chart : null;
    var manifestPiece = state.manifest ? state.manifest.piece : null;
    var display = getDisplayExplanation(h, manifestChart, manifestPiece);
    var evidence = display.evidence;
    var heuristic = display.heuristic || buildFallbackExplanation(h, manifestChart);
    var llm = display.llm;
    var layer = display.layer; // 'llm' | 'heuristic' | 'evidence'
    var isLLM = layer === 'llm' && llm;
    var explanation = isLLM ? {
      headline: heuristic.headline,
      summary: llm.summary || heuristic.summary,
      aspect_interplay: llm.musical_connection || heuristic.aspect_interplay || heuristic.dimension_interplay,
      dimension_interplay: llm.musical_connection || heuristic.dimension_interplay || heuristic.aspect_interplay,
      score_cue: heuristic.score_cue,
      timeline_context: heuristic.timeline_context,
      confidence: 'llm-polish',
      layer: 'llm',
      model: llm.model,
      evidence_hash: llm.evidence_hash
    } : heuristic;

    var measureRange = h.measure_range || (h.measure_numbers && h.measure_numbers.length ? h.measure_numbers.join('\u2013') : '') || 'this passage';
    var headline = explanation.headline || ('Measures ' + measureRange);
    var shortPhrase = headlineShortPhrase(headline, measureRange);
    // Title: "Measures X–Y" + short phrase if available (not repeating measure range)
    var titleHtml = '<div class="detail-title-block">'
      + '<div class="eyebrow">Key passage #' + esc(String(h.rank||'')) + '</div>'
      + '<h3 class="detail-title">Measures ' + esc(measureRange) + '</h3>'
      + (shortPhrase ? '<div class="detail-subtitle small">' + esc(shortPhrase) + '</div>' : '')
      + '</div>';
    var scoreBadge = '<span class="badge detail-score-badge">score ' + esc((h.score_value!=null)? h.score_value.toFixed(2): (h.score!=null? h.score.toFixed(2):'?')) + '</span>';

    // 2. Main explanation — one clear paragraph (LLM if valid, otherwise heuristic concise)
    var rawSummary = isLLM && llm.summary ? llm.summary : (heuristic.summary || '');
    var mainParagraph = conciseSummary(rawSummary) || 'No summary available for this passage.';
    // Prefer LLM summary verbatim; for heuristic, already stripped micro clause
    var mainHtml = '<section class="detail-main"><p class="detail-main-text">' + esc(mainParagraph) + '</p></section>';

    // 3. Top contributors — 2-3 chips/cards for graph dimensions
    var chipSource = (evidence && evidence.dimensions && evidence.dimensions.length) ? evidence.dimensions : aspectContribs.slice().sort(function(a,b){ return (a.rank||99)-(b.rank||99); }).slice(0,3).map(function(c){
      return { dimension_id: c.dimension_id || c.graph_dimension_id || c.aspect_id || c.feature_id || c.id, plain: resolvePlain(c), normalized_value: c.normalized_value, rank: c.rank, strength: strengthLabel(c.normalized_value), role: roleLabel(c.rank) };
    });
    var chipList = chipSource.slice(0,3).map(function(c){
      var aid = c.dimension_id || c.dimensionId || c.plain;
      var plain = c.plain || resolvePlain(c);
      var strength = c.strength || strengthLabel(c.normalized_value);
      var role = c.role || roleLabel(c.rank);
      var color = GRAPH_DIMENSION_COLORS[c.dimension_id] || GRAPH_DIMENSION_COLORS[aid] || ASPECT_COLORS[aid] || '#64748b';
      return { aid: aid, dimId: c.dimension_id || aid, plain: plain, strength: strength, role: role, color: color, normalized_value: c.normalized_value };
    });
    var chipsHtml = '';
    if (chipList.length) {
      chipsHtml = '<section class="detail-section detail-contributors"><h4>Top contributors</h4><div class="contrib-chips">'
        + chipList.map(function(c){
          return '<span class="contrib-chip" style="border-color:' + c.color + '"><span class="swatch" style="background:' + c.color + '"></span><span class="contrib-label">' + esc(c.plain) + '</span> <span class="contrib-strength small muted">' + esc(c.strength) + '</span></span>';
        }).join('') + '</div></section>';
    } else {
      chipsHtml = '<section class="detail-section detail-contributors"><h4>Top contributors</h4><div class="small muted">No single dimension dominates — distributed evidence.</div></section>';
    }

    // 4. Why It Feels Hard — short section using heuristic/LLM
    var whyText = (isLLM && llm.musical_connection) ? llm.musical_connection : (explanation.dimension_interplay || explanation.aspect_interplay || '');
    // Ensure plain learner language — heuristic already plain, but keep concise (first 2 sentences)
    var whyHtml = whyText ? '<section class="detail-section detail-why"><h4>Why It Feels Hard</h4><p class="small">' + esc(whyText) + '</p></section>' : '';

    // 5. Practice Focus — LLM if available else generic cue from top dimension
    var practiceText = '';
    var practiceSource = '';
    if (isLLM && llm.practice_focus) {
      practiceText = llm.practice_focus;
      practiceSource = 'Suggestion from LLM polish';
    } else {
      var topDimId = chipList.length ? chipList[0].dimId : '';
      practiceText = practiceCueForDimension(topDimId);
      practiceSource = 'Suggestion';
    }
    var practiceHtml = '<section class="detail-section detail-practice"><h4>Practice focus <span class="small muted" style="font-weight:400;text-transform:none;letter-spacing:0">\u2014 suggestion, not diagnosis</span></h4><p class="small">' + esc(practiceText) + '</p><p class="small muted" style="margin-top:4px;font-style:italic">' + esc(practiceSource) + ' \u00b7 try at a comfortable tempo and check against the score.</p></section>';

    // 6. Evidence — collapsed by default, deterministic details
    var rep = h.representative_region || {};
    var suppDims = h.supporting_dimension_ids || h.supporting_graph_dimension_ids || [];
    var suppAspects = (suppDims.length ? suppDims : (h.supporting_aspect_ids || h.supporting_factor_ids || [])).join(', ') || '\u2014';
    var suppWindows = (h.supporting_window_indices || []);
    var evidenceBody = '';
    // Build evidence internals from evidence brief + contributors
    var evDimsHtml = '';
    if (evidence && evidence.dimensions && evidence.dimensions.length) {
      evDimsHtml = '<ul class="small" style="margin:6px 0 0 16px">' + evidence.dimensions.map(function(d){
        var col = GRAPH_DIMENSION_COLORS[d.dimension_id] || ASPECT_COLORS[d.dimension_id] || '#64748b';
        return '<li><span class="swatch" style="background:' + col + ';display:inline-block;width:8px;height:8px;border-radius:999px;margin-right:6px;vertical-align:middle"></span>' + esc(d.plain || d.label || d.dimension_id) + ' \u2014 ' + esc(d.strength || strengthLabel(d.normalized_value)) + ' (norm ' + fmt(d.normalized_value) + ', share ' + (d.contribution_share!=null? (d.contribution_share*100).toFixed(1)+'%':'\u2014') + ')</li>';
      }).join('') + '</ul>';
    } else if (aspectContribs.length) {
      evDimsHtml = '<ul class="small" style="margin:6px 0 0 16px">' + aspectContribs.slice(0,3).map(function(c){
        var fid = c.dimension_id || c.graph_dimension_id || c.aspect_id || c.id;
        return '<li>' + esc(resolvePlain(c)) + ' \u2014 ' + esc(strengthLabel(c.normalized_value)) + ' (norm ' + fmt(c.normalized_value) + ')</li>';
      }).join('') + '</ul>';
    } else {
      evDimsHtml = '<span class="small muted">No dimension data.</span>';
    }
    var microList = (evidence && evidence.micro_features) ? evidence.micro_features : [];
    // Fallback: collect from contributors if evidence lacks micro
    if (!microList.length && aspectContribs.length) {
      var tmp = [];
      aspectContribs.slice(0,2).forEach(function(c){
        var feats = c.feature_contributors || c.supporting_feature_contributors || c.graph_contributors || [];
        feats.slice(0,3).forEach(function(f){ if (tmp.length<6) tmp.push(f); });
      });
      microList = tmp.map(function(f){
        return { plain: plainFeature(f.feature_id, f.label||''), raw_value: f.raw_value, units: f.units, normalized_value: f.normalized_value, feature_id: f.feature_id };
      });
    }
    var microHtml = microList.length ? '<ul class="small" style="margin:6px 0 0 16px">' + microList.slice(0,6).map(function(m){
      var raw = m.raw_value!=null ? fmt(m.raw_value) + (m.units ? ' ' + esc(m.units) : '') : '\u2014';
      return '<li>' + esc(m.plain || m.feature_id) + ' <span class="small muted">\u2014 ' + raw + ' \u00b7 norm ' + fmt(m.normalized_value) + '</span></li>';
    }).join('') + '</ul>' : '<span class="small muted">No micro-features listed.</span>';
    var caveats = (state.manifest && state.manifest.caveats) ? state.manifest.caveats.slice(0,4) : [];
    var caveatsHtml = caveats.length ? '<ul class="small" style="margin:6px 0 0 16px">' + caveats.map(function(t){ return '<li>' + esc(t) + '</li>'; }).join('') + '</ul>' : '<span class="small muted">No caveats.</span>';
    var evMetaLine = '';
    if (evidence && evidence.evidence_hash) evMetaLine = 'Evidence ' + esc(evidence.evidence_version || 'david_evidence.v1') + ' \u00b7 hash ' + esc(evidence.evidence_hash.slice(0,12));
    else if (evidence) evMetaLine = 'Evidence (fallback)';

    var timelineNote = heuristic && heuristic.timeline_context ? '<p class="small muted" style="margin-top:6px">' + esc(heuristic.timeline_context) + '</p>' : '';
    var scoreCueNote = heuristic && heuristic.score_cue ? '<p class="small muted" style="margin-top:4px">' + esc(heuristic.score_cue) + '</p>' : '';
    var provenanceSummary = (heuristic && heuristic.provenance_summary) || (display && display.heuristic && display.heuristic.provenance_summary) || '';
    var provenanceInterplay = (heuristic && heuristic.provenance_interplay) || (display && display.heuristic && display.heuristic.provenance_interplay) || '';
    var provenanceHtml = '';
    if (provenanceSummary) {
      provenanceHtml = '<div class="detail-section"><h4>Why this was flagged (debug / provenance)</h4><p class="small muted">' + esc(provenanceSummary) + '</p>' + (provenanceInterplay ? '<p class="small muted" style="margin-top:6px">' + esc(provenanceInterplay) + '</p>' : '') + '<p class="small muted" style="margin-top:6px"><em>Winning taxonomy and normalized contributors are relative within this piece; selection is descriptive, not a grade.</em></p></div>';
    }
    // Phase 3: hard bit grouping provenance — show core vs display + supporting windows
    var hardBitProvenanceHtml = '';
    if (h.core_region || h.display_region || h.practice_region) {
      var core = h.core_region || {};
      var displayR = h.display_region || h.practice_region || {};
      var sw = h.supporting_windows || [];
      var sRes = (h.supporting_resolutions || []).join(', ') || '—';
      var swHtml = sw.length ? '<ul class="small" style="margin:6px 0 0 16px">' + sw.slice(0,8).map(function(w){
        return '<li>' + esc(w.id || w.section_id || '?') + ' — ' + esc(w.measure_range || (w.measure_numbers||[]).join('–')) + ' <span class="mono small">' + esc(w.resolution_key||'') + '</span> score ' + esc(w.score_value!=null? Number(w.score_value).toFixed(2):'—') + '</li>';
      }).join('') + (sw.length>8 ? '<li class="small muted">… +'+(sw.length-8)+' more</li>' : '') + '</ul>' : '<span class="small muted">No supporting windows listed.</span>';
      // Include synthetic 1m if present
      var synth = h.supporting_windows_synthetic_1m || [];
      var synthHtml = synth.length ? '<div class="small muted" style="margin-top:6px">Synthetic 1m provenance (from 2m measure coverage): ' + synth.map(function(w){ return esc(w.measure_range); }).join(', ') + '</div>' : '';
      hardBitProvenanceHtml = '<div class="detail-section"><h4>Grouping (Phase 3)</h4>'
        + '<ul class="kv-list">'
        + '<li><span>Core</span><span><strong>' + esc(core.measure_range || core.label || '—') + '</strong> <span class="small muted">' + esc((core.measure_numbers||[]).join(',')) + '</span></span></li>'
        + '<li><span>Display / practice</span><span><strong>' + esc(displayR.measure_range || displayR.label || measureRange) + '</strong> <span class="small muted">buffer ±1, bounded</span></span></li>'
        + '<li><span>Supporting resolutions</span><span class="mono small">' + esc(sRes) + '</span></li>'
        + '<li><span>Supporting windows</span><span>' + swHtml + synthHtml + '</span></li>'
        + '</ul></div>';
    }
    evidenceBody = '<div class="evidence-body">'
      + '<div class="detail-section"><h4>Passage &amp; position</h4><ul class="kv-list">'
      + '<li><span>Measures</span><span><strong>' + esc(measureRange) + '</strong></span></li>'
      + '<li><span>Score</span><span class="mono">' + esc((h.score_value!=null)? h.score_value.toFixed(3): (h.score!=null? h.score.toFixed(3):'?')) + '</span></li>'
      + '<li><span>Section</span><span class="mono small">' + esc(h.section_id || h.id) + '</span></li>'
      + '<li><span>Window</span><span class="mono small">' + esc(String(rep.window_index!=null? rep.window_index : (suppWindows[0]!=null? suppWindows[0]:''))) + ' / ' + esc(String((evidence && evidence.total_windows) || (manifestChart && manifestChart.regions ? manifestChart.regions.length : ''))) + '</span></li>'
      + '</ul>' + timelineNote + scoreCueNote + '</div>'
      + '<div class="detail-section"><h4>Top dimensions (deterministic)</h4>' + evDimsHtml + '</div>'
      + '<div class="detail-section"><h4>Micro-features</h4>' + microHtml + '</div>'
      + hardBitProvenanceHtml
      + provenanceHtml
      + '<div class="detail-section"><h4>Caveats</h4>' + caveatsHtml + '</div>'
      + (evMetaLine ? '<p class="small muted" style="margin-top:10px">' + evMetaLine + '</p>' : '')
      + '</div>';

    // Compose final innerHTML — concise first view, evidence collapsed
    detailContent.innerHTML = ''
      + '<div class="detail-header" style="display:flex;justify-content:space-between;gap:8px;align-items:start">' + titleHtml + scoreBadge + '</div>'
      + snippetHtml
      + mainHtml
      + chipsHtml
      + whyHtml
      + practiceHtml
      + '<details class="evidence-disclosure"><summary>Evidence (deterministic)</summary>' + evidenceBody + '</details>'
      + '<p class="small muted" style="margin-top:10px;font-style:italic">Relative evidence within this piece \u00b7 not a grade.</p>';
    detailContent.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }



  function svgEl(tag, attrs, text) {
    var el = document.createElementNS('http://www.w3.org/2000/svg', tag);
    for (var k in attrs) el.setAttribute(k, attrs[k]);
    if (text != null) el.textContent = text;
    return el;
  }
  function clamp01(v) { if (typeof v !== 'number' || isNaN(v)) return 0; return Math.max(0, Math.min(1, v)); }
  function hotspotWindowIndex(h, N, regions) {
    if (h.representative_region && typeof h.representative_region.window_index === 'number') return h.representative_region.window_index;
    if (h.supporting_window_indices && h.supporting_window_indices.length) {
      var m = h.supporting_window_indices[Math.floor(h.supporting_window_indices.length/2)];
      return Math.max(0, Math.min(N-1, m));
    }
    if (typeof h.score_position === 'number' && regions.length) {
      var approx = Math.round(h.score_position / 4);
      return Math.max(0, Math.min(N-1, approx));
    }
    if (typeof h.window_index === 'number') return h.window_index;
    return 0;
  }
  function starPoints(cx, cy, outerR, innerR, n) {
    var pts = [];
    for (var i = 0; i < n*2; i++) {
      var r = (i % 2 === 0) ? outerR : innerR;
      var angle = Math.PI/2 * 3 + (Math.PI * i / n);
      pts.push((cx + Math.cos(angle)*r).toFixed(1) + ',' + (cy + Math.sin(angle)*r).toFixed(1));
    }
    return pts.join(' ');
  }
  function esc(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
  function escAttr(s) {
  return String(s)
    .replace(/&/g,'&amp;')
    .replace(/</g,'&lt;')
    .replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;')
    .replace(/'/g,'&#39;');
}
  function fmt(v) { if (v==null) return '\u2014'; if (typeof v==='number') return v.toFixed(3); return esc(String(v)); }

  // ── Live dataset picker (requires run_live_demo_server.py) ──────────────
  (function initLive() {
    var liveDataset = document.getElementById('live-dataset');
    var liveSearch = document.getElementById('live-search');
    var btnLiveSearch = document.getElementById('btn-live-search');
    var liveResults = document.getElementById('live-results');
    var btnAnalyze = document.getElementById('btn-analyze');
    var liveStatus = document.getElementById('live-status');
    var liveError = document.getElementById('live-error');
    var liveHint = document.getElementById('live-hint');
    if (!liveDataset || !liveSearch || !btnLiveSearch || !liveResults) return;

    var liveState = { selected: null, polling: null, results: [] };

    function showLiveError(msg) {
      if (!liveError) return;
      if (!msg) { liveError.classList.add('hidden'); liveError.textContent=''; return; }
      liveError.textContent = msg;
      liveError.classList.remove('hidden');
    }
    function setLiveStatus(msg) { if (liveStatus) liveStatus.textContent = msg || ''; }

    // Probe API availability — keep UI quiet; hide path details unless error.
    fetch('/api/datasets', { cache: 'no-cache' }).then(function (r) {
      if (!r.ok) throw new Error('HTTP '+r.status);
      return r.json();
    }).then(function () {
      if (liveHint) {
        liveHint.textContent = '';
        liveHint.classList.add('hidden');
      }
    }).catch(function () {
      if (liveHint) {
        liveHint.textContent = '';
        liveHint.classList.add('hidden');
      }
    });

    function renderLiveResults() {
      liveResults.innerHTML = '';
      if (!liveState.results.length) {
        liveResults.innerHTML = '<div class="live-empty">No results. Try a broader query or switch dataset.</div>';
        if (btnAnalyze) btnAnalyze.disabled = true;
        return;
      }
      liveState.results.forEach(function (item, idx) {
        var btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'live-result' + (liveState.selected && liveState.selected.dataset_relative_path === item.dataset_relative_path && liveState.selected.dataset === item.dataset ? ' selected' : '');
        btn.setAttribute('role', 'option');
        var composer = item.composer || '';
        var title = item.title || item.work_name || item.piece_id || '';
        var displayTitle = composer ? composer + ' — ' + title : title;
        var rawLabel = item.difficulty_label || '';
        var shortLabel = rawLabel ? rawLabel.split(' (')[0].trim() : '';
        if (!shortLabel && item.henle) shortLabel = 'Henle ' + item.henle;
        else if (!shortLabel && item.dataset === 'oktav' && item.difficulty_label) shortLabel = rawLabel.split(' (')[0].trim();
        if (item.dataset === 'cipi' && item.henle && !shortLabel) shortLabel = 'Henle ' + item.henle;
        var existsBadge = item.exists === false ? '<span class="live-badge" style="background:#fef2f2;border-color:#fecaca;color:#7f1d1d">missing file</span>' : '';
        var labelHtml = shortLabel ? '<span class="live-result-meta">' + esc(shortLabel) + '</span>' : '';
        btn.innerHTML = '<span class="live-result-title">' + esc(displayTitle) + existsBadge + '</span>' + labelHtml;
        btn.addEventListener('click', function () {
          liveState.selected = item;
          renderLiveResults();
          if (btnAnalyze) btnAnalyze.disabled = !item.exists && item.exists !== undefined ? true : false;
          showLiveError('');
          setLiveStatus('Selected: ' + displayTitle);
        });
        liveResults.appendChild(btn);
      });
      if (liveState.selected && btnAnalyze) {
        btnAnalyze.disabled = liveState.selected.exists === false;
      }
    }

    function doSearch() {
      var dataset = (liveDataset.value || 'cipi').toLowerCase();
      var q = (liveSearch.value || '').trim();
      showLiveError('');
      setLiveStatus('Searching…');
      liveResults.innerHTML = '<div class="live-empty">Searching…</div>';
      if (btnAnalyze) btnAnalyze.disabled = true;
      liveState.selected = null;
      var url = '/api/pieces?dataset=' + encodeURIComponent(dataset) + '&q=' + encodeURIComponent(q) + '&limit=50';
      fetch(url, { cache: 'no-cache' }).then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      }).then(function (data) {
        liveState.results = data.results || [];
        if (liveState.results.length) setLiveStatus('Found ' + liveState.results.length + ' result(s).');
        else setLiveStatus('No results.');
        renderLiveResults();
      }).catch(function (err) {
        showLiveError('Search failed: ' + err.message);
        setLiveStatus('');
        liveResults.innerHTML = '<div class="live-empty">Search failed.</div>';
      });
    }

    btnLiveSearch.addEventListener('click', doSearch);
    liveSearch.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); doSearch(); }});
    liveDataset.addEventListener('change', function () {
      liveState.results = [];
      liveState.selected = null;
      renderLiveResults();
      setLiveStatus('');
      showLiveError('');
    });

    // Analyze flow
    if (btnAnalyze) {
      btnAnalyze.addEventListener('click', function () {
        if (!liveState.selected) { showLiveError('Select a piece first.'); return; }
        var sel = liveState.selected;
        showLiveError('');
        setLiveStatus('Analyzing "' + (sel.title || sel.work_name || 'piece') + '"…');
        btnAnalyze.disabled = true;
        btnAnalyze.textContent = 'Analyzing…';
        var payload = {
          dataset: sel.dataset,
          piece_id: sel.piece_id,
          piece_uid: sel.piece_uid,
          dataset_id: sel.dataset_id || sel.cipi_id || sel.piece_id,
          dataset_relative_path: sel.dataset_relative_path,
          composer: sel.composer,
          title: sel.title
        };
        fetch('/api/analyze', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        }).then(function (r) {
          return r.json().then(function (j) { return { ok: r.ok, status: r.status, body: j }; });
        }).then(function (res) {
          if (!res.ok) throw new Error(res.body.error || ('HTTP ' + res.status));
          var jobId = res.body.job_id || res.body.jobId;
          if (!jobId) throw new Error('No job_id returned');
          setLiveStatus('Running analysis…');
          pollJob(jobId);
        }).catch(function (err) {
          showLiveError('Analyze failed: ' + err.message);
          setLiveStatus('');
          btnAnalyze.disabled = false;
          btnAnalyze.textContent = 'Analyze piece';
        });
      });
    }

    function pollJob(jobId) {
      var attempts = 0;
      var maxAttempts = 120; // 2 minutes polling
      function tick() {
        attempts += 1;
        fetch('/api/jobs/' + encodeURIComponent(jobId), { cache: 'no-cache' }).then(function (r) {
          if (!r.ok) throw new Error('HTTP ' + r.status);
          return r.json();
        }).then(function (job) {
          var st = job.status;
          if (st === 'queued' || st === 'running') {
            setLiveStatus(st === 'queued' ? 'Queued…' : 'Analyzing…');
            if (attempts < maxAttempts) setTimeout(tick, 1000);
            else {
              showLiveError('Analysis timed out. Please try again.');
              if (btnAnalyze) { btnAnalyze.disabled = false; btnAnalyze.textContent = 'Analyze piece'; }
            }
            return;
          }
          if (st === 'succeeded') {
            var url = job.manifest_url || job.manifest_url_rel;
            if (!url) { showLiveError('Analysis complete but could not load chart.'); return; }
            setLiveStatus('Analysis complete — opening chart…');
            loadLiveManifest(url, job);
            if (btnAnalyze) { btnAnalyze.disabled = false; btnAnalyze.textContent = 'Analyze piece'; }
            return;
          }
          if (st === 'failed') {
            var err = job.error || 'Unknown error';
            showLiveError('Analysis failed: ' + err);
            if (job.log) console.error('Job log:', job.log);
            setLiveStatus('');
            if (btnAnalyze) { btnAnalyze.disabled = false; btnAnalyze.textContent = 'Analyze piece'; }
            return;
          }
          showLiveError('Unexpected status: ' + st);
        }).catch(function (err) {
          showLiveError('Polling failed: ' + err.message);
          if (btnAnalyze) { btnAnalyze.disabled = false; btnAnalyze.textContent = 'Analyze piece'; }
        });
      }
      setTimeout(tick, 800);
    }

    function loadLiveManifest(manifestUrl, job) {
      // Reuse the same final chart view as pre-analyzed catalog (single rendering path)
      showLiveError('');
      fetch(manifestUrl, { cache: 'no-cache' }).then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      }).then(function (data) {
        var base = manifestUrl.slice(0, manifestUrl.lastIndexOf('/') + 1);
        state.selectedPieceId = null; // live piece not in catalog (keeps catalog selection stable)
        try {
          applyManifest(data, base);
        } catch (e) {
          throw e;
        }
        setLiveStatus('');
      }).catch(function (err) {
        showLiveError('Could not open chart: ' + err.message);
        setLiveStatus('');
      });
    }

    // Initial empty state
    renderLiveResults();
    setLiveStatus('');
  })();

})();
