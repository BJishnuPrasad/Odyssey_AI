import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import { Compass, Map, Layers, Landmark, History, BookOpen, ArrowUpRight, ArrowRight, Play, Download, Droplets, Mountain, MapPin, X, Info, RefreshCw, ChevronRight, Database, AlertCircle, Activity } from 'lucide-react'
import { request, artifactUrl } from './api'
import Atlas from './components/Atlas'
import ApiStatus from './components/ApiStatus'
import HeritageLibrary, { SiteDetail, SiteQuery } from './components/HeritageLibrary'
const EnvironmentEvidence = lazy(() => import('./components/EnvironmentEvidence'))

const nav = [['explore', Map, 'Research atlas'], ['evidence', Layers, 'Data & evidence'], ['settlements', Landmark, 'Settlement context'], ['runs', History, 'Analysis history'], ['method', BookOpen, 'Methodology']]
const fmt = (number, digits = 0) => number == null ? '—' : Number(number).toLocaleString('en-IN', { maximumFractionDigits: digits })
const date = value => new Date(value).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })
const zoneColors = { High: '#318977', Moderate: '#e4c06a', Low: '#e0926f', 'Insufficient data': '#8492a2' }
nav.push(['library', BookOpen, 'Learning library'], ['glossary', Info, 'Glossary'], ['lessons', Layers, 'Learning modules'], ['references', BookOpen, 'References'])
nav.splice(2, 0, ['environment', Droplets, 'Environmental evidence'])
function savedRole() { try { return localStorage.getItem('geodyssey-role') || 'practitioner' } catch { return 'practitioner' } }

function Badge({ children, tone = '' }) { return <span className={`badge ${tone}`}>{children}</span> }
function Empty({ title, children }) { return <div className="empty"><Compass size={32} /><h3>{title}</h3><p>{children}</p></div> }
function Metric({ icon: Icon, label, value, unit, note }) { return <div className="metric"><div className="metric-top"><span>{label}</span><Icon size={18} /></div><div className="metric-value">{value}<small>{unit}</small></div><p>{note}</p></div> }

