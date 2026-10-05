/* Effects below synchronize the selected site/run with external API resources. */
/* oxlint-disable react/set-state-in-effect */
import { lazy, Suspense, useEffect, useRef, useState } from 'react'
import { request } from '../api'
const SiteModel = lazy(() => import('./SiteModel'))
import './heritage.css'

const display = (v, unit = '') => v == null ? 'Unavailable' : `${Number(v).toFixed(2)}${unit}`
const linkSafe = url => /^https?:\/\//i.test(url || '') ? url : undefined

function Sources({ references = [] }) {
  return <ul className="source-list">{references.map((ref, i) => <li key={i}><a href={linkSafe(typeof ref === 'string' ? ref : ref.url)} target="_blank" rel="noreferrer">{typeof ref === 'string' ? ref : ref.title} ↗</a></li>)}</ul>
}

export function SoilView({ soil }) {
  const max = Math.max(...soil.layers.map(l => l.bottom_cm))
  const colors = ['#e5cd9f', '#d2b283', '#bd946a', '#a77f5c', '#8d6e54', '#735b4b']
  const available = soil.source_kind !== 'unavailable'
  return <div className="soil-view"><span className="badge amber">{soil.confidence} · depth below ground</span><svg viewBox="0 0 520 355" role="img" aria-label="Soil profile cross-section with depth in centimetres"><defs><pattern id="missing-soil" width="9" height="9" patternUnits="userSpaceOnUse"><rect width="9" height="9" fill="#e3e5de" /><path d="M0 9L9 0" stroke="#c6ccc0" /></pattern></defs><text x="16" y="20" fontSize="12">Depth (cm)</text>{soil.layers.map((l, i) => { const y = 36+l.top_cm/max*270, h = (l.bottom_cm-l.top_cm)/max*270; const values = [l.sand_pct,l.silt_pct,l.clay_pct,l.bulk_density_g_cm3,l.organic_carbon_g_kg]; const missing = !available || values.every(v => v == null); return <g key={i}>{(l.top_cm === 0 || l.top_cm >= 30) && <text x="22" y={y+4} fontSize="11">{l.top_cm}</text>}<rect x="82" y={y} width="270" height={h} fill={missing ? 'url(#missing-soil)' : colors[i % colors.length]} stroke="#f7f7ef" /><path d={`M352 ${y} L378 ${40+i*43} L393 ${40+i*43}`} fill="none" stroke="#6d7c70" /><text x="398" y={44+i*43} fontSize="11">{l.top_cm}–{l.bottom_cm} cm</text></g> })}<text x="22" y="310" fontSize="11">{max}</text><text x="82" y="336" fontSize="12">{available ? 'Colour identifies depth interval, not soil class.' : 'Hatched = no data; intervals are a template.'}</text>{soil.cultural_layer_cm && <rect x="82" y={36+soil.cultural_layer_cm[0]/max*270} width="270" height={(soil.cultural_layer_cm[1]-soil.cultural_layer_cm[0])/max*270} fill="none" stroke="#a04737" strokeWidth="3" strokeDasharray="6 3" />}</svg><p>{soil.caveat}</p><div className="table-scroll"><table><thead><tr><th>DEPTH</th><th>SAND / SILT / CLAY %</th><th>BULK DENSITY g/cm³</th><th>ORGANIC C g/kg</th></tr></thead><tbody>{soil.layers.map((l,i) => <tr key={i}><td>{l.top_cm}–{l.bottom_cm} cm<small>{l.label}</small></td><td>{[l.sand_pct,l.silt_pct,l.clay_pct].map(v => v == null ? '—' : v.toFixed(1)).join(' / ')}</td><td>{display(l.bulk_density_g_cm3)}</td><td>{display(l.organic_carbon_g_kg)}</td></tr>)}</tbody></table></div><p><strong>Bedrock:</strong> {soil.bedrock_depth_cm == null ? 'Unknown; no supported depth estimate.' : `${soil.bedrock_depth_cm} cm · ${soil.bedrock_evidence}`}</p><p><strong>Cultural layer:</strong> {soil.cultural_layer_cm ? `${soil.cultural_layer_cm.join('–')} cm · ${soil.cultural_layer_evidence}` : 'Unknown. Site period alone cannot establish burial depth.'}</p><p>Source: {soil.source} {soil.resolution_m && `· ${soil.resolution_m} m grid`} {soil.retrieved_at && `· acquired ${soil.retrieved_at.slice(0,10)}`}</p>{soil.source_url && <Sources references={[soil.source_url]} />}</div>
}

