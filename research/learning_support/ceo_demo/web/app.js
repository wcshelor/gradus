// Demo launcher — static wrapper over stored piece manifests (catalog-driven).
// Primary model: 9-aspect taxonomy. Chart toggles are aspects; hotspots list aspect contributors with nested feature contributors.
(function () {
  const CATALOG_URL = '../artifacts/pieces.json';
  const FALLBACK_CATALOG = [
    {
      id: 'debussy_arabesque_1',
      title: 'Debussy — Arabesque No. 1',
      subtitle: 'Claude Debussy · CIPI',
      manifestUrl: '../artifacts/debussy_arabesque_1/demo_manifest.json',
      artifactBase: '../artifacts/debussy_arabesque_1/',
      enabled: true,
    },
  ];

  let PIECE_CATALOG = [];

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
  function plainFeature(fid, label) { return FEATURE_GLOSSARY[fid] || (label ? label.replace(/_/g,' ').replace(/\./g,' · ') : fid.replace(/_/g,' ').replace(/\./g,' · ')); }
  function strengthLabel(v) {
    if (typeof v !== 'number' || isNaN(v)) return 'unknown';
    if (v >= 0.75) return 'very high';
    if (v >= 0.55) return 'high';
    if (v >= 0.33) return 'moderate';
    return 'low';
  }
  function roleLabel(rank) { if (rank===1) return 'primary'; if (rank===2||rank===3) return 'secondary'; return 'supporting'; }
  function buildFallbackExplanation(h, chart) {
    var measure_range = h.measure_range || '';
    if (!measure_range || measure_range==='unknown') {
      var nums = h.measure_numbers || [];
      if (nums.length >=2) measure_range = nums[0]+'\u2013'+nums[nums.length-1];
      else if (nums.length===1) measure_range = String(nums[0]);
      else measure_range = 'this window';
    }
    var score_value = (h.score_value!=null? h.score_value : h.score);
    var contributors = (h.aspect_contributors || h.top_contributors || h.contributions || []).slice();
    contributors.sort(function(a,b){ return (a.rank||99)-(b.rank||99); });
    var top = contributors.slice(0,3);
    var elevated = top.filter(function(c){ return typeof c.normalized_value==='number' && c.normalized_value>=0.5; });
    var hasStrong = contributors.slice(0,2).some(function(c){ return typeof c.normalized_value==='number' && c.normalized_value>=0.5; });
    var headline, summary, aspect_interplay, score_cue, timeline_context=null;
    if (top.length) {
      var leadPlain = plainAspect(top[0].aspect_id || top[0].feature_id || '');
      var leadStrength = strengthLabel(top[0].normalized_value);
      headline = 'Measures ' + measure_range + ' \u2014 ' + leadPlain + ' stands out (' + leadStrength + ')';
    } else {
      headline = 'Measures ' + measure_range + ' \u2014 distributed evidence';
    }
    if (!contributors.length) {
      summary = 'The score-derived evidence for this window is distributed \u2014 no single aspect stands out strongly. The trace suggests a modest, shared contribution across aspects within this piece (not a calibrated grade).';
    } else if (!hasStrong) {
      var names = top.slice(0,2).map(function(c){ return plainAspect(c.aspect_id||''); }).join(', ');
      summary = 'The score-derived evidence points to a distributed pattern in measures ' + measure_range + ': ' + names + ' are the relatively higher signals, but all remain moderate or lower. This suggests no single demand dominates here \u2014 the window sits close to the piece average.';
    } else {
      var primary = top[0];
      var pPlain = plainAspect(primary.aspect_id||'');
      var pStrength = strengthLabel(primary.normalized_value);
      if (top.length>=2 && elevated.length>=2) {
        var sPlain = plainAspect(top[1].aspect_id||'');
        var sStrength = strengthLabel(top[1].normalized_value);
        summary = 'The score-derived evidence suggests measures ' + measure_range + ' stand out mainly for ' + pPlain + ' (' + pStrength + ', primary), with secondary support from ' + sPlain + ' (' + sStrength + '). The signal is relative within this piece, not a calibrated grade or learner diagnosis.';
      } else {
        summary = 'The score-derived evidence points to ' + pPlain + ' as the primary contributor in measures ' + measure_range + ' (' + pStrength + '). The other aspects are lower in this window. The signal is relative within this piece.';
      }
      var feats = primary.feature_contributors || primary.supporting_feature_contributors || [];
      if (feats.length) {
        var ft = feats.slice().sort(function(a,b){return (a.rank||99)-(b.rank||99);})[0];
        if (ft && typeof ft.normalized_value==='number' && ft.normalized_value>=0.5) {
          summary += ' Among supporting signals, ' + plainFeature(ft.feature_id, ft.label) + ' is relatively elevated here.';
        }
      }
    }
    if (!contributors.length) {
      aspect_interplay = 'No aspect contributor data is available for this window \u2014 the explanation is limited to position and composite.';
    } else if (!hasStrong) {
      aspect_interplay = 'The evidence is distributed \u2014 the score-derived signals are broadly similar across the top aspects, so no clear interplay dominates. This window reflects a balanced, average passage in the 9-aspect view.';
    } else if (elevated.length>=2) {
      var nms = elevated.slice(0,3).map(function(c){ return plainAspect(c.aspect_id||''); });
      if (nms.indexOf('hand shape and span')!==-1 && nms.indexOf('texture and polyphony')!==-1) {
        aspect_interplay = 'Two or more aspects are elevated together \u2014 ' + nms.slice(0,2).join(', ') + ' \u2014 which suggests that multiple notes sounding together coincides with wider hand shapes in this window. The score-derived evidence points to a combined texture + span character, not a single cause.';
      } else {
        aspect_interplay = 'More than one aspect is elevated \u2014 ' + nms.join(', ') + ' \u2014 which suggests these demands coincide in this window. The overlap is descriptive within the 9-aspect model, not a weighted difficulty claim.';
      }
    } else {
      aspect_interplay = 'The primary signal is ' + plainAspect(top[0].aspect_id||'') + '; the other aspects are lower here, so the window\u2019s character is mainly shaped by that one demand. The score-derived evidence suggests a focused rather than combined pattern.';
    }
    if (typeof score_value==='number') {
      var level = score_value>=0.55? 'relatively high for this piece' : score_value>=0.42? 'above the piece average' : score_value>=0.32? 'near the piece average' : 'relatively modest for this piece';
      score_cue = 'Composite around ' + score_value.toFixed(2) + ' \u2014 ' + level + '. Hotspot rank #' + (h.rank||'?') + '; the value is a descriptive mean within the 9-aspect model, not a calibrated grade.';
    } else {
      score_cue = 'Composite is not available for this window \u2014 the ranking is relative within the 9-aspect model, not a calibrated grade.';
    }
    if (chart && chart.regions) {
      var total = chart.regions.length;
      var rep = h.representative_region||{};
      var winIdx = (typeof rep.window_index==='number'? rep.window_index : (h.supporting_window_indices && h.supporting_window_indices[0]));
      if (typeof winIdx==='number' && total) {
        var pct = winIdx/Math.max(1,total-1);
        var where = pct<0.2? 'near the opening' : pct<0.4? 'in the early-middle' : pct<0.6? 'around the middle' : pct<0.8? 'in the late-middle' : 'toward the end';
        timeline_context = 'Window ' + (winIdx+1) + ' of ' + total + ' ' + where + ' (measures ' + measure_range + '). Position is descriptive \u2014 it does not imply a learning sequence.';
      }
    }
    return { headline: headline, summary: summary, aspect_interplay: aspect_interplay, score_cue: score_cue, timeline_context: timeline_context, confidence: 'heuristic' };
  }

  const state = {
    manifest: null,
    manifestBase: '',
    enabled: new Set(),
    compositeEnabled: true,
    selectedId: null,
    selectedPieceId: null,
  };

  // DOM
  const btnLoad = document.getElementById('btn-load');
  const loadError = document.getElementById('load-error');
  const viewLoad = document.getElementById('view-load');
  const viewChart = document.getElementById('view-chart');
  const pieceListEl = document.getElementById('piece-list');
  const pieceMeta = document.getElementById('piece-meta');
  const factorToggles = document.getElementById('factor-toggles');
  const toggleComposite = document.getElementById('toggle-composite');
  const chartSvg = document.getElementById('chart-svg');
  const chartXLabels = document.getElementById('chart-x-labels');
  const hotspotList = document.getElementById('hotspot-list');
  const detailEmpty = document.getElementById('detail-empty');
  const detailContent = document.getElementById('detail-content');
  const caveatsList = document.getElementById('caveats-list');
  const snippetGlobal = document.getElementById('snippet-global-status');
  const btnBack = document.getElementById('btn-back-to-load');
  // Open in MuseScore (local demo only — requires live server)
  const scoreOpenRow = document.getElementById('score-open-row');
  const btnOpenScore = document.getElementById('btn-open-score');
  const openScoreStatus = document.getElementById('open-score-status');
  let openScoreLiveAvailable = null;
  // Aspects (9-aspect taxonomy)
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

  btnLoad.addEventListener('click', loadManifest);
  btnBack.addEventListener('click', function () {
    viewChart.classList.add('hidden');
    viewLoad.classList.remove('hidden');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
  toggleComposite.addEventListener('change', function () {
    state.compositeEnabled = toggleComposite.checked;
    renderChart();
  });

  // ── Open in MuseScore (local demo convenience — requires live server) ──
  if (btnOpenScore) {
    btnOpenScore.addEventListener('click', handleOpenScore);
  }
  // Probe live-server availability once at startup (quietly)
  probeOpenScoreAvailability();

  async function initCatalog() {
    if (pieceListEl) pieceListEl.innerHTML = '<div class="small muted" style="padding:8px">Loading pieces…</div>';
    try {
      var res = await fetch(CATALOG_URL, { cache: 'no-cache' });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      var data = await res.json();
      var pieces = data.pieces || data || [];
      if (!Array.isArray(pieces) || pieces.length === 0) throw new Error('Empty catalog');
      PIECE_CATALOG = pieces.map(function (p) {
        var isReady = (p.status || 'ready') === 'ready';
        var title = p.title || p.id;
        var composer = p.composer || '';
        var displayTitle = composer ? composer + ' — ' + title : title;
        var subtitleParts = [];
        if (p.composer) subtitleParts.push(p.composer);
        if (p.difficulty_label) {
          var shortLabel = p.difficulty_label.split(' (')[0];
          subtitleParts.push(shortLabel);
        }
        if (p.dataset) subtitleParts.push(p.dataset);
        var subtitle = subtitleParts.join(' · ') || (p.dataset_id || '');
        return {
          id: p.id,
          title: displayTitle,
          subtitle: subtitle,
          manifestUrl: p.manifest_url || p.manifestUrl || ('../artifacts/' + p.id + '/demo_manifest.json'),
          artifactBase: p.artifact_base || p.artifactBase || ('../artifacts/' + p.id + '/'),
          enabled: isReady,
          raw: p,
        };
      });
    } catch (err) {
      console.warn('Catalog load failed, using fallback:', err);
      PIECE_CATALOG = FALLBACK_CATALOG.slice();
      if (loadError) {
        loadError.textContent = 'Catalog not available — showing fallback piece. If this persists, check that artifacts/pieces.json exists.';
        loadError.classList.remove('hidden');
        setTimeout(function () { loadError.classList.add('hidden'); }, 4000);
      }
    }
    var preferred = PIECE_CATALOG.find(function (p) { return p.id === 'debussy_arabesque_1' && p.enabled; });
    var firstEnabled = PIECE_CATALOG.find(function (p) { return p.enabled; });
    var chosen = preferred || firstEnabled || PIECE_CATALOG[0] || null;
    if (chosen) state.selectedPieceId = chosen.id;
    renderPieceList();
  }

  function getSelectedPiece() {
    return PIECE_CATALOG.find(function (p) { return p.id === state.selectedPieceId; }) || null;
  }

  function renderPieceList() {
    if (!pieceListEl) return;
    pieceListEl.innerHTML = '';
    if (!PIECE_CATALOG.length) {
      pieceListEl.innerHTML = '<div class="small muted" style="padding:8px">No pieces available. Build artifacts first.</div>';
      return;
    }
    var visible = PIECE_CATALOG.filter(function (p) { return p.enabled; });
    visible.forEach(function (p) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'piece-row' + (p.id === state.selectedPieceId ? ' selected' : '');
      btn.setAttribute('role', 'option');
      btn.setAttribute('aria-selected', p.id === state.selectedPieceId ? 'true' : 'false');
      btn.setAttribute('data-piece-id', p.id);
      btn.innerHTML = '<span class="piece-row-title">' + esc(p.title) + '</span>' +
        '<span class="piece-row-sub">' + esc(p.subtitle || '') + '</span>';
      btn.addEventListener('click', function () {
        state.selectedPieceId = p.id;
        renderPieceList();
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
      row.innerHTML = '<span class="piece-row-title">' + esc(p.title) + '</span>' +
        '<span class="piece-row-sub">' + esc(p.subtitle || 'Coming soon') + '</span>';
      pieceListEl.appendChild(row);
    });
    if (visible.length === 0 && disabled.length > 0) {
      var msg = document.createElement('div');
      msg.className = 'small muted';
      msg.style.padding = '8px';
      msg.textContent = 'No ready pieces. Build artifacts with build_demo_piece.py.';
      pieceListEl.appendChild(msg);
    }
  }

  async function loadManifest() {
    loadError.classList.add('hidden');
    loadError.textContent = '';
    var piece = getSelectedPiece();
    if (!piece) {
      loadError.textContent = 'Please select a piece.';
      loadError.classList.remove('hidden');
      return;
    }
    var manifestUrl = piece.manifestUrl;
    state.manifestBase = piece.artifactBase || manifestUrl.slice(0, manifestUrl.lastIndexOf('/') + 1);
    btnLoad.disabled = true;
    btnLoad.textContent = 'Loading\u2026';
    try {
      var res = await fetch(manifestUrl, { cache: 'no-cache' });
      if (!res.ok) throw new Error('HTTP ' + res.status);
      var data = await res.json();
      if (!data.chart || !data.hotspots) {
        throw new Error('Invalid manifest: missing chart/hotspots');
      }
      // Validate 9-aspect contract: chart must have 9 aspect series
      var aspectIds = data.chart.aspect_ids || data.chart.factor_ids || [];
      if (aspectIds.length !== 9) {
        console.warn('Manifest chart does not have 9 aspect ids, found', aspectIds.length);
      }
      state.manifest = data;
      var ids = (data.chart.aspect_ids && data.chart.aspect_ids.length) ? data.chart.aspect_ids : (data.chart.factor_ids || []);
      // Filter to only aspects that are not blocked? But show all 9 toggles honestly; enable ready/partial/caveated by default, blocked disabled but visible
      state.enabled = new Set();
      ids.forEach(function (id) {
        // Check if series is blocked
        var series = data.chart.series && data.chart.series[id];
        if (series && series.blocked) {
          // blocked aspects shown but disabled by default
          return;
        }
        state.enabled.add(id);
      });
      // If no enabled because all blocked fallback, enable at least ready ones
      if (state.enabled.size === 0 && ids.length) {
        ids.slice(0,3).forEach(function (id) { state.enabled.add(id); });
      }
      state.compositeEnabled = true;
      toggleComposite.checked = true;
      onLoaded();
    } catch (err) {
      loadError.textContent = 'Failed to load "' + piece.title + '". The piece may be missing or not yet built. Please try another.';
      loadError.classList.remove('hidden');
      btnLoad.disabled = false;
      btnLoad.textContent = 'Load piece';
      console.error(err);
    }
  }

  function onLoaded() {
    var m = state.manifest;
    viewLoad.classList.add('hidden');
    viewChart.classList.remove('hidden');
    btnLoad.disabled = false;
    btnLoad.textContent = 'Load piece';
    renderMeta(m);
    renderToggles(m);
    renderCaveats(m);
    renderAspects(m);
    renderChart();
    renderHotspotList();
    if (m.hotspots && m.hotspots.length) {
      selectHotspot(m.hotspots[0].id);
    }
    updateOpenScoreUI();
  }

  // ── Open in MuseScore helpers ──
  function probeOpenScoreAvailability() {
    if (!scoreOpenRow || !btnOpenScore || !openScoreStatus) return;
    // Quiet probe: live server exposes /api/health; static python -m http.server will 404.
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
    if (!scoreOpenRow || !btnOpenScore || !openScoreStatus) return;
    var m = state.manifest;
    if (!m || !m.piece) {
      scoreOpenRow.classList.add('hidden');
      return;
    }
    scoreOpenRow.classList.remove('hidden');
    if (openScoreLiveAvailable === false) {
      btnOpenScore.disabled = true;
      btnOpenScore.textContent = 'Open in MuseScore';
      openScoreStatus.textContent = 'Local demo only — requires live server';
      openScoreStatus.title = 'Run: conda run -n piano-difficulty python research/learning_support/ceo_demo/scripts/run_live_demo_server.py --port 8000';
      return;
    }
    if (openScoreLiveAvailable === null) {
      btnOpenScore.disabled = true;
      btnOpenScore.textContent = 'Open in MuseScore';
      openScoreStatus.textContent = 'Checking local demo server…';
      return;
    }
    // Live available
    btnOpenScore.disabled = false;
    btnOpenScore.textContent = 'Open in MuseScore';
    openScoreStatus.textContent = 'Local demo only — opens the canonical source file on this machine';
  }

  function handleOpenScore() {
    if (!btnOpenScore || !openScoreStatus) return;
    var m = state.manifest;
    if (!m || !m.piece) return;
    var piece = m.piece;
    var pieceId = piece.id || piece.piece_id || piece.demo_id || state.selectedPieceId || '';
    var sourceScorePath = piece.source_score_path || piece.canonical_filename || '';
    // Also include safe live id when in live mode (piece.id is safe id)
    btnOpenScore.disabled = true;
    btnOpenScore.textContent = 'Opening…';
    openScoreStatus.textContent = 'Requesting local MuseScore…';
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
      // Quiet copy when endpoint not available (static server)
      if (msg.indexOf('Failed to fetch') !== -1 || msg.indexOf('404') !== -1) {
        openScoreStatus.textContent = 'Local demo only — requires live server';
        openScoreLiveAvailable = false;
        btnOpenScore.disabled = true;
        btnOpenScore.textContent = 'Open in MuseScore';
      } else if (msg.indexOf('403') !== -1 || msg.toLowerCase().indexOf('not in allowed') !== -1) {
        openScoreStatus.textContent = 'Blocked — this score is not in the approved demo locations.';
        btnOpenScore.disabled = false;
        btnOpenScore.textContent = 'Open in MuseScore';
      } else {
        openScoreStatus.textContent = 'Could not open score: ' + msg;
        btnOpenScore.disabled = false;
        btnOpenScore.textContent = 'Open in MuseScore';
      }
    });
  }

  function renderMeta(m) {
    var p = m.piece || {};
    var c = m.chart || {};
    var w = c.window || {};
    pieceMeta.innerHTML = '\n      <div class="meta-main">\n        <div class="eyebrow">Piece</div>\n        <h2>' + esc(p.title || 'Arabesque No.1') + ' <span class="small muted">\u2014 ' + esc(p.composer || 'Debussy') + '</span></h2>\n        <div class="meta-grid">\n          <div class="meta-kv"><div class="k">Measures</div><div class="v">' + esc(String(p.measure_count || '')) + ' \u00b7 windows ' + esc(String((c.regions||[]).length || '')) + '</div></div>\n          <div class="meta-kv"><div class="k">Notes</div><div class="v">' + esc(String(p.written_note_count || '')) + ' written \u00b7 ' + esc(String(p.logical_note_count || '')) + ' logical</div></div>\n          <div class="meta-kv"><div class="k">Window</div><div class="v mono">' + esc(w.kind||'measure') + ' ' + esc(String(w.size||'')) + ' / step ' + esc(String(w.step||'')) + ' \u00b7 beat ' + esc(String(w.beat_size||'')) + '</div></div>\n        </div>\n      </div>\n      <div class="meta-side">\n        <div class="interpretation">\u201c' + esc(m.interpretation || '') + '\u201d</div>\n        <div class="small muted" style="margin-top:10px">Hand mode: <strong>' + esc(m.hand_mode || c.hand_mode || 'both') + '</strong></div>\n      </div>\n    ';
  }

  function renderToggles(m) {
    // Primary: use 9 aspects from difficulty_aspects payload, not legacy factors
    var aspectsPayload = (m && (m.difficulty_aspects || m.aspects)) || null;
    var aspectsList = aspectsPayload && aspectsPayload.aspects ? aspectsPayload.aspects : null;
    var chartSeries = m.chart.series || {};
    var order = m.chart.aspect_ids || m.chart.factor_ids || Object.keys(chartSeries);
    // If aspectsList available, use it to order; otherwise use chart order
    var ordered = [];
    if (aspectsList && aspectsList.length === 9) {
      order.forEach(function (aid) {
        var a = aspectsList.find(function (x) { return (x.aspect_id || x.id) === aid; });
        if (a) ordered.push(a);
      });
      // Ensure all 9 present even if order missing some
      aspectsList.forEach(function (a) {
        var aid = a.aspect_id || a.id;
        if (!ordered.find(function (o) { return (o.aspect_id||o.id)===aid; })) ordered.push(a);
      });
    } else {
      // Fallback to chart series as aspects
      order.forEach(function (aid) {
        var s = chartSeries[aid];
        if (s) ordered.push({ aspect_id: aid, label: s.label || aid, readiness: s.readiness || 'ready', availability: s.availability, blocked: s.blocked, caveated: s.caveated });
      });
    }

    factorToggles.innerHTML = '';
    ordered.forEach(function (a) {
      var aspectId = a.aspect_id || a.id;
      var label = a.label || a.name || aspectId;
      var readiness = (a.readiness || a.status || a.availability || 'unknown').toLowerCase();
      var isBlocked = readiness === 'blocked' || a.blocked;
      var isCaveated = readiness === 'caveated' || a.caveated;
      var color = ASPECT_COLORS[aspectId] || FACTOR_COLORS[aspectId] || '#64748b';
      var series = chartSeries[aspectId];
      var hasData = series && series.normalized_values && series.normalized_values.some(function (v) { return v != null; });
      var enabled = state.enabled.has(aspectId);
      var labelEl = document.createElement('label');
      labelEl.className = 'toggle' + (enabled ? ' active' : '') + (isBlocked ? ' toggle-blocked' : '') + (isCaveated ? ' toggle-caveated' : '');
      var disabledAttr = isBlocked ? ' disabled' : '';
      var checkedAttr = enabled ? 'checked' : '';
      var badge = '';
      if (isBlocked) badge = '<span class="badge badge-blocked">blocked</span>';
      else if (isCaveated) badge = '<span class="badge badge-caveated">caveated</span>';
      else if (readiness === 'partial') badge = '<span class="badge badge-partial">partial</span>';
      labelEl.innerHTML = '\n        <input type="checkbox" value="' + escAttr(aspectId) + '" ' + checkedAttr + disabledAttr + ' />\n        <span class="swatch" style="background:' + color + '"></span>\n        <span>' + esc(label) + '</span>\n        ' + badge + '\n        <span class="small muted">' + esc(aspectId) + '</span>\n      ';
      var cb = labelEl.querySelector('input');
      if (isBlocked) {
        labelEl.style.opacity = '0.55';
        labelEl.title = 'Blocked — no temporal trace (structural pattern)';
      } else if (isCaveated) {
        labelEl.title = 'Caveated — written proxies only';
      } else if (!hasData) {
        labelEl.title = 'No temporal data in this piece';
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
    // If no aspects found, show fallback message
    if (!ordered.length) {
      factorToggles.innerHTML = '<span class="small muted">No aspect series in manifest (expected 9).</span>';
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
      aspectsCount.textContent = payload ? cnt + ' aspects \u00b7 ' + (payload.aspects ? payload.aspects.length + ' in payload' : '') : 'no aspects in manifest';
    }
    if (aspectsProfileVersion) aspectsProfileVersion.textContent = payload ? 'profile v' + (payload.profile_version || '') : '';
    if (aspectsInterpretation && payload && payload.interpretation) {
      aspectsInterpretation.textContent = payload.interpretation + ' Timeline & hotspots are aspect-based (overall demand = mean of aspects excluding blocked).';
    }
    if (aspectsDiagnostics) {
      var diags = (payload && payload.diagnostics) || [];
      aspectsDiagnostics.textContent = diags.length ? 'Diagnostics: ' + diags.join(' \u00b7 ') : '';
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

    if (!payload || !Array.isArray(payload.aspects)) {
      if (aspectsNotice) {
        aspectsNotice.textContent = 'No 9-aspect taxonomy payload in manifest.';
        aspectsNotice.className = 'msg msg-error small';
        aspectsNotice.classList.remove('hidden');
      }
      if (aspectsPanel) aspectsPanel.classList.add('aspects-missing');
      return;
    }

    var aspects = payload.aspects;
    if (aspects.length !== 9) {
      if (aspectsNotice) {
        aspectsNotice.textContent = 'Expected 9 aspects, got ' + aspects.length + '. Check manifest integrity.';
        aspectsNotice.className = 'msg msg-error small';
        aspectsNotice.classList.remove('hidden');
      }
    }

    // Show temporal status: check chart series temporal availability
    var chartSeries = m.chart && m.chart.series ? m.chart.series : {};
    var temporalAspects = Object.keys(chartSeries).length;
    if (aspectsNotice) {
      if (temporalAspects === 9) {
        var blockedCount = aspects.filter(function (a) { return (a.readiness||'').toLowerCase()==='blocked'; }).length;
        var caveatedCount = aspects.filter(function (a) { return (a.readiness||'').toLowerCase()==='caveated'; }).length;
        aspectsNotice.textContent = '9-aspect temporal model active: chart shows per-aspect demand traces (composite = mean excluding blocked). Blocked: ' + blockedCount + ', Caveated: ' + caveatedCount + '. Do not interpret as calibrated grade.';
        aspectsNotice.className = 'msg small';
        aspectsNotice.style.background = '#f0fdf4';
        aspectsNotice.style.border = '1px solid #bbf7d0';
        aspectsNotice.style.padding = '8px 10px';
        aspectsNotice.style.borderRadius = '8px';
        aspectsNotice.classList.remove('hidden');
      } else {
        // Check old fallback
        var hasTemporal = aspects.some(function (a) { return a.temporal_series || a.series; });
        if (!hasTemporal && temporalAspects !== 9) {
          aspectsNotice.textContent = 'Aspects are grouped coverage — no temporal timeline series. Do not interpret as calibrated scores.';
          aspectsNotice.className = 'msg small';
          aspectsNotice.style.background = '#f8fafc';
          aspectsNotice.style.border = '1px dashed #cbd5e1';
          aspectsNotice.style.padding = '8px 10px';
          aspectsNotice.style.borderRadius = '8px';
          aspectsNotice.classList.remove('hidden');
        }
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

      // Show temporal trace preview if available
      var temporalPreview = '';
      if (series && series.normalized_values) {
        var vals = series.normalized_values;
        var definedVals = vals.filter(function (v) { return v != null; });
        if (definedVals.length) {
          var minV = Math.min.apply(null, definedVals).toFixed(2);
          var maxV = Math.max.apply(null, definedVals).toFixed(2);
          var meanV = (definedVals.reduce(function (a,b){return a+b;},0)/definedVals.length).toFixed(2);
          temporalPreview = '<div class="small muted" style="margin-top:6px">Temporal: n=' + vals.length + ' \u00b7 min ' + minV + ' \u00b7 max ' + maxV + ' \u00b7 mean ' + meanV + (series.blocked ? ' \u00b7 blocked (no trace)' : '') + (series.caveated ? ' \u00b7 caveated' : '') + '</div>';
        } else if (series.blocked) {
          temporalPreview = '<div class="small muted" style="margin-top:6px">Temporal: blocked — no windowed signal</div>';
        }
      }

      card.innerHTML = '\n        <div class="aspect-head">\n          <div class="aspect-title">\n            <span class="aspect-num">' + num + '</span>\n            <span class="aspect-id mono small">' + esc(aspectId) + '</span>\n            <span class="' + badgeClass + '">' + esc(readinessLabel) + '</span>\n            ' + extraNote + '\n          </div>\n          <div class="aspect-label">' + esc(label) + '</div>\n          <div class="small muted">' + esc(description) + '</div>\n          ' + temporalPreview + '\n        </div>\n        <div class="aspect-body">\n          <div class="aspect-field">\n            <div class="k">Included feature IDs <span class="small muted">(' + included.length + ')</span></div>\n            <div class="v aspect-features">' + includedHtml + '</div>\n          </div>\n          <div class="aspect-field">\n            <div class="k">Missing / future</div>\n            <div class="v">' + missingHtml + '</div>\n          </div>\n          <div class="aspect-field">\n            <div class="k">Limitations / caveats</div>\n            <div class="v">' + limitHtml + '</div>\n          </div>\n          ' + (a.features || a.feature_summaries ? '<div class="small muted" style="margin-top:8px">Sample values: ' + (a.features||a.feature_summaries).slice(0,2).map(function (f) { return esc(f.feature_id)+': '+fmt(f.value)+' '+esc(f.units||''); }).join(' \u00b7 ') + ((a.features||a.feature_summaries).length>2 ? ' \u00b7 \u2026' : '') + '</div>' : '') + '\n        </div>\n      ';
      aspectsGrid.appendChild(card);
    });
  }

  function renderChart() {
    var m = state.manifest;
    if (!m) return;
    var W = 960, H = 340;
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
      var label = region ? (region.measure_numbers ? 'm' + region.measure_numbers[0] : 'w' + i) : 'w' + i;
      gGrid.appendChild(svgEl('text', { x: x, y: H - margin.bottom + 14, 'text-anchor': 'middle', class: 'tick-label' }, label));
    }
    gGrid.appendChild(svgEl('rect', { x: margin.left, y: margin.top, width: plotW, height: plotH, fill: 'none', class: 'axis' }));
    chartSvg.appendChild(gGrid);

    function buildPath(values) {
      var d = '';
      var hasSegment = false;
      values.forEach(function (v, i) {
        if (v == null || isNaN(v)) {
          hasSegment = false;
          return;
        }
        var x = margin.left + (i / Math.max(1, values.length - 1)) * plotW;
        var y = margin.top + (1 - clamp01(v)) * plotH;
        if (!hasSegment) {
          d += (d ? ' M ' : 'M ') + x + ' ' + y;
          hasSegment = true;
        } else {
          d += ' L ' + x + ' ' + y;
        }
      });
      return d;
    }

    var aspectIds = m.chart.aspect_ids || m.chart.factor_ids || Object.keys(seriesMap);
    aspectIds.forEach(function (aid) {
      if (!state.enabled.has(aid)) return;
      var s = seriesMap[aid];
      if (!s) return;
      if (s.blocked) return;
      var vals = s.normalized_values || s.smoothed_values || [];
      // Skip if all null
      if (!vals.some(function (v){ return v!=null;})) return;
      var d = buildPath(vals);
      if (!d) return;
      var color = ASPECT_COLORS[aid] || FACTOR_COLORS[aid] || '#334155';
      var path = svgEl('path', { d: d, class: 'series-path', stroke: color, opacity: '0.92' });
      path.setAttribute('data-aspect', aid);
      path.setAttribute('data-factor', aid);
      chartSvg.appendChild(path);
    });

    if (state.compositeEnabled && composite && composite.normalized_values) {
      var vals = composite.normalized_values;
      if (vals.some(function (v){return v!=null;})) {
        var d = buildPath(vals);
        if (d) {
          var p = svgEl('path', { d: d, class: 'series-path', stroke: COMPOSITE_COLOR, 'stroke-dasharray': '7 5', 'stroke-width': '2.2', opacity: '0.95' });
          p.setAttribute('data-factor', 'composite.aspect_demand');
          p.setAttribute('data-aspect', 'composite.aspect_demand');
          chartSvg.appendChild(p);
        }
      }
    }

    var hotspots = [].concat(m.hotspots || []).sort(function (a,b) { return (a.rank||99)-(b.rank||99); });
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
      chartXLabels.textContent = 'Windows 0\u2013' + (N-1) + '  \u00b7  Measures ' + first + '\u2013' + last + '  \u00b7  ' + N + ' windows';
    }
  }

  function renderHotspotList() {
    var m = state.manifest;
    if (!m || !m.hotspots) return;
    hotspotList.innerHTML = '';
    [].concat(m.hotspots).sort(function (a,b) { return a.rank-b.rank; }).forEach(function (h) {
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
    var h = (m.hotspots||[]).find(function (x) { return x.id===id; });
    if (!h) return;
    state.selectedId = id;
    renderChart();
    renderHotspotList();
    renderDetail(h);
  }

  function renderDetail(h) {
    detailEmpty.classList.add('hidden');
    detailContent.classList.remove('hidden');

    var aspectContribs = h.aspect_contributors || h.top_contributors || h.contributions || [];
    var suppAspects = (h.supporting_aspect_ids || h.supporting_factor_ids || []).join(', ') || '\u2014';
    var suppWindows = (h.supporting_window_indices || []);
    var rep = h.representative_region || {};
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

    // --- Explanation (deterministic heuristic, LLM-free v0) ---
    var explanation = h.explanation || buildFallbackExplanation(h, state.manifest ? state.manifest.chart : null);
    var top3 = aspectContribs.slice().sort(function(a,b){ return (a.rank||99)-(b.rank||99); }).slice(0,3);
    var chipsHtml = top3.length ? top3.map(function(c){
      var aid = c.aspect_id || c.feature_id || c.id;
      var color = ASPECT_COLORS[aid] || '#64748b';
      var strength = strengthLabel(c.normalized_value);
      var role = roleLabel(c.rank);
      var plain = plainAspect(aid);
      return '<span class="aspect-chip" style="border-color:' + color + '"><span class="swatch" style="background:' + color + '"></span>' + esc(plain) + ' <span class="small muted">' + esc(strength) + ' \u00b7 ' + esc(role) + '</span></span>';
    }).join('') : '<span class="small muted">No strong contributor \u2014 distributed evidence</span>';

    // Build collapsed evidence (old full contributor list)
    var contributorsHtml = '';
    if (aspectContribs.length) {
      contributorsHtml = aspectContribs.map(function (c) {
        var fid = c.aspect_id || c.feature_id || c.id;
        var color = ASPECT_COLORS[fid] || '#334155';
        var readiness = (c.readiness || '').toLowerCase();
        var badge = '';
        if (readiness === 'blocked') badge = '<span class="badge badge-blocked">blocked</span>';
        else if (readiness === 'caveated') badge = '<span class="badge badge-caveated">caveated</span>';
        else if (readiness === 'partial') badge = '<span class="badge badge-partial">partial</span>';
        var peakBadge = c.is_peak_support ? '<span class="badge-peak">peak support</span>' : '';
        var featureHtml = '';
        var feats = c.feature_contributors || c.supporting_feature_contributors || [];
        if (feats.length) {
          featureHtml = '<div class="small" style="margin-top:6px"><strong>Supporting features:</strong><ul style="margin:4px 0 0 16px">' +
            feats.slice(0,5).map(function (f) {
              return '<li><code class="mono small">' + esc(f.feature_id) + '</code> \u2014 ' + esc(plainFeature(f.feature_id, f.label || f.feature_name || '')) +
                ' <span class="small muted">raw ' + fmt(f.raw_value) + ' \u00b7 norm ' + fmt(f.normalized_value) + ' \u00b7 share ' + (f.contribution_share!=null? (f.contribution_share*100).toFixed(1)+'%':'\u2014') + '</span></li>';
            }).join('') + (feats.length>5? '<li class="small muted">\u2026 +' + (feats.length-5) + ' more</li>':'') + '</ul></div>';
        }
        return '<div class="contributor">\n          <div class="contributor-head">\n            <span><span class="swatch" style="background:' + color + ';display:inline-block;width:10px;height:10px;border-radius:999px;margin-right:6px;vertical-align:middle"></span>' + esc(c.label || fid) + ' <code class="mono small">' + esc(fid) + '</code> ' + badge + '</span>\n            <span class="small muted">#' + esc(String(c.rank||'')) + ' \u00b7 share ' + (c.contribution_share!=null? (c.contribution_share*100).toFixed(1)+'%':'\u2014') + ' ' + peakBadge + '</span>\n          </div>\n          <div class="contributor-meta">normalized ' + fmt(c.normalized_value) + ' \u00b7 weighted ' + fmt(c.weighted_value) + ' \u00b7 strength ' + esc(strengthLabel(c.normalized_value)) + '</div>\n          ' + featureHtml + '\n        </div>';
      }).join('');
    } else {
      contributorsHtml = '<div class="small muted">No aspect contributors in this hotspot.</div>';
    }

    var confidenceBadge = explanation.confidence ? '<span class="badge badge-heuristic">' + esc(explanation.confidence) + '</span>' : '';
    var timelineHtml = explanation.timeline_context ? '<p class="small muted" style="margin:6px 0 0">' + esc(explanation.timeline_context) + '</p>' : '';

    detailContent.innerHTML = '\n      <div style="display:flex;justify-content:space-between;gap:8px;align-items:start">\n        <div>\n          <div class="eyebrow">Hotspot #' + esc(String(h.rank||'')) + ' ' + confidenceBadge + '</div>\n          <h3 style="margin:2px 0 4px">' + esc(explanation.headline || h.label || h.id) + '</h3>\n          <div class="small muted">Measure range <strong>' + esc(h.measure_range || (h.measure_numbers||[]).join('\u2013') || '') + '</strong> \u00b7 Window indices ' + esc(suppWindows.length? suppWindows.join(', '): String(rep.window_index != null ? rep.window_index : '')) + '</div>\n        </div>\n        <span class="badge" style="background:#eef6ff;border-color:#bfdbfe;color:#1e40af">score ' + esc((h.score_value!=null)? h.score_value.toFixed(3): (h.score!=null? h.score.toFixed(3):'?')) + '</span>\n      </div>\n      ' + snippetHtml + '\n      <div class="explanation-card">\n        <div class="explanation-head"><span class="eyebrow">Heuristic explanation</span> ' + confidenceBadge + ' <span class="small muted">deterministic \u00b7 no LLM</span></div>\n        <p class="explanation-summary">' + esc(explanation.summary || '') + '</p>\n        <div class="aspect-chips">' + chipsHtml + '</div>\n        <div class="explanation-grid">\n          <div class="explanation-field"><div class="k">How aspects combine</div><div class="v small">' + esc(explanation.aspect_interplay || '') + '</div></div>\n          <div class="explanation-field"><div class="k">Score cue</div><div class="v small">' + esc(explanation.score_cue || '') + '</div></div>\n        </div>\n        ' + timelineHtml + '\n        <p class="small muted" style="margin:8px 0 0;font-style:italic">Relative evidence within this piece \u00b7 not a calibrated grade, learner diagnosis, or practice prescription.</p>\n      </div>\n      <details class="evidence-disclosure"><summary>Show evidence</summary><div class="evidence-body">\n        <div class="detail-section">\n          <h4>Window &amp; position</h4>\n          <ul class="kv-list">\n            <li><span>Section</span><span class="mono">' + esc(h.section_id || h.id) + '</span></li>\n            <li><span>Offsets</span><span class="mono">' + esc(h.start_offset||'') + ' \u2192 ' + esc(h.end_offset||'') + '</span></li>\n            <li><span>Score position</span><span class="mono">' + esc(String(h.score_position != null ? h.score_position : '')) + '</span></li>\n            <li><span>Representative</span><span class="mono">' + esc(rep.label || '') + '</span></li>\n            <li><span>Measures (detail)</span><span>' + esc((h.measure_numbers||[]).join(', ')) + '</span></li>\n            <li><span>Method</span><span class="mono small">' + esc(h.method||'') + '</span></li>\n          </ul>\n        </div>\n        <div class="detail-section">\n          <h4>Aspect contributors (full)</h4>\n          ' + contributorsHtml + '\n          <ul class="kv-list" style="margin-top:10px">\n            <li><span>Supporting aspect IDs</span><span class="mono small" style="text-align:right;max-width:190px">' + esc(suppAspects) + '</span></li>\n            <li><span>Supporting windows</span><span class="mono small">' + esc(suppWindows.length ? suppWindows.join(', ') : String(rep.window_index != null ? rep.window_index : '')) + '</span></li>\n          </ul>\n        </div>\n        <div class="detail-section">\n          <h4>Caveats</h4>\n          <ul class="small" style="margin:6px 0 0 16px">' + (state.manifest.caveats||[]).slice(0,4).map(function (t){ return '<li>' + esc(t) + '</li>'; }).join('') + '</ul>\n        </div>\n      </div></details>\n    ';
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
  function escAttr(s) { return String(s).replace(/"/g,'&quot;'); }
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

    // Probe API availability
    fetch('/api/datasets', { cache: 'no-cache' }).then(function (r) {
      if (!r.ok) throw new Error('HTTP '+r.status);
      return r.json();
    }).then(function (data) {
      if (liveHint) {
        var cipi = (data.datasets||[]).find(function(d){return d.id==='cipi';});
        var oktav = (data.datasets||[]).find(function(d){return d.id==='oktav';});
        var parts = [];
        if (cipi) parts.push('CIPI:'+cipi.count);
        if (oktav) parts.push('Oktav:'+oktav.count);
        liveHint.textContent = parts.length ? 'Live server ready — ' + parts.join(' · ') + ' · labels provenance only' : 'Live server ready';
        liveHint.classList.remove('hidden');
      }
    }).catch(function () {
      if (liveHint) {
        liveHint.textContent = 'Live mode requires: python research/learning_support/ceo_demo/scripts/run_live_demo_server.py  (then reopen this page via that server)';
        liveHint.classList.remove('hidden');
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
        var idLine = (item.dataset_id || item.cipi_id || item.piece_id || '') + (item.dataset_relative_path ? ' · ' + item.dataset_relative_path : '');
        var labelLine = item.difficulty_label || item.henle || '';
        if (item.dataset === 'oktav' && item.difficulty_label) labelLine = item.difficulty_label;
        if (item.dataset === 'cipi' && item.henle) labelLine = 'Henle ' + item.henle;
        var existsBadge = item.exists === false ? '<span class="live-badge" style="background:#fef2f2;border-color:#fecaca;color:#7f1d1d">missing file</span>' : '';
        btn.innerHTML = '<span class="live-result-title">' + esc(displayTitle) + existsBadge + '</span>' +
          '<span class="live-result-sub">' + esc(idLine) + '</span>' +
          (labelLine ? '<span class="live-result-meta">' + esc(labelLine) + '</span>' : '');
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
      setLiveStatus('Searching ' + dataset + (q ? ' for "' + q + '"': '') + '…');
      liveResults.innerHTML = '<div class="live-empty">Searching…</div>';
      if (btnAnalyze) btnAnalyze.disabled = true;
      liveState.selected = null;
      var url = '/api/pieces?dataset=' + encodeURIComponent(dataset) + '&q=' + encodeURIComponent(q) + '&limit=50';
      fetch(url, { cache: 'no-cache' }).then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      }).then(function (data) {
        liveState.results = data.results || [];
        setLiveStatus('Found ' + liveState.results.length + ' result(s) in ' + dataset + (q ? ' for "' + q + '"' : ''));
        renderLiveResults();
      }).catch(function (err) {
        showLiveError('Search failed: ' + err.message + ' — is the live server running?');
        setLiveStatus('');
        liveResults.innerHTML = '<div class="live-empty">Search failed. Requires live server.</div>';
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
        setLiveStatus('Queueing analysis for "' + (sel.title || sel.dataset_relative_path) + '"…');
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
          setLiveStatus('Job ' + jobId + ' queued — running analysis…');
          pollJob(jobId);
        }).catch(function (err) {
          showLiveError('Analyze failed: ' + err.message);
          setLiveStatus('');
          btnAnalyze.disabled = false;
          btnAnalyze.textContent = 'Analyze selected';
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
            setLiveStatus('Job ' + jobId + ' ' + st + '… (' + attempts + 's)');
            if (attempts < maxAttempts) setTimeout(tick, 1000);
            else {
              showLiveError('Job polling timed out after 120s. Check server logs.');
              if (btnAnalyze) { btnAnalyze.disabled = false; btnAnalyze.textContent = 'Analyze selected'; }
            }
            return;
          }
          if (st === 'succeeded') {
            var url = job.manifest_url || job.manifest_url_rel;
            if (!url) { showLiveError('Job succeeded but no manifest_url returned.'); return; }
            setLiveStatus('Analysis complete — loading chart…');
            loadLiveManifest(url, job);
            if (btnAnalyze) { btnAnalyze.disabled = false; btnAnalyze.textContent = 'Analyze selected'; }
            return;
          }
          if (st === 'failed') {
            var err = job.error || 'Unknown error';
            showLiveError('Analysis failed: ' + err);
            if (job.log) console.error('Job log:', job.log);
            setLiveStatus('Failed');
            if (btnAnalyze) { btnAnalyze.disabled = false; btnAnalyze.textContent = 'Analyze selected'; }
            return;
          }
          showLiveError('Unexpected job status: ' + st);
        }).catch(function (err) {
          showLiveError('Polling failed: ' + err.message);
          if (btnAnalyze) { btnAnalyze.disabled = false; btnAnalyze.textContent = 'Analyze selected'; }
        });
      }
      setTimeout(tick, 800);
    }

    function loadLiveManifest(manifestUrl, job) {
      // Reuse existing chart flow: fetch manifest then render
      showLiveError('');
      fetch(manifestUrl, { cache: 'no-cache' }).then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      }).then(function (data) {
        if (!data.chart || !data.hotspots) throw new Error('Invalid manifest: missing chart/hotspots');
        // Derive base for snippets: manifestUrl directory
        var base = manifestUrl.slice(0, manifestUrl.lastIndexOf('/') + 1);
        // Set global state like loadManifest does
        state.manifest = data;
        state.manifestBase = base;
        state.selectedPieceId = null; // live piece not in catalog
        var ids = (data.chart.aspect_ids && data.chart.aspect_ids.length) ? data.chart.aspect_ids : (data.chart.factor_ids || []);
        state.enabled = new Set();
        ids.forEach(function (id) {
          var series = data.chart.series && data.chart.series[id];
          if (series && series.blocked) return;
          state.enabled.add(id);
        });
        if (state.enabled.size === 0 && ids.length) ids.slice(0,3).forEach(function(id){state.enabled.add(id);});
        state.compositeEnabled = true;
        var tc = document.getElementById('toggle-composite');
        if (tc) tc.checked = true;
        // Use same onLoaded but need to ensure piece meta shows live provenance
        // Call internal onLoaded via direct render
        // Inline onLoaded steps to avoid catalog dependency
        var m = state.manifest;
        document.getElementById('view-load').classList.add('hidden');
        // Keep live-panel visible? Hide live panel on chart view? Keep shown under load screen only.
        // Show chart view
        document.getElementById('view-chart').classList.remove('hidden');
        // Trigger renders
        // renderMeta etc are in closure; call via window workaround: dispatch to existing functions by reusing code path
        // Instead call the existing render functions directly (they are in closure scope)
        // We have access via closure: renderMeta etc are defined in outer scope and accessible here
        try { renderMeta(m); } catch(e){console.error(e);}
        try { renderToggles(m); } catch(e){console.error(e);}
        try { renderCaveats(m); } catch(e){console.error(e);}
        try { renderAspects(m); } catch(e){console.error(e);}
        try { renderChart(); } catch(e){console.error(e);}
        try { renderHotspotList(); } catch(e){console.error(e);}
        if (m.hotspots && m.hotspots.length) { try { selectHotspot(m.hotspots[0].id); } catch(e){} }
        try { updateOpenScoreUI(); } catch(e){console.error(e);}
        window.scrollTo({ top: 0, behavior: 'smooth' });
        setLiveStatus('Loaded live piece: ' + (job.piece_title || manifestUrl) + ' — manifest: ' + manifestUrl);
      }).catch(function (err) {
        showLiveError('Failed to load live manifest: ' + err.message);
        setLiveStatus('');
      });
    }

    // Initial empty state
    renderLiveResults();
    setLiveStatus('Enter a query and click Search. Live server proxies to local CIPI/Oktav corpora.');
  })();

})();