export default function GeoDyssey() {
  const [tab, setTab] = useState(() => savedRole() === 'student' ? 'library' : 'explore')
  const [role, setRole] = useState(savedRole)
  const [detailId, setDetailId] = useState(null)
  const [glossaryQuery, setGlossaryQuery] = useState('')
  function openSite(id) { setDetailId(id); setTab('site') }
  function changeRole(value) { setRole(value); try { localStorage.setItem('geodyssey-role', value) } catch { /* optional preference */ } setTab(value === 'student' ? 'library' : 'explore') }
  const [catalog, setCatalog] = useState([])
  const [boundary, setBoundary] = useState(null)
  const [baseSites, setBaseSites] = useState(null)
  const [siteResults, setSiteResults] = useState(null)
  const [runs, setRuns] = useState([])
  const [selected, setSelected] = useState(null)
  const [run, setRun] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refresh, setRefresh] = useState(0)
  const [error, setError] = useState('')
  const [runError, setRunError] = useState('')
  const [dialog, setDialog] = useState(false)
  const [resolution, setResolution] = useState(250)
  const [weight, setWeight] = useState(0.55)
  const [submitting, setSubmitting] = useState(false)
  const [mode, setMode] = useState('terrain')
  const [cell, setCell] = useState(null)
  const [cellError, setCellError] = useState('')
  const [focusSite, setFocusSite] = useState(null)
  const inspectSequence = useRef(0)
  const report = run?.id === selected && run?.status === 'completed' ? run.summary : null
  const sites = report && siteResults?.id === selected ? siteResults.data : baseSites
  const active = runs.some(r => ['queued', 'running'].includes(r.status)) || ['queued', 'running'].includes(run?.status)

  async function load() {
    setLoading(true); setError(''); setRunError('')
    try {
      const [data, geometry, locations, history] = await Promise.all([request('/catalog'), request('/boundary'), request('/sites'), request('/runs')])
      setCatalog(data.datasets); setBoundary(geometry); setBaseSites(locations); setRuns(history)
      setSelected(previous => previous || history[0]?.id || null)
      setRefresh(n => n+1)
    } catch (e) { setError(`Could not connect to the research API. ${e.message}`) }
    finally { setLoading(false) }
  }
  // Loading flags accompany external API synchronization, not derived render state.
  // oxlint-disable-next-line react/set-state-in-effect
  useEffect(() => { load() }, [])
  useEffect(() => {
    if (!selected) return
    let stopped = false
    let timer
    // Clear inspection while synchronizing a new external run.
    // oxlint-disable-next-line react/set-state-in-effect
    setCell(null); setCellError(''); inspectSequence.current++
    async function poll() {
      try {
        const current = await request(`/runs/${selected}`)
        if (stopped) return
        setRun(current)
        const history = await request('/runs')
        if (stopped) return
        setRuns(history)
        if (current.status === 'completed') {
          const data = await request(`/runs/${selected}/artifacts/sites.geojson`)
          if (!stopped) setSiteResults({ id: selected, data })
        } else if (['queued', 'running'].includes(current.status)) timer = setTimeout(poll, 1600)
        if (!stopped) setRunError('')
      } catch (e) { if (!stopped) { setRunError(e.message); timer = setTimeout(poll, 5000) } }
    }
    poll()
    return () => { stopped = true; clearTimeout(timer) }
  }, [selected, refresh])

  async function start() {
    setSubmitting(true); setError('')
    try {
      const created = await request('/runs', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ resolution_m: resolution, slope_weight: weight }) })
      setRuns(old => [created, ...old]); setSelected(created.id); setDialog(false); setTab('explore')
    } catch (e) { setError(e.message) }
    finally { setSubmitting(false) }
  }
  async function inspect(latlng) {
    if (!report) return
    const sequence = ++inspectSequence.current
    setCell(null); setCellError('Inspecting this location…')
    try {
      const result = await request(`/runs/${selected}/cell?lat=${latlng.lat}&lng=${latlng.lng}`)
      if (sequence === inspectSequence.current) { setCell(result); setCellError('') }
    } catch (e) { if (sequence === inspectSequence.current) setCellError(e.message) }
  }
  const snapshotCatalog = tab === 'evidence' ? catalog : report?.datasets || catalog
  const available = snapshotCatalog.filter(d => d.status === 'available').length

  return <div className="shell">
    <aside className="sidebar">
      <a className="brand" href="#" onClick={e => { e.preventDefault(); setTab('explore') }}><span className="brand-mark"><Compass size={27} /></span><span>GeoDyssey<small>LANDSCAPES · WATER · HERITAGE</small></span></a>
      <div className="workspace-label">RESEARCH WORKSPACE</div>
      <nav aria-label="Main navigation">{nav.map(([id, Icon, title]) => <button key={id} aria-label={title} aria-current={tab === id ? 'page' : undefined} className={tab === id ? 'nav active' : 'nav'} onClick={() => setTab(id)}><Icon size={18} /><span>{title}</span>{tab === id && <ChevronRight size={15} />}</button>)}</nav>
      <div className="region-card"><div className="region-art"><span /><MapPin size={26} /></div><small>STUDY REGION</small><strong>Thanjavur</strong><p>Tamil Nadu, India</p><div><span className="dot" /> District-scale research</div></div>
      <div className="sidebar-bottom"><div><Database size={15} /> Local workspace</div><p>SQLite · Files stored on your device</p><small>GeoDyssey / Research edition 1.0</small></div>
    </aside>
    <div className="main-shell">
      <header className="topbar"><div><span>Workspace</span><ChevronRight size={14} /><strong>{(tab === 'site' ? 'Site 3D & subsurface' : nav.find(n => n[0] === tab)?.[2])}</strong></div><div className="topbar-right"><ApiStatus onReconnect={load} /><span className="avatar">GP</span></div></header>
      <main>
        <div className="role-switch"><label htmlFor="workspace-mode">Workspace mode</label><select id="workspace-mode" value={role} onChange={e => changeRole(e.target.value)}><option value="practitioner">Practitioner</option><option value="student">Researcher / Student</option></select></div>
        <div className="page-heading"><div><div className="eyebrow">THANJAVUR RESEARCH ATLAS <span>11° N / 79° E</span></div><h1>{tab === 'explore' ? 'Read the landscape.' : (tab === 'site' ? 'Site 3D & subsurface' : nav.find(n => n[0] === tab)?.[2])}</h1><p>{tab === 'explore' ? 'Explore the connections between terrain, water and human settlement.' : 'Trace every insight back to its evidence.'}</p></div><button className="primary" disabled={loading || submitting || active} onClick={() => setDialog(true)}><Play size={15} />{active ? 'Analysis in progress' : 'New analysis'}<ArrowUpRight size={16} /></button></div>
        {(error || runError) && <div className="error" role="alert"><AlertCircle size={18} /><span>{error || runError}</span><button onClick={load}>Retry</button><button aria-label="Dismiss error" onClick={() => { setError(''); setRunError('') }}><X size={16} /></button></div>}
        {run && ['queued', 'running'].includes(run.status) && <div className="progress-banner" role="status"><Activity size={19} /><div><strong>{run.stage}</strong><div className="progress-track"><span style={{ width: `${run.progress}%` }} /></div></div><span>{run.progress}%</span></div>}
        {run?.status === 'failed' && <div className="error" role="alert"><AlertCircle size={18} /><span>This run failed: {run.error}. Previous runs remain available in Analysis history.</span></div>}
        {tab === 'explore' && <>
          <SiteQuery onOpenSite={openSite} />
          <div className="metrics"><Metric icon={Map} label="Study area" value={fmt(report?.district_area_km2, 1)} unit="km²" note="Calculated from the supplied district boundary" /><Metric icon={Mountain} label="Usable terrain coverage" value={fmt(report?.coverage_percent, 1)} unit="%" note={report ? `${fmt(report.valid_cells)} cells with usable terrain` : 'Run an analysis to measure coverage'} /><Metric icon={Landmark} label="Heritage locations" value={fmt(sites?.features?.length)} unit="records" note="Deduplicated OSM context · not training labels" /><Metric icon={Layers} label="Available evidence" value={available} unit={`/ ${snapshotCatalog.length}`} note="Missing sources remain explicitly unassessed" /></div>
          <div className="atlas-layout"><section className="panel map-panel"><div className="panel-header"><div><span className="eyebrow">SPATIAL EXPLORER</span><h2>Water & landscape</h2></div><Badge tone="amber">Exploratory screening</Badge></div>
            <div className="map-toolbar"><div className="segmented"><button className={mode === 'terrain' ? 'selected' : ''} onClick={() => setMode('terrain')}>Terrain potential</button><button className={mode === 'evidence' ? 'selected' : ''} onClick={() => setMode('evidence')}>Evidence assessment</button></div><span>{report ? `${report.parameters.resolution_m} m grid` : 'No analysis selected'}</span></div>
            <Atlas boundary={boundary} sites={sites} report={report} runId={selected} mode={mode} onInspect={inspect} focusSite={focusSite} onOpenSite={openSite} />
            <div className="map-footer"><span><Info size={14} /> Click inside the district to inspect a grid cell</span><span>WGS84 display · UTM 44N analysis</span></div>
          </section><aside className="insight-column">
            <section className="panel zones"><div className="panel-header"><h2>{mode === 'terrain' ? 'Potential zones' : 'Evidence readiness'}</h2><Droplets size={18} /></div><p className="subtext">{mode === 'terrain' ? 'Relative terrain proxy · unvalidated' : 'Integrated water-storage assessment'}</p>
              {report ? mode === 'terrain' ? <><div className="stacked-bar">{report.zones.map(z => <span key={z.name} style={{ width: `${z.percent}%`, background: zoneColors[z.name] }} />)}</div>{report.zones.map(z => <div className="zone-row" key={z.name}><span className="swatch" style={{ background: zoneColors[z.name] }} /><div><strong>{z.name}</strong><small>{fmt(z.area_km2, 1)} km²</small></div><b>{fmt(z.percent, z.percent > 0 && z.percent < 1 ? 2 : 1)}<small>%</small></b></div>)}<p className="footnote">A high score indicates a terrain pattern to investigate, not confirmed water storage.</p></> : <><div className="readiness"><Layers size={28} /><h3>Insufficient data</h3><p>Rainfall, soil, historical evidence and independent validation are still needed.</p></div><button className="text-button" onClick={() => setTab('evidence')}>Review evidence gaps <ArrowRight size={16} /></button></> : <Empty title="Your analysis starts here">Create a run to calculate real zones from the supplied elevation data.</Empty>}
            </section>
            <section className="panel inspector"><div className="panel-header"><h2>Location details</h2><MapPin size={17} /></div>{cell ? <><div className="coordinates">{cell.lat.toFixed(5)}° N, {cell.lng.toFixed(5)}° E</div><Badge>{cell.terrain_zone} terrain proxy</Badge><dl><div><dt>Elevation</dt><dd>{fmt(cell.elevation_m, 1)} m</dd></div><div><dt>Slope</dt><dd>{fmt(cell.slope_degrees, 2)}°</dd></div><div><dt>Mapped water</dt><dd>{fmt(cell.distance_to_mapped_water_m)} m</dd></div><div><dt>Terrain score</dt><dd>{fmt(cell.terrain_screening_score, 3)}</dd></div></dl><small>Evidence assessment: insufficient data</small></> : <p>{cellError || 'Select a location on the map to explore its elevation, slope and mapped water proximity.'}</p>}</section>
          </aside></div>
          <div className="bottom-grid"><section className="context-card"><span className="eyebrow">TWO TIMESCALES. ONE LANDSCAPE.</span><h2>Evidence before conclusions.</h2><p>Recent mapping describes what is recorded today. Historical interpretation needs dated, georeferenced evidence. Explore both without confusing one for the other.</p><button className="text-button" onClick={() => setTab('evidence')}>Explore the data catalogue <ArrowUpRight size={16} /></button></section><section className="panel exports"><div className="panel-header"><h2>Take your research further</h2><Download size={18} /></div><p>Download the selected run with its parameters and source fingerprints.</p><div className="export-links">{[['terrain.tif', 'GeoTIFF'], ['zones.geojson', 'GeoJSON'], ['report.json', 'Run report']].map(([file, label]) => report ? <a key={file} href={artifactUrl(selected, file)} download><Download size={14} />{label}</a> : <span className="disabled-link" key={file}>{label}</span>)}</div>{report && <small>Run {selected.slice(0, 8)} · {date(run.finished_at)}</small>}</section></div>
        </>}
        {tab === 'evidence' && <><div className="notice"><Info size={19} /><p><strong>{'Current available datasets; previous runs retain their own snapshots.'}</strong> Missing inputs are not replaced by fabricated values. OSM records are mapping observations, not a rainfall or historical time series.</p></div><div className="timescales"><section className="panel"><span className="eyebrow">01 / SHORT TERM</span><h2>Recent conditions</h2><p>Dated rainfall and seasonal satellite indices now provide current environmental context. Inspect acquisition dates, cloud coverage and source resolution.</p><Badge tone="amber">Partial evidence</Badge></section><section className="panel"><span className="eyebrow">02 / LONG TERM</span><h2>Historical landscape</h2><p>Georeferenced satellite-era water maps reveal landscape changes. Older map interpretations and dated palaeochannels can be imported with their supporting sources.</p><Badge tone="muted">Insufficient evidence</Badge></section><section className="panel"><span className="eyebrow">03 / CONTEXT</span><h2>Terrain & geography</h2><p>Elevation supports slope and local terrain-position analysis. Coverage gaps are measured and preserved.</p><Badge>Terrain screening available</Badge></section></div><section className="panel table-panel"><div className="panel-header"><h2>Source catalogue</h2><span>{available} / {snapshotCatalog.length} available</span></div><div className="table-scroll"><table><thead><tr><th>DATASET</th><th>TIMESCALE</th><th>STATUS</th><th>RECORDS</th><th>INTERPRETATION</th></tr></thead><tbody>{snapshotCatalog.map(d => <tr key={d.id}><td><strong>{d.name}</strong><small>{d.path || 'Not supplied'}</small></td><td>{d.timescale}</td><td><Badge tone={d.status === 'available' ? '' : 'muted'}>{d.status === 'available' ? 'Available' : d.status === 'partial' ? 'Partial' : 'Missing'}</Badge></td><td>{fmt(d.features)}</td><td className="note-cell">{d.note}</td></tr>)}</tbody></table></div></section></>}
        {tab === 'settlements' && <><div className="notice"><Landmark size={20} /><p><strong>Heritage context, not archaeological prediction.</strong> Duplicate records and multi-site relation centres are excluded. These locations have not been field verified or assigned settlement dates.</p></div>{report && <div className="metrics three"><Metric icon={Landmark} label="Usable site samples" value={report.settlement_context.sites_with_terrain} unit="sites" note="Locations overlapping usable terrain" /><Metric icon={Mountain} label="Mean site terrain score" value={fmt(report.settlement_context.mean_site_score, 3)} note="Descriptive proxy · no causal interpretation" /><Metric icon={Map} label="Mean district terrain score" value={fmt(report.settlement_context.mean_district_score, 3)} note="Background comparison · not a validation score" /></div>}<section className="panel table-panel"><div className="panel-header"><h2>Recorded heritage locations</h2><Badge tone="amber">OSM inventory</Badge></div><div className="table-scroll"><table><thead><tr><th>LOCATION</th><th>TYPE</th><th>ELEVATION</th><th>MAPPED WATER</th><th>TERRAIN PROXY</th><th /></tr></thead><tbody>{sites?.features.map(f => <tr key={f.properties.osm_id}><td><strong>{f.properties.name}</strong><small>{f.properties.osm_id}</small></td><td>{f.properties.category}</td><td>{fmt(f.properties.elevation_m, 1)} m</td><td>{fmt(f.properties.water_distance_m)} m</td><td>{report ? f.properties.terrain_zone : 'Run analysis'}</td><td><button className="text-button" aria-label={`Locate ${f.properties.name}`} onClick={() => { setFocusSite(f); setTab('explore') }}><MapPin size={16} /> Locate</button></td></tr>)}</tbody></table></div></section>{report && <section className="panel excluded"><h2>Inventory exclusions</h2>{report.excluded_sites.map((s, i) => <p key={i}><strong>{s.name}</strong> — {s.reason}</p>)}</section>}</>}
        {tab === 'runs' && <section className="panel table-panel"><div className="panel-header"><h2>Reproducible analysis history</h2><button className="text-button" onClick={load}><RefreshCw size={15} /> Refresh</button></div>{runs.length ? <div className="table-scroll"><table><thead><tr><th>RUN / CREATED</th><th>GRID</th><th>SLOPE WEIGHT</th><th>STATUS</th><th>PROGRESS</th><th /></tr></thead><tbody>{runs.map(r => <tr key={r.id}><td><strong>{r.id.slice(0, 8)} {selected === r.id && '· Selected'}</strong><small>{date(r.created_at)}</small></td><td>{r.parameters.resolution_m} m</td><td>{r.parameters.slope_weight}</td><td><Badge tone={r.status === 'failed' ? 'amber' : ''}>{r.status}</Badge></td><td>{r.stage}<small>{r.error || `${r.progress}%`}</small></td><td><button className="text-button" onClick={() => { setSelected(r.id); setTab('explore') }}>Open <ArrowUpRight size={16} /></button></td></tr>)}</tbody></table></div> : <Empty title="No runs yet">Start an analysis to create a versioned result and exportable research record.</Empty>}</section>}
        {tab === 'method' && <><div className="method-grid"><section className="panel"><span className="eyebrow">METHOD / TERRAIN SCREENING 1.0</span><h2>A transparent starting point</h2><p>Elevation is reprojected to UTM zone 44N. Slope uses metre spacing. Local terrain position compares each cell to a neighbourhood extending approximately 1 km in each direction.</p><div className="formula">{report?.formula || 'score = 0.55 × flatness + 0.45 × relative lower position'}</div><p>Flatness = exp(−slope / 5). Lower position = clip(0.5 + elevation difference / 10, 0, 1). The weights, 5° slope scale, 10 m terrain scale and thresholds are analyst assumptions; they are not fitted or validated.</p><div className="thresholds"><Badge>High ≥ 0.65</Badge><Badge tone="amber">Moderate 0.40–0.65</Badge><Badge tone="muted">Low &lt; 0.40</Badge></div><p>Invalid cells and cells with less than 80% neighbourhood coverage are insufficient data. Mapped water distance is descriptive context and is not included in this terrain score.</p></section><section className="panel"><span className="eyebrow">SENSITIVITY / ROBUSTNESS</span><h2>How much do assumptions matter?</h2>{report ? <>{report.sensitivity.map(s => <div className="sensitivity" key={s.slope_weight}><div><strong>{Math.round(s.slope_weight * 100)}% slope weight</strong><span>{s.changed_percent}% changed zones</span></div><div className="progress-track"><span style={{ width: `${s.changed_percent}%` }} /></div></div>)}<p>Compared with this run on valid cells. A stable result under these weights does not establish real-world accuracy.</p></> : <p>Run an analysis to compare classifications under three alternative slope weights.</p>}<div className="readiness compact"><strong>Storage and archaeological validation: pending</strong><p>The Environmental evidence page provides a separate surface-water reference comparison. Imported field outcomes are required to assess storage suitability or archaeological presence.</p></div></section></div><section className="panel method-notes"><h2>Scope and interpretation</h2>{(report?.limitations || ['The terrain map is an exploratory proxy, not a storage capacity estimate.', 'Historical fusion, hydrological flow routing and trained prediction require further inputs and validation.']).map((note, i) => <p key={i}><Info size={16} />{note}</p>)}<h3>Technical references</h3><p><a href="https://gdal.org/en/stable/programs/gdaldem.html" target="_blank" rel="noreferrer">GDAL slope and coordinate units <ArrowUpRight size={13} /></a><a href="https://www.usgs.gov/centers/eros/science/usgs-eros-archive-digital-elevation-shuttle-radar-topography-mission-srtm" target="_blank" rel="noreferrer">USGS SRTM source context <ArrowUpRight size={13} /></a></p></section>{report && <section className="panel provenance"><h2>Source fingerprints</h2><p>SHA-256 hashes identify the exact files used in this run.</p>{report.provenance.map(p => <div key={p.path}><strong>{p.path}</strong><code>{p.sha256}</code></div>)}</section>}</>}
        {['library','glossary','lessons','references'].includes(tab) && <HeritageLibrary key={`${tab}-${glossaryQuery}`} section={tab} initialQuery={tab === 'glossary' ? glossaryQuery : ''} onOpenSite={openSite} run={run?.id === selected ? run : null} />}
        {tab === 'environment' && <Suspense fallback={<p>Loading environmental evidence…</p>}><EnvironmentEvidence boundary={boundary} run={run?.id === selected ? run : null} onRefresh={load} /></Suspense>}
        {tab === 'site' && detailId && <SiteDetail key={detailId} siteId={detailId} run={run?.id === selected ? run : null} onBack={() => setTab('library')} />}
        {['method','evidence','explore'].includes(tab) && <div className="glossary-shortcuts"><span>Understand the methods:</span>{['Slope','TWI','NDVI','SoilGrids','Palaeochannel'].map(term => <button className="text-button" key={term} onClick={() => { setGlossaryQuery(term); setTab('glossary') }}>{term} ↗</button>)}</div>}
        <footer className="page-footer"><span>GEODYSSEY <i /> A landscape of questions. Evidence for answers.</span><span>Thanjavur · Research edition</span></footer>
      </main>
    </div>
    {dialog && <RunDialog onClose={() => setDialog(false)} start={start} submitting={submitting} resolution={resolution} setResolution={setResolution} weight={weight} setWeight={setWeight} />}
  </div>
}