export function TerrainExperiment({ site, run }) {
  const [sample, setSample] = useState(null)
  const [error, setError] = useState('')
  const [slope, setSlope] = useState(true)
  const [position, setPosition] = useState(true)
  const runId = run?.status === 'completed' ? run.id : null
  useEffect(() => {
    let ignore = false
    setSample(null); setError('')
    if (runId && site) {
      const [lng, lat] = site.coordinates
      request(`/runs/${runId}/cell?lat=${lat}&lng=${lng}`).then(data => { if (!ignore) setSample(data) }).catch(e => { if (!ignore) setError(e.message) })
    }
    return () => { ignore = true }
  }, [runId, site])
  const w = run?.parameters?.slope_weight ?? .55
  const flat = sample?.slope_degrees == null ? null : Math.exp(-sample.slope_degrees/5)
  const lower = sample?.relative_lower_position_m == null ? null : Math.min(1, Math.max(0, .5+sample.relative_lower_position_m/10))
  const valid = flat != null && lower != null
  const value = valid && (slope || position) ? (slope ? w*flat : 0)+(position ? (1-w)*lower : 0) : null
  return <section className="terrain-experiment"><h3>Explore the score</h3><p>Live sample from the selected run. Switch contributions off to see the declared heuristic; weights are held fixed and are not renormalised. This experiment does not change the stored run.</p><div className="factor-toggles"><label><input type="checkbox" checked={slope} onChange={e => setSlope(e.target.checked)} />Slope / flatness ({Math.round(w*100)}%)</label><label><input type="checkbox" checked={position} onChange={e => setPosition(e.target.checked)} />Relative lower position ({Math.round((1-w)*100)}%)</label>{['Rainfall','NDVI','TWI'].map(name => <label key={name}><input type="checkbox" disabled />{name} · not in terrain score</label>)}</div>{!runId ? <p>Complete or select an analysis run to use live terrain values.</p> : error ? <p role="alert">{error}</p> : !sample ? <p>Loading terrain…</p> : <><div className="experiment-score"><strong>{value == null ? 'Unassessed' : value.toFixed(3)}</strong><span>Teaching scenario · unvalidated terrain proxy</span></div><p>Slope: {display(sample.slope_degrees, '°')} · elevation: {display(sample.elevation_m, ' m')} · mapped water: {display(sample.distance_to_mapped_water_m, ' m')}</p><p>Flatness contribution: {display(flat == null ? null : (slope ? w*flat : 0))} · position contribution: {display(lower == null ? null : (position ? (1-w)*lower : 0))}</p><p>Integrated evidence assessment remains insufficient data.</p>{sample.environment && <details><summary>Acquired environmental context at this site</summary><dl>{Object.entries(sample.environment).map(([key,item])=><div key={key}><dt>{item.title}</dt><dd>{display(item.value)} {item.units}</dd></div>)}</dl><p>Frozen observations from this run; these values do not alter the terrain-only teaching score.</p></details>}</>}</section>
}

