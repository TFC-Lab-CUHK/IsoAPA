import { describe, expect, it } from 'vitest'
import {
  AXIS_SCALE_LINEAR,
  AXIS_SCALE_LOG,
  DEFAULT_MIN_GAP,
  LEVEL_UNASSIGNED,
  MAX_LANES,
  MAX_MARK_RADIUS,
  MIN_MARK_RADIUS,
  PAS_LEVEL_LEGEND,
  assignLanes,
  axisFraction,
  axisMaxUpstream,
  axisTicks,
  buildTrackPoints,
  distalAnchor,
  formatBiotype,
  formatCount,
  formatDistance,
  formatUpstreamExtent,
  formatUsage,
  geneLevelSites,
  geneUpstreamExtent,
  levelKey,
  siteUsage,
  upstreamDistance,
  usageRadius
} from '../pasLayout'

const site = (overrides = {}) => ({
  site_id: 'site-1',
  position: 1000,
  pa_level: 'PAS-L1',
  mean_abundance: 0.5,
  sample_count: 2,
  samples: [],
  ...overrides
})

const gene = (positions, strand = '+') => {
  const sites = positions.map((p, i) => site({ site_id: `s${i}`, position: p }))
  return { strand, sites, transcripts: [{ transcript_id: 't1', sites }] }
}

describe('levelKey', () => {
  it('maps the three atlas levels', () => {
    expect(levelKey('PAS-L1')).toBe('l1')
    expect(levelKey('PAS-L2')).toBe('l2')
    expect(levelKey('PAS-L3')).toBe('l3')
  })

  it('tolerates case and whitespace drift from the ETL', () => {
    expect(levelKey('  pas-l2 ')).toBe('l2')
  })

  it('reports anything unlabelled as unassigned rather than the lowest tier', () => {
    expect(levelKey('NA')).toBe(LEVEL_UNASSIGNED)
    expect(levelKey(null)).toBe(LEVEL_UNASSIGNED)
    expect(levelKey(undefined)).toBe(LEVEL_UNASSIGNED)
    expect(levelKey('')).toBe(LEVEL_UNASSIGNED)
    expect(levelKey(42)).toBe(LEVEL_UNASSIGNED)
  })

  it('does not leak Object.prototype members as level keys', () => {
    // A plain-object lookup table would return the Object constructor here and
    // render it into a CSS class name.
    expect(levelKey('constructor')).toBe(LEVEL_UNASSIGNED)
    expect(levelKey('toString')).toBe(LEVEL_UNASSIGNED)
    expect(levelKey('__proto__')).toBe(LEVEL_UNASSIGNED)
  })

  it('exposes every level in the legend', () => {
    expect(PAS_LEVEL_LEGEND.map(entry => entry.key)).toEqual([
      'l1',
      'l2',
      'l3',
      LEVEL_UNASSIGNED
    ])
  })
})

describe('distalAnchor', () => {
  it('anchors a plus-strand gene at its highest coordinate', () => {
    expect(distalAnchor(gene([500, 1200, 900], '+'))).toEqual({
      position: 1200,
      empty: false
    })
  })

  it('anchors a minus-strand gene at its lowest coordinate', () => {
    // On the minus strand transcription runs from high to low coordinates, so
    // the 3'-most site is the numerically smallest one.
    expect(distalAnchor(gene([500, 1200, 900], '-'))).toEqual({
      position: 500,
      empty: false
    })
  })

  it('spans every transcript of the gene so rows share one anchor', () => {
    const multi = {
      strand: '+',
      transcripts: [
        { transcript_id: 't1', sites: [site({ site_id: 'a', position: 100 })] },
        { transcript_id: 't2', sites: [site({ site_id: 'b', position: 4000 })] }
      ]
    }
    multi.sites = multi.transcripts.flatMap(transcript => transcript.sites)
    expect(distalAnchor(multi).position).toBe(4000)
  })

  it('reports empty when the gene has no positioned sites', () => {
    expect(distalAnchor({ strand: '+', transcripts: [] }).empty).toBe(true)
    expect(distalAnchor(null).empty).toBe(true)
  })

  it('ignores sites carrying no usable coordinate', () => {
    const dirty = {
      strand: '+',
      transcripts: [
        {
          sites: [
            site({ site_id: 'a', position: null }),
            site({ site_id: 'b', position: '' }),
            site({ site_id: 'c', position: 'oops' }),
            site({ site_id: 'd', position: false }),
            site({ site_id: 'e', position: 700 })
          ]
        }
      ]
    }
    // Number(null), Number('') and Number(false) are all 0 and all finite, so a
    // naive coercion would anchor a plus-strand gene at 700 but drag a minus
    // strand one to a phantom coordinate zero.
    dirty.sites = dirty.transcripts[0].sites
    expect(distalAnchor(dirty)).toEqual({ position: 700, empty: false })
    expect(distalAnchor({ ...dirty, strand: '-' })).toEqual({
      position: 700,
      empty: false
    })
  })
})