function RunDialog({ onClose, start, submitting, resolution, setResolution, weight, setWeight }) {
  const dialog = useRef(null)
  useEffect(() => { dialog.current.showModal() }, [])
  return <dialog className="run-dialog" ref={dialog} onCancel={onClose} onClose={onClose}><div className="panel-header"><span className="eyebrow">CONFIGURE ANALYSIS</span><button className="icon-button" aria-label="Close configuration" onClick={onClose}><X size={20} /></button></div><h2>A new look at the landscape.</h2><p>Create a reproducible terrain-screening run from the available Thanjavur datasets.</p><label htmlFor="resolution">Analysis grid</label><select id="resolution" value={resolution} onChange={e => setResolution(Number(e.target.value))}><option value={100}>100 metres · finer detail</option><option value={250}>250 metres · balanced</option><option value={500}>500 metres · regional overview</option></select><label htmlFor="weight">Slope contribution <strong>{Math.round(weight * 100)}%</strong></label><input id="weight" type="range" min="0.1" max="0.9" step="0.05" value={weight} onChange={e => setWeight(Number(e.target.value))} /><small>Remaining {Math.round((1-weight)*100)}%: relative lower terrain position.</small><div className="notice"><Info size={17} /><p>These are exploratory assumptions. Integrated water-storage potential remains insufficient data until the missing evidence is available.</p></div><button className="primary" disabled={submitting} onClick={start}><Play size={16} />{submitting ? 'Starting…' : 'Start analysis'}<ArrowRight size={17} /></button></dialog>
}