export function SiteDetail({ siteId, run, onBack }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  useEffect(() => {
    let ignore = false
    setData(null); setError('')
    request(`/heritage/${siteId}`).then(d => { if (!ignore) setData(d) }).catch(e => { if (!ignore) setError(e.message) })
    return () => { ignore = true }
  }, [siteId])
  async function upload(event, kind) {
    const file = event.target.files[0]
    event.target.value = ''
    if (!file) return
    setBusy(true); setError('')
    try {
      if (file.size > (kind === 'model' ? 25*1024*1024 : 1024*1024)) throw new Error('File exceeds the upload size limit.')
      const body = kind === 'soil' ? JSON.stringify(JSON.parse(await file.text())) : await file.arrayBuffer()
      await request(`/heritage/${siteId}/${kind}`, { method: 'PUT', headers: { 'Content-Type': kind === 'soil' ? 'application/json' : 'model/gltf-binary' }, body })
      setData(await request(`/heritage/${siteId}`))
    } catch(e) { setError(e.message) } finally { setBusy(false) }
  }
  async function resetModel() {
    setBusy(true); setError('')
    try { const asset = await request(`/heritage/${siteId}/model`, { method: 'DELETE' }); setData(old => ({...old, asset})) } catch(e) { setError(e.message) } finally { setBusy(false) }
  }
  return <div className="heritage-detail"><button className="text-button" onClick={onBack}>← Back to library</button>{error && <div className="error" role="alert">{error}</div>}{!data ? <p>{error ? 'Site could not be loaded.' : 'Loading site evidence…'}</p> : <><section className="panel heritage-intro"><span className="eyebrow">SITE ENCYCLOPEDIA / {data.site.typology}</span><h2>{data.site.title}</h2><div className="site-tags"><span className="badge">{data.site.period}</span><span className="badge muted">History: {data.site.confidence}</span></div><p>{data.summary}</p><small>{data.site.coordinates[1].toFixed(5)}° N, {data.site.coordinates[0].toFixed(5)}° E · {data.site.location_quality}</small></section><div className="heritage-visuals"><section className="panel"><h3>Site in three dimensions</h3><Suspense fallback={<p>Loading 3D viewer…</p>}><SiteModel asset={data.asset} /></Suspense><details><summary>Use your own model</summary><p>Upload a self-contained, uncompressed GLB up to 25 MiB. Export CAD/BIM or a scan to GLB first. Model files stay in this local project.</p><label className="file-control">Upload GLB<input type="file" accept=".glb" disabled={busy} onChange={e => upload(e, 'model')} /></label>{data.asset.tier === 3 && <button className="text-button" disabled={busy} onClick={resetModel}>Use reconstructed approximation</button>}</details><details><summary>Photogrammetry upgrade path</summary><p>A reconstruction needs overlapping photographs, appropriate reuse rights, camera calibration and scale control. The linked official galleries provide reference images, not a complete capture set. Process a suitable image set in COLMAP or another reconstruction tool, then export a GLB for this viewer.</p><a href="https://colmap.github.io/tutorial.html" target="_blank" rel="noreferrer">COLMAP workflow ↗</a></details></section><section className="panel"><h3>Below the surface</h3><SoilView soil={data.soil} /><details><summary>Import a located soil or field profile</summary><p>Supply JSON using the documented SoilProfile schema. Trench, borehole, GPR and resistivity interpretations use the same view, with their own provenance and depth units. Maximum 1 MiB.</p><label className="file-control">Import profile JSON<input type="file" accept=".json" disabled={busy} onChange={e => upload(e, 'soil')} /></label></details></section></div><section className="panel"><TerrainExperiment site={data.site} run={run} /></section><section className="panel"><h3>Sources & reference photographs</h3><Sources references={data.site.references} /></section></>}</div>
}