describe('upstreamDistance', () => {
  const anchor = { position: 2000, empty: false }

  it('measures base pairs upstream on the plus strand', () => {
    expect(upstreamDistance(2000, anchor, '+')).toBe(0)
    expect(upstreamDistance(1500, anchor, '+')).toBe(500)
  })

  it('measures base pairs upstream on the minus strand', () => {
    const minus = { position: 2000, empty: false }
    expect(upstreamDistance(2000, minus, '-')).toBe(0)
    expect(upstreamDistance(2600, minus, '-')).toBe(600)
  })

  it('never returns a negative distance', () => {
    // Defensive: the anchor is drawn from the same site set, so nothing should
    // sit beyond it, but a strand/annotation mismatch must not push a mark off
    // the right-hand edge of the axis.
    expect(upstreamDistance(2400, anchor, '+')).toBe(0)
    expect(upstreamDistance(1000, { position: 2000, empty: false }, '-')).toBe(0)
  })

  it('returns null for an unusable position or anchor', () => {
    expect(upstreamDistance(null, anchor, '+')).toBeNull()
    expect(upstreamDistance('', anchor, '+')).toBeNull()
    expect(upstreamDistance(false, anchor, '+')).toBeNull()
    expect(upstreamDistance('oops', anchor, '+')).toBeNull()
    expect(upstreamDistance(1500, { position: 0, empty: true }, '+')).toBeNull()
    expect(upstreamDistance(1500, null, '+')).toBeNull()
  })
})

describe('geneUpstreamExtent and axisMaxUpstream', () => {
  it('reports how far upstream a gene reaches from its distal site', () => {
    expect(geneUpstreamExtent(gene([1000, 3000, 2500], '+'))).toBe(2000)
    expect(geneUpstreamExtent(gene([1000, 3000, 2500], '-'))).toBe(2000)
  })

  it('reports zero extent for a single-site or empty gene', () => {
    expect(geneUpstreamExtent(gene([900], '+'))).toBe(0)
    expect(geneUpstreamExtent({ transcripts: [] })).toBe(0)
  })

  it('shares one axis maximum across every compared species', () => {
    const genes = [gene([1000, 2000], '+'), gene([5000, 9000], '+')]
    expect(axisMaxUpstream(genes)).toBe(4000)
  })

  it('never returns a zero maximum, so callers cannot divide by zero', () => {
    expect(axisMaxUpstream([gene([900], '+')])).toBeGreaterThan(0)
    expect(axisMaxUpstream([])).toBeGreaterThan(0)
  })
})

describe('axisFraction', () => {
  it('puts the distal site hard against the right edge', () => {
    expect(axisFraction(0, 4000, AXIS_SCALE_LINEAR)).toBe(1)
    expect(axisFraction(0, 4000, AXIS_SCALE_LOG)).toBe(1)
  })

  it('puts the furthest upstream site at the left edge', () => {
    expect(axisFraction(4000, 4000, AXIS_SCALE_LINEAR)).toBe(0)
    expect(axisFraction(4000, 4000, AXIS_SCALE_LOG)).toBe(0)
  })

  it('scales linearly by base pairs', () => {
    expect(axisFraction(1000, 4000, AXIS_SCALE_LINEAR)).toBeCloseTo(0.75, 10)
    expect(axisFraction(2000, 4000, AXIS_SCALE_LINEAR)).toBeCloseTo(0.5, 10)
  })

  it('expands the near-distal region under the log scale', () => {
    // The proximal/distal choice plays out within a few hundred bp of the
    // distal site, so log spacing must give that region more room than linear.
    const linear = axisFraction(200, 20000, AXIS_SCALE_LINEAR)
    const log = axisFraction(200, 20000, AXIS_SCALE_LOG)
    expect(log).toBeLessThan(linear)
  })

  it('clamps out-of-range distances into the track', () => {
    expect(axisFraction(9000, 4000, AXIS_SCALE_LINEAR)).toBe(0)
    expect(axisFraction(-50, 4000, AXIS_SCALE_LINEAR)).toBe(1)
  })

  it('returns null for an unusable distance', () => {
    expect(axisFraction(null, 4000, AXIS_SCALE_LINEAR)).toBeNull()
    expect(axisFraction('oops', 4000, AXIS_SCALE_LINEAR)).toBeNull()
    expect(axisFraction('', 4000, AXIS_SCALE_LINEAR)).toBeNull()
  })

  it('centres everything when the axis has no extent', () => {
    expect(axisFraction(0, 0, AXIS_SCALE_LINEAR)).toBe(1)
  })
})

