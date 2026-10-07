/**
 * Pure layout and formatting helpers for the cross-species PAS architecture
 * view. Every export is a pure function: same input, same output, no DOM
 * access and no module-level mutable state, so this file is unit testable.
 *
 * All rows use distance upstream of the gene's distal observed PAS. The full
 * gene profile defines that anchor even when transcript display is limited.
 * Equal distances across species do not establish homologous cleavage sites.
 */

/**
 * Accepts only genuine JS number primitives that are finite.
 * String coercions like Number('') === 0 and Number(false) === 0 are finite
 * but carry no real coordinate information, so we refuse them here.
 */
const finiteNumber = value =>
  typeof value === 'number' && Number.isFinite(value) ? value : null

export const LEVEL_UNASSIGNED = 'unassigned'

const LEVEL_BY_LABEL = Object.assign(Object.create(null), {
  'PAS-L1': 'l1',
  'PAS-L2': 'l2',
  'PAS-L3': 'l3'
})

export const PAS_LEVEL_LEGEND = [
  { key: 'l1', label: 'PAS-L1' },
  { key: 'l2', label: 'PAS-L2' },
  { key: 'l3', label: 'PAS-L3' },
  { key: LEVEL_UNASSIGNED, label: 'Unassigned' }
]

/**
 * Evidence level of a PA site. Anything the atlas did not label — including
 * the literal 'NA' the pipeline writes — is reported as unassigned rather than
 * being folded into the lowest evidence tier.
 * Input is trimmed and upper-cased so case drift in the ETL does not silently
 * paint every site as Unassigned.
 */
export const levelKey = paLevel => {
  const key = typeof paLevel === 'string' ? paLevel.trim().toUpperCase() : ''
  return LEVEL_BY_LABEL[key] || LEVEL_UNASSIGNED
}

export const AXIS_SCALE_LINEAR = 'linear'
export const AXIS_SCALE_LOG = 'log'

/**
 * Floor for the shared axis extent. A gene whose sites all sit within a few
 * base pairs would otherwise produce a near-zero axis on which rounding noise
 * becomes the dominant visual signal.
 */
export const MIN_AXIS_UPSTREAM = 100

const EMPTY_ANCHOR = { position: 0, empty: true }

const genePositions = gene =>
  geneLevelSites(gene)
    .map(site => finiteNumber(site?.position))
    .filter(position => position !== null)

/**
 * The gene's distal (3'-most) PA site — the anchor every other site is measured
 * against. Transcription runs towards higher coordinates on the plus strand and
 * towards lower coordinates on the minus strand, so the 3'-most site is the
 * largest coordinate on + and the smallest on −.
 *
 * Computed across all of the gene's transcripts, so gene-level and
 * transcript-level rows share one anchor and stay vertically comparable.
 */
export const distalAnchor = gene => {
  const positions = genePositions(gene)
  if (!positions.length) return { ...EMPTY_ANCHOR }
  const position =
    gene?.strand === '-' ? Math.min(...positions) : Math.max(...positions)
  return { position, empty: false }
}

/**
 * Base pairs a site sits upstream of the distal anchor. Always >= 0: the anchor
 * is drawn from the same site set, so nothing should lie beyond it, but a
 * strand/annotation mismatch must not push a mark off the right-hand edge.
 * Returns null when either the position or the anchor is unusable, so callers
 * drop the site rather than drawing a phantom mark at the anchor.
 */
export const upstreamDistance = (position, anchor, strand) => {
  const value = finiteNumber(position)
  if (value === null) return null
  if (!anchor || anchor.empty) return null
  const anchorPosition = finiteNumber(anchor.position)
  if (anchorPosition === null) return null
  const distance =
    strand === '-' ? value - anchorPosition : anchorPosition - value
  return Math.max(0, distance)
}

/** How far upstream of its own distal site a gene's PA sites reach, in bp. */
export const geneUpstreamExtent = gene => {
  const anchor = distalAnchor(gene)
  if (anchor.empty) return 0
  const distances = geneLevelSites(gene)
    .map(site => upstreamDistance(site?.position, anchor, gene?.strand))
    .filter(distance => distance !== null)
  return distances.length ? Math.max(...distances) : 0
}