export default function HeritageLibrary({ section, onOpenSite, run, initialQuery = '' }) {
  const [query, setQuery] = useState(initialQuery)
  const [filters, setFilters] = useState({})
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [selected, setSelected] = useState(null)
  const reader = useRef(null)
  useEffect(() => { if (selected) reader.current?.scrollIntoView({ block: 'start' }) }, [selected])
  const [sites, setSites] = useState([])
  const [exampleId, setExampleId] = useState('')
  const [soil, setSoil] = useState(null)
  const [soilError, setSoilError] = useState('')
  useEffect(() => { let stop=false; request('/library?kind=site').then(d => { if(!stop) {setSites(d.items); setExampleId(d.items[0]?.id || '')} }).catch(e=>{if(!stop)setError(e.message)}); return()=>{stop=true} }, [])
  useEffect(() => {
    let stop = false
    const timer = setTimeout(() => {
      const params = new URLSearchParams({ q: query, ...filters, kind: section === 'glossary' ? 'glossary' : section === 'lessons' ? 'lesson' : section === 'references' ? 'reference' : filters.kind || '' })
      setError(''); setResult(null)
      request(`/library?${params}`).then(d => { if(!stop) setResult(d) }).catch(e => { if(!stop) setError(e.message) })
    }, 180)
    return () => { stop = true; clearTimeout(timer) }
  }, [section, query, filters])
  useEffect(() => {
    let stop = false
    setSoil(null); setSoilError('')
    if (selected?.exercise === 'soil' && exampleId) request(`/heritage/${exampleId}`).then(d => {if(!stop)setSoil(d.soil)}).catch(e => {if(!stop)setSoilError(e.message)})
    return () => {stop=true}
  }, [selected, exampleId])
  const example = sites.find(s => s.id === exampleId)
  function open(item) { if(item.kind === 'site') onOpenSite(item.id); else setSelected(item) }
  return <div className="library"><section className="library-banner"><span className="eyebrow">LEARN FROM THE LANDSCAPE</span><h2>Places, evidence, and the questions between.</h2><p>Explore nine recorded locations, understand the methods, and test ideas against the same data used by the research atlas.</p></section><div className="library-search"><label>Search the library<input type="search" value={query} placeholder="Try a site name, soil, water, or NDVI…" onChange={e => setQuery(e.target.value)} /></label>{section === 'library' && <label>Content<select value={filters.kind || ''} onChange={e=>setFilters({...filters,kind:e.target.value})}><option value="">All content</option><option value="site">Site encyclopedia</option><option value="glossary">Glossary</option><option value="lesson">Learning modules</option><option value="reference">References</option></select></label>}</div>{section === 'library' && <div className="library-filters">{['region','period','typology','confidence'].map(key=><label key={key}>{key === 'typology' ? 'Site type' : key === 'confidence' ? 'Historical documentation' : key}<select value={filters[key] || ''} onChange={e=>setFilters({...filters,[key]:e.target.value})}><option value="">All</option>{(result?.facets[key] || (filters[key] ? [filters[key]] : [])).map(value=><option key={value}>{value}</option>)}</select></label>)}<button className="text-button" onClick={()=>{setFilters({});setQuery('')}}>Clear filters</button></div>}{Object.entries(filters).some(([k,v])=>k!=='kind'&&v) && <p className="filter-note">Site filters apply to site profiles. Clear them to search lessons and glossary terms.</p>}{error && <div className="error" role="alert">{error}</div>}{!result && !error ? <p>Searching the library…</p> : <><p className="library-count">{result?.items.length || 0} results</p><div className="library-grid">{result?.items.map(item=><button className="library-card" key={item.id} onClick={()=>open(item)}><span className="eyebrow">{item.kind === 'site' ? item.typology : item.kind}</span><h3>{item.title}</h3><p>{item.summary}</p><span className="library-card-footer">{item.period || item.tags.join(' · ')} <span>Explore ↗</span></span></button>)}</div>{result?.items.length === 0 && <p className="empty">No matches. Try another spelling or clear the filters.</p>}</>}{selected && <section ref={reader} className="panel library-reader"><div className="panel-header"><span className="eyebrow">{selected.kind}</span><button className="text-button" onClick={()=>setSelected(null)}>Close article</button></div><h2>{selected.title}</h2><p>{selected.summary}</p><p className="article-body">{selected.body}</p>{selected.steps.length > 0 && <ol>{selected.steps.map((step,i)=><li key={i}>{step}</li>)}</ol>}{selected.exercise && <><label className="example-select">Live project example<select value={exampleId} onChange={e=>setExampleId(e.target.value)}>{sites.map(s=><option key={s.id} value={s.id}>{s.title}</option>)}</select></label>{selected.exercise === 'soil' ? soil ? <SoilView soil={soil} /> : <p>{soilError || 'Loading profile…'}</p> : <TerrainExperiment site={example} run={run} />}<button className="text-button" onClick={()=>onOpenSite(exampleId)}>Open the full site profile ↗</button></>}<Sources references={selected.references} /></section>}</div>
}