describe('axisTicks', () => {
  it('keeps a near-boundary log tick from colliding with the endpoint label', () => {
    const ticks = axisTicks(1144, AXIS_SCALE_LOG, 300)
    expect(ticks.map(tick => tick.distance)).not.toContain(1000)
    expect(ticks[0].distance).toBe(1144)
    expect(ticks.at(-1).distance).toBe(0)
    for (let i = 1; i < ticks.length; i++) {
      expect((ticks[i].fraction - ticks[i - 1].fraction) * 300).toBeGreaterThanOrEqual(80)
    }
  })
  it('labels zero as the distal anchor and ascends upstream', () => {
    const ticks = axisTicks(4000, AXIS_SCALE_LINEAR)
    expect(ticks[ticks.length - 1].distance).toBe(0)
    expect(ticks[0].distance).toBeGreaterThan(0)
  })

  it('places each tick at its own axis fraction', () => {
    for (const tick of axisTicks(4000, AXIS_SCALE_LINEAR)) {
      expect(tick.fraction).toBeCloseTo(
        axisFraction(tick.distance, 4000, AXIS_SCALE_LINEAR),
        10
      )
    }
  })

  it('keeps every tick inside the track', () => {
    for (const scale of [AXIS_SCALE_LINEAR, AXIS_SCALE_LOG]) {
      for (const tick of axisTicks(12345, scale)) {
        expect(tick.fraction).toBeGreaterThanOrEqual(0)
        expect(tick.fraction).toBeLessThanOrEqual(1)
      }
    }
  })
})

describe('formatDistance', () => {
  it('names the anchor rather than printing a bare zero', () => {
    expect(formatDistance(0)).toBe('distal PAS')
  })

  it('prints base pairs upstream with an explicit minus sign', () => {
    expect(formatDistance(350)).toBe('−350 bp')
  })

  it('switches to kilobases past a thousand', () => {
    expect(formatDistance(1200)).toBe('−1.2 kb')
  })

  it('falls back for unusable input', () => {
    expect(formatDistance(null)).toBe('—')
    expect(formatDistance('oops')).toBe('—')
  })
})

describe('formatUpstreamExtent', () => {
  it('describes a gene with one site', () => {
    expect(formatUpstreamExtent(0)).toBe('single site')
  })

  it('describes how far upstream the sites reach', () => {
    expect(formatUpstreamExtent(450)).toBe('450 bp upstream')
    expect(formatUpstreamExtent(2400)).toBe('2.4 kb upstream')
  })

  it('falls back for unusable input', () => {
    expect(formatUpstreamExtent(null)).toBe('no sites')
  })
})

describe('siteUsage', () => {
  it('reads the mean in the aggregate view', () => {
    expect(siteUsage(site({ mean_abundance: 0.4, sample_count: 3 }), '')).toBe(0.4)
  })

  it('reports a never-measured site as null, not zero', () => {
    // The backend emits mean_abundance 0 for a site with no supporting samples.
    // "Not detected" and "detected at zero" are different scientific claims.
    expect(siteUsage(site({ mean_abundance: 0, sample_count: 0 }), '')).toBeNull()
  })

  it('keeps a genuine measured zero distinguishable from not-detected', () => {
    expect(siteUsage(site({ mean_abundance: 0, sample_count: 4 }), '')).toBe(0)
  })

  it('reads the selected sample', () => {
    const s = site({ samples: [{ key: 'brain', abundance: 0.7 }] })
    expect(siteUsage(s, 'brain')).toBe(0.7)
  })

  it('returns null when the selected sample never measured the site', () => {
    const s = site({ samples: [{ key: 'brain', abundance: 0.7 }] })
    expect(siteUsage(s, 'liver')).toBeNull()
  })

  it('returns null for a sample carrying no usable abundance', () => {
    const s = site({ samples: [{ key: 'brain', abundance: null }] })
    expect(siteUsage(s, 'brain')).toBeNull()
  })
})