/**
 * One axis extent shared by every compared species — that shared scale is what
 * makes the rows readable against each other. Never zero, so callers can divide.
 */
export const axisMaxUpstream = genes => {
  const extents = (genes || []).map(geneUpstreamExtent)
  return Math.max(MIN_AXIS_UPSTREAM, extents.length ? Math.max(...extents) : 0)
}

/**
 * Horizontal position of a distance as a 0..1 fraction of the track, where 1 is
 * the right-hand edge (the distal PAS, distance 0) and 0 is the most upstream
 * point on the axis. Returns null for an unusable distance.
 *
 * The log scale plots log10(1 + bp), which maps distance 0 to exactly 0 rather
 * than diverging, and gives the near-distal region — where proximal/distal
 * choice actually plays out — room that a linear scale collapses whenever one
 * species carries a far upstream site.
 */
export const axisFraction = (distance, maxUpstream, scale = AXIS_SCALE_LINEAR) => {
  const value = finiteNumber(distance)
  if (value === null) return null
  const max = finiteNumber(maxUpstream)
  if (max === null || max <= 0) return 1
  const clamped = Math.min(max, Math.max(0, value))
  const ratio =
    scale === AXIS_SCALE_LOG
      ? Math.log10(1 + clamped) / Math.log10(1 + max)
      : clamped / max
  return 1 - ratio
}

/** Round step that yields roughly four intervals across the axis. */
const niceStep = max => {
  const raw = max / 4
  const magnitude = 10 ** Math.floor(Math.log10(raw))
  for (const multiple of [1, 2, 5]) {
    if (raw <= multiple * magnitude) return multiple * magnitude
  }
  return 10 * magnitude
}

const linearTickDistances = max => {
  const step = niceStep(max)
  const distances = [0]
  for (let d = step; d < max; d += step) distances.push(d)
  distances.push(max)
  return distances
}

const logTickDistances = max => {
  const distances = [0]
  for (let d = MIN_AXIS_UPSTREAM; d < max; d *= 10) distances.push(d)
  distances.push(max)
  return distances
}

/**
 * Axis ticks in real base pairs, ordered left to right (furthest upstream
 * first, the distal anchor last).
 */
export const axisTicks = (maxUpstream, scale = AXIS_SCALE_LINEAR, axisWidth = 900) => {
  const max = finiteNumber(maxUpstream)
  if (max === null || max <= 0) return []
  const distances =
    scale === AXIS_SCALE_LOG ? logTickDistances(max) : linearTickDistances(max)
  const ticks = [...new Set(distances)]
    .filter(distance => distance >= 0 && distance <= max)
    .sort((a, b) => b - a)
    .map(distance => ({
      distance,
      fraction: axisFraction(distance, max, scale),
      label: formatDistance(distance)
    }))
  const minGap = Math.min(0.49, 80 / Math.max(1, axisWidth))
  const visible = [ticks[0]]
  for (const tick of ticks.slice(1, -1)) {
    if (tick.fraction - visible[visible.length - 1].fraction >= minGap && 1 - tick.fraction >= minGap) {
      visible.push(tick)
    }
  }
  return [...visible, ticks[ticks.length - 1]]
}

/** Signed distance label, e.g. "−1.2 kb". Distance 0 is the anchor itself. */
export const formatDistance = bp => {
  const value = finiteNumber(bp)
  if (value === null) return '—'
  if (value <= 0) return 'distal PAS'
  if (value >= 1000) return `−${(value / 1000).toFixed(1)} kb`
  return `−${Math.round(value)} bp`
}

/** Per-row extent label, so the reader sees the scale the shared axis hides. */
export const formatUpstreamExtent = bp => {
  const value = finiteNumber(bp)
  if (value === null) return 'no sites'
  if (value <= 0) return 'single site'
  if (value >= 1000) return `${(value / 1000).toFixed(1)} kb upstream`
  return `${Math.round(value)} bp upstream`
}

export const MIN_MARK_RADIUS = 5
export const MAX_MARK_RADIUS = 9

/**
 * Relative usage of a site in the selected context.
 * Returns null — not 0 — when the chosen sample never measured this site, so
 * the view can draw "not detected" differently from "detected at zero".
 * In the default (no sample selected) path, a site with no supporting samples
 * (sample_count falsy) also returns null so the first-load view is honest.
 */