export function SiteQuery({ onOpenSite }) {
  const [query, setQuery] = useState('')
  const [matches, setMatches] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [sites, setSites] = useState([])
  const [loading, setLoading] = useState(true)
  const [listError, setListError] = useState(false)
  const [open, setOpen] = useState(false)
  const [browseAll, setBrowseAll] = useState(false)
  const [active, setActive] = useState(-1)
  const input = useRef(null)
  const list = useRef(null)
  useEffect(() => {
    let stopped = false
    request('/library?kind=site').then(data => {
      if (!stopped) setSites([...data.items].sort((a,b) => a.title.localeCompare(b.title)))
    }).catch(() => { if (!stopped) setListError(true) }).finally(() => { if (!stopped) setLoading(false) })
    return () => { stopped = true }
  }, [])
  const words = query.toLocaleLowerCase().trim().split(/\s+/).filter(Boolean)
  const options = sites.filter(site => browseAll || words.every(word =>
    `${site.title} ${(site.aliases || []).join(' ')} ${site.typology}`.toLocaleLowerCase().includes(word)))
  useEffect(() => {
    if (open && active >= 0) list.current?.children[active]?.scrollIntoView({block:'nearest'})
  }, [active, open])
  function choose(site) {
    setQuery(site.title); setOpen(false); setActive(-1); setError(''); setMatches(null)
    onOpenSite(site.id)
  }
  function keyDown(event) {
    if (event.key === 'Escape') { event.preventDefault(); setOpen(false); setActive(-1) }
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault(); setOpen(true)
      if (options.length) setActive(index => event.key === 'ArrowDown' ? (index+1)%options.length : (index<=0 ? options.length-1 : index-1))
    }
    if (event.key === 'Enter' && open && active >= 0 && options[active]) {
      event.preventDefault(); choose(options[active])
    }
  }
  async function submit(e) {
    e.preventDefault(); setOpen(false); setError(''); setMatches(null); setBusy(true)
    try { const data = await request(`/heritage/resolve?q=${encodeURIComponent(query)}`); if(data.matches.length === 1) onOpenSite(data.matches[0].id); else setMatches(data.matches) } catch(e) {setError(e.message)} finally {setBusy(false)}
  }
  return <section className="site-query" onBlur={event => { if (!event.currentTarget.contains(event.relatedTarget)) { setOpen(false); setActive(-1) } }}>
    <form onSubmit={submit}>
      <label htmlFor="site-question">Find a heritage site</label>
      <div>
        <div className="site-combobox">
          <div className="site-combobox-field">
            <input ref={input} id="site-question" role="combobox" aria-autocomplete="list" aria-expanded={open} aria-controls="heritage-options" aria-activedescendant={open && active >= 0 && options[active] ? `heritage-option-${options[active].id}` : undefined} aria-describedby="heritage-search-help" autoComplete="off" value={query} disabled={busy} maxLength={300}
              onFocus={() => { setOpen(true); setActive(-1) }} onKeyDown={keyDown}
              onChange={event => { setQuery(event.target.value); setBrowseAll(false); setOpen(true); setActive(-1); setMatches(null); setError('') }} placeholder="Choose a location or type a heritage site name" />
            <button type="button" className="site-dropdown-toggle" aria-label="Show available heritage locations" aria-expanded={open} aria-controls="heritage-options" disabled={busy} onClick={() => { const next=!open; input.current?.focus(); setBrowseAll(true); setActive(-1); setOpen(next) }}>▾</button>
          </div>
          {open && <div className="site-dropdown">
            {loading ? <p role="status">Loading heritage locations…</p> : listError ? <p role="status">Choices are unavailable. Type a name and use Explore site.</p> : <>
              <div ref={list} id="heritage-options" role="listbox" aria-label="Available heritage locations">
                {options.map((site,index) => <button type="button" role="option" aria-selected={active===index} id={`heritage-option-${site.id}`} key={site.id} tabIndex={-1} onClick={() => choose(site)}><strong>{site.title}</strong><small>{site.typology} · {site.period}</small></button>)}
              </div>
              {!options.length && <p>No matching choices. Try another name or use Explore site for a longer question.</p>}
            </>}
          </div>}
        </div>
        <button className="primary" disabled={busy || !query.trim()}>{busy ? 'Finding…' : 'Explore site'}</button>
      </div>
      <p id="heritage-search-help">{sites.length ? `${sites.length} available locations. ` : ''}Choose a location to open its 3D model and soil profile, or search by name.</p>
    </form>
    {error && <p role="alert">{error}</p>}
    {matches && <div>{matches.length ? <><p>Choose the matching location:</p>{matches.map(s=><button className="text-button" key={s.id} onClick={()=>onOpenSite(s.id)}>{s.title}</button>)}</> : <p>No matching heritage record. Try a shorter name or browse the library.</p>}</div>}
  </section>
}