describe('usageRadius', () => {
  it('keeps mark area proportional by taking the square root', () => {
    const span = MAX_MARK_RADIUS - MIN_MARK_RADIUS
    expect(usageRadius(0)).toBeCloseTo(MIN_MARK_RADIUS, 10)
    expect(usageRadius(1)).toBeCloseTo(MAX_MARK_RADIUS, 10)
    expect(usageRadius(0.25)).toBeCloseTo(MIN_MARK_RADIUS + 0.5 * span, 10)
  })

  it('draws not-detected at the smallest radius', () => {
    expect(usageRadius(null)).toBe(MIN_MARK_RADIUS)
    expect(usageRadius(undefined)).toBe(MIN_MARK_RADIUS)
  })
})

describe('assignLanes', () => {
  it('leaves well-separated marks on the base lane', () => {
    const lanes = assignLanes([{ x: 0.1 }, { x: 0.5 }, { x: 0.9 }]).map(p => p.lane)
    expect(lanes).toEqual([0, 0, 0])
  })

  it('raises marks that would visually collide', () => {
    const lanes = assignLanes([{ x: 0.5 }, { x: 0.505 }, { x: 0.51 }]).map(p => p.lane)
    expect(new Set(lanes).size).toBeGreaterThan(1)
  })

  it('never exceeds the lane budget', () => {
    const crowded = Array.from({ length: 12 }, (_, i) => ({ x: 0.5 + i * 0.0001 }))
    for (const point of assignLanes(crowded)) {
      expect(point.lane).toBeLessThan(MAX_LANES)
    }
  })

  it('is deterministic across repeated runs', () => {
    const input = [{ x: 0.3 }, { x: 0.31 }, { x: 0.7 }]
    expect(assignLanes(input)).toEqual(assignLanes(input))
  })

  it('does not mutate its input', () => {
    const input = [{ x: 0.3 }, { x: 0.1 }]
    const copy = JSON.parse(JSON.stringify(input))
    assignLanes(input)
    expect(input).toEqual(copy)
  })

  it('honours a custom minimum gap', () => {
    expect(DEFAULT_MIN_GAP).toBeGreaterThan(0)
    const lanes = assignLanes([{ x: 0.1 }, { x: 0.2 }], 0.5).map(p => p.lane)
    expect(new Set(lanes).size).toBeGreaterThan(1)
  })
})

describe('geneLevelSites', () => {
  it('uses the complete pooled profile rather than the first transcript usage', () => {
    const shared = {
      sites: [site({ site_id: 'a', mean_abundance: 0.68 }), site({ site_id: 'c' })],
      transcripts: [
        { sites: [site({ site_id: 'a', mean_abundance: 0.4 })] }
      ]
    }
    expect(geneLevelSites(shared).map(s => s.site_id)).toEqual(['a', 'c'])
    expect(siteUsage(geneLevelSites(shared)[0], '')).toBe(0.68)
  })

  it('drops sites with no identity', () => {
    const anonymous = { sites: [site({ site_id: null })] }
    expect(geneLevelSites(anonymous)).toEqual([])
  })

  it('handles a gene with no transcripts', () => {
    expect(geneLevelSites({})).toEqual([])
    expect(geneLevelSites(null)).toEqual([])
  })

  it('does not silently substitute a partial transcript profile for missing pooled data', () => {
    expect(geneLevelSites({ transcripts: [{ sites: [site()] }] })).toEqual([])
  })

  it('keeps the full gene anchor when the distal site is only on an undisplayed transcript', () => {
    const full = {
      strand: '+',
      sites: [site({ position: 100 }), site({ site_id: 'distal', position: 9000 })],
      transcripts: [{ sites: [site({ position: 100 })] }]
    }
    expect(distalAnchor(full).position).toBe(9000)
    expect(geneUpstreamExtent(full)).toBe(8900)
  })
})