export const siteUsage = (site, sampleKey) => {
  if (!sampleKey) {
    if (!site?.sample_count) return null
    return finiteNumber(site?.mean_abundance) ?? 0
  }
  const match = (site?.samples || []).find(sample => sample?.key === sampleKey)
  if (!match) return null
  return finiteNumber(match.abundance)
}

/** Bounded mark radius in px; higher usage produces larger marks. */
export const usageRadius = usage => {
  if (usage === null || usage === undefined) return MIN_MARK_RADIUS
  const bounded = Math.min(1, Math.max(0, Number(usage) || 0))
  return MIN_MARK_RADIUS + Math.sqrt(bounded) * (MAX_MARK_RADIUS - MIN_MARK_RADIUS)
}

/** Marks closer than this fraction of track width would overlap visually. */
export const DEFAULT_MIN_GAP = 0.025
export const MAX_LANES = 3

/**
 * Stagger crowded marks onto raised lanes instead of stacking them.
 * Left to right, first free lane. Deterministic, so a re-render never
 * reshuffles the picture; returns new objects rather than mutating the input.
 * Non-finite x values are never written into laneLastX so they cannot
 * corrupt the gap-tracking state for subsequent valid marks.
 */
export const assignLanes = (points, minGap = DEFAULT_MIN_GAP) => {
  const laneLastX = []
  return [...points]
    .sort((a, b) => a.x - b.x)
    .map(point => {
      let lane = laneLastX.findIndex(lastX => point.x - lastX >= minGap)
      if (lane === -1) lane = laneLastX.length < MAX_LANES ? laneLastX.length : 0
      if (Number.isFinite(point.x)) laneLastX[lane] = point.x
      return { ...point, lane }
    })
}

/** Complete gene profiles are pooled on the server, before display truncation. */
export const geneLevelSites = gene => (gene?.sites || []).filter(site => site?.site_id != null)

/**
 * Turn raw sites into fully resolved marks for PasTrack. Sites are positioned
 * first and numbered second, so P-numbers always read 5-prime to 3-prime (P1 is
 * the most upstream site) regardless of strand or of the order transcripts
 * happened to arrive in. Sites with no usable coordinate are dropped before
 * ordering so they cannot steal a P-number or inject NaN into assignLanes.
 */
export const buildTrackPoints = (
  sites,
  { strand, anchor, maxUpstream, scale, sampleKey }
) => {
  if (!anchor || anchor.empty) return []
  const positioned = (sites || [])
    .map(site => {
      const distance = upstreamDistance(site?.position, anchor, strand)
      if (distance === null) return null
      return {
        key: site.site_id,
        distance,
        x: axisFraction(distance, maxUpstream, scale),
        site
      }
    })
    .filter(point => point !== null && point.x !== null)
    .sort((a, b) => a.x - b.x || String(a.key).localeCompare(String(b.key)))

  return assignLanes(
    positioned.map((point, index) => {
      const usage = siteUsage(point.site, sampleKey)
      const samples = point.site.samples || []
      const selectedObservation = sampleKey ? samples.find(sample => sample.key === sampleKey) : null
      const counts = samples.map(sample => finiteNumber(sample.site_count))
      const supportingReads = sampleKey
        ? finiteNumber(selectedObservation?.site_count)
        : (counts.length && counts.every(count => count !== null) ? counts.reduce((sum, count) => sum + count, 0) : null)
      return {
        ...point,
        order: Number.isInteger(point.site.site_order) ? point.site.site_order : index + 1,
        supportingReads,
        usage,
        radius: usageRadius(usage),
        levelKey: levelKey(point.site.pa_level),
        muted: usage === null
      }
    })
  )
}

export const formatUsage = value => {
  if (value === null || value === undefined) return 'Not called'
  const n = Number(value)
  if (!Number.isFinite(n)) return '—'
  return `${(n * 100).toFixed(1)}%`
}

export const formatCount = value => {
  const n = Number(value)
  if (!Number.isFinite(n)) return '—'
  return n.toLocaleString('en-US')
}

export const formatBiotype = value =>
  value ? String(value).replace(/_/g, ' ') : 'transcript'