describe('buildTrackPoints', () => {
  const context = (overrides = {}) => ({
    strand: '+',
    anchor: { position: 3000, empty: false },
    maxUpstream: 2000,
    scale: AXIS_SCALE_LINEAR,
    sampleKey: '',
    ...overrides
  })

  it('places the distal site at the right edge and numbers upstream first', () => {
    const points = buildTrackPoints(
      [
        site({ site_id: 'distal', position: 3000 }),
        site({ site_id: 'proximal', position: 2000 })
      ],
      context()
    )
    const byKey = Object.fromEntries(points.map(p => [p.key, p]))
    expect(byKey.distal.x).toBe(1)
    expect(byKey.distal.distance).toBe(0)
    expect(byKey.proximal.distance).toBe(1000)
    // P-numbers run 5' to 3', so the upstream site is P1.
    expect(byKey.proximal.order).toBe(1)
    expect(byKey.distal.order).toBe(2)
  })

  it('drops sites with no usable coordinate instead of pinning them to an edge', () => {
    const points = buildTrackPoints(
      [
        site({ site_id: 'a', position: 2500 }),
        site({ site_id: 'bad', position: null }),
        site({ site_id: 'worse', position: 'oops' }),
        site({ site_id: 'c', position: 3000 })
      ],
      context()
    )
    expect(points.map(p => p.key).sort()).toEqual(['a', 'c'])
    expect(points.map(p => p.order).sort()).toEqual([1, 2])
  })

  it('marks a not-detected site as muted while keeping its level', () => {
    const points = buildTrackPoints(
      [site({ site_id: 'a', position: 3000, pa_level: 'PAS-L3', sample_count: 0, mean_abundance: 0 })],
      context()
    )
    expect(points[0].usage).toBeNull()
    expect(points[0].muted).toBe(true)
    expect(points[0].levelKey).toBe('l3')
  })

  it('does not mute a genuine measured zero', () => {
    const points = buildTrackPoints(
      [site({ site_id: 'a', position: 3000, sample_count: 5, mean_abundance: 0 })],
      context()
    )
    expect(points[0].usage).toBe(0)
    expect(points[0].muted).toBe(false)
  })

  it('shares the gene anchor across transcript rows so they stay comparable', () => {
    const shared = context()
    const rowA = buildTrackPoints([site({ site_id: 'a', position: 2000 })], shared)
    const rowB = buildTrackPoints([site({ site_id: 'b', position: 2000 })], shared)
    expect(rowA[0].x).toBe(rowB[0].x)
  })

  it('orients the minus strand so upstream still runs leftwards', () => {
    const points = buildTrackPoints(
      [
        site({ site_id: 'distal', position: 1000 }),
        site({ site_id: 'upstream', position: 2000 })
      ],
      context({ strand: '-', anchor: { position: 1000, empty: false } })
    )
    const byKey = Object.fromEntries(points.map(p => [p.key, p]))
    expect(byKey.distal.x).toBe(1)
    expect(byKey.upstream.distance).toBe(1000)
    expect(byKey.upstream.x).toBeLessThan(byKey.distal.x)
  })

  it('returns an empty track when the gene has no anchor', () => {
    const points = buildTrackPoints([site({ position: 1000 })], {
      ...context(),
      anchor: { position: 0, empty: true }
    })
    expect(points).toEqual([])
  })

  it('assigns every point a lane and a radius', () => {
    const points = buildTrackPoints(
      [site({ site_id: 'a', position: 3000 }), site({ site_id: 'b', position: 2900 })],
      context()
    )
    for (const point of points) {
      expect(typeof point.lane).toBe('number')
      expect(point.radius).toBeGreaterThanOrEqual(MIN_MARK_RADIUS)
    }
  })

  it('tolerates a missing site list', () => {
    expect(buildTrackPoints(null, context())).toEqual([])
  })

  it('preserves gene-local site numbering in a transcript subset and its own read count', () => {
    const points = buildTrackPoints([site({ site_order: 3, samples: [{ key: 'brain', abundance: 0.4, site_count: 40 }] })], context({ sampleKey: 'brain' }))
    expect(points[0].order).toBe(3)
    expect(points[0].supportingReads).toBe(40)
    expect(points[0].usage).toBe(0.4)
  })
})

describe('formatters', () => {
  it('formats usage as a percentage', () => {
    expect(formatUsage(0.421)).toBe('42.1%')
    expect(formatUsage(0)).toBe('0.0%')
  })

  it('names the not-detected state', () => {
    expect(formatUsage(null)).toBe('Not called')
    expect(formatUsage(undefined)).toBe('Not called')
  })

  it('falls back for unusable usage', () => {
    expect(formatUsage('oops')).toBe('—')
  })

  it('formats counts with thousands separators', () => {
    expect(formatCount(1234)).toBe('1,234')
    expect(formatCount('oops')).toBe('—')
  })

  it('humanises biotypes', () => {
    expect(formatBiotype('protein_coding')).toBe('protein coding')
    expect(formatBiotype(null)).toBe('transcript')
  })
})
