"""Coverage and bounded owner-lifetime transitions; never infer blend eligibility."""
import collections
import csv
import math

FIELDS = ('frame,gameTick,objectId,lifetimeId,coinType,shellMode,imageId,resource,'
          'resourceGeneration,celColumn,celRow,imageWidth,imageHeight,sheetCols,sheetRows,'
          'drawX,drawY,translationX,translationY,scaleX,scaleY,scaleOriginX,scaleOriginY,'
          'clipX,clipY,clipWidth,clipHeight,mirror,colorized,red,green,blue,alpha,drawMode,'
          'paused,collected,disappearTimer').split(',')
FLOATS = set('translationX translationY scaleX scaleY scaleOriginX scaleOriginY'.split())
TEXT = {'objectId', 'imageId', 'resource'}

class CoinTransitions:
    """Compare unique requests in adjacent frames with at most 128 stored rows.

    Lifetime IDs identify owners only. Even an identical nonzero resource
    generation is not assigned continuity semantics by this analyzer.
    """
    FRAME_LIMIT = 64
    STATE_GROUPS = {
        'sheet': ('coinType', 'shellMode', 'imageId', 'resource', 'resourceGeneration',
                  'celRow', 'imageWidth', 'imageHeight', 'sheetCols', 'sheetRows'),
        'position': ('drawX', 'drawY', 'translationX', 'translationY'),
        'transform': ('scaleX', 'scaleY', 'scaleOriginX', 'scaleOriginY', 'mirror'),
        'clip': ('clipX', 'clipY', 'clipWidth', 'clipHeight'),
        'appearance': ('colorized', 'red', 'green', 'blue', 'alpha', 'drawMode'),
        'owner_state': ('paused', 'collected', 'disappearTimer'),
    }

    def __init__(self):
        self.counts = collections.Counter()
        self.previous = {}
        self.rows = []
        self.frame = None
        self.tainted = False
        self.skip_next_frame = False

    def invalidate(self):
        # An unparseable row may belong to either side of a frame boundary.
        # Discard the pending frame and the next observed frame, conservatively.
        self.counts['barriers'] += 1
        self.previous.clear()
        self.rows.clear()
        self.frame = None
        self.skip_next_frame = True

    def observe(self, row):
        if row['frame'] != self.frame:
            self._flush()
            self.frame = row['frame']
            self.tainted = self.skip_next_frame
            self.skip_next_frame = False
        if self.tainted:
            return
        if self.rows and row['gameTick'] != self.rows[0]['gameTick']:
            self.counts['inconsistent_frames'] += 1
            self.rows.clear()
            self.tainted = True
            return
        if len(self.rows) == self.FRAME_LIMIT:
            self.counts['oversized_frames'] += 1
            self.rows.clear()
            self.tainted = True
            return
        self.rows.append(row)

    def _flush(self):
        if self.frame is None:
            return
        if self.tainted:
            self.previous.clear()
            self.rows.clear()
            self.frame = None
            return
        lifetimes = collections.Counter(r['lifetimeId'] for r in self.rows)
        owners = collections.Counter(r['objectId'] for r in self.rows)
        current = {}
        for row in self.rows:
            identity = row['lifetimeId']
            if lifetimes[identity] != 1 or owners[row['objectId']] != 1:
                self.counts['ambiguous_requests'] += 1
                continue
            current[identity] = row
            old = self.previous.get(identity)
            if old is None:
                self.counts['unpaired_requests'] += 1
                continue
            if old['objectId'] != row['objectId']:
                self.counts['owner_mismatches'] += 1
                continue
            if row['frame'] - old['frame'] != 1:
                self.counts['frame_gaps'] += 1
                continue
            ticks = row['gameTick'] - old['gameTick']
            if ticks not in (0, 1):
                self.counts['tick_gaps'] += 1
                continue
            self.counts['pairs'] += 1
            self.counts['same_tick' if ticks == 0 else 'next_tick'] += 1
            if not old['resourceGeneration'] or not row['resourceGeneration']:
                self.counts['unknown_generation_pairs'] += 1
            changed = {name for name, keys in self.STATE_GROUPS.items()
                       if any(old[k] != row[k] for k in keys)}
            for name in changed:
                self.counts[name + '_changes'] += 1
            if 'sheet' in changed:
                continue
            delta = row['celColumn'] - old['celColumn']
            label = 'same' if delta == 0 else 'plus_one' if delta == 1 else 'other'
            self.counts[f'cel_{ticks}_{label}'] += 1
        self.previous = current
        self.rows.clear()
        self.frame = None

    def finish(self):
        self._flush()
        c = self.counts
        lines = [
            'Coin request transitions (adjacent presentation frames, same owner lifetime):',
            f"- {c['pairs']:,} pairs: {c['same_tick']:,} within the same scheduler tick; {c['next_tick']:,} across one scheduler tick.",
            f"- Numeric cel changes with matching sheet descriptors, same tick: unchanged {c['cel_0_same']:,}, +1 {c['cel_0_plus_one']:,}, other {c['cel_0_other']:,}; next tick: unchanged {c['cel_1_same']:,}, +1 {c['cel_1_plus_one']:,}, other {c['cel_1_other']:,}.",
            '- Changed state (categories overlap): ' + ', '.join(
                f"{name.replace('_', ' ')} {c[name + '_changes']:,}"
                for name in self.STATE_GROUPS) + '.',
            f"- Skipped comparisons: frame gaps {c['frame_gaps']:,}, scheduler tick gaps {c['tick_gaps']:,}, owner mismatches {c['owner_mismatches']:,}; ambiguous requests {c['ambiguous_requests']:,}, oversized frames {c['oversized_frames']:,}, inconsistent frame ticks {c['inconsistent_frames']:,}, invalid/order barriers {c['barriers']:,}. Unpaired requests {c['unpaired_requests']:,}.",
            f"- {c['unknown_generation_pairs']:,} pairs include unknown image generation. Resource continuity is unverified for every pair, including matching nonzero generation values.",
            '- Numeric changes are observations, not verified animation advances or wraps. Scheduler ticks are not owner updates; pause and other state changes remain separate observations. No pair is certified safe for blending.',
        ]
        notes = []
        if c['ambiguous_requests']:
            notes.append('WARN: Repeated coin lifetimes or owner addresses within a frame make pairing ambiguous; those requests were excluded, without assuming the draws were invalid.')
        if any(c[k] for k in ('owner_mismatches', 'oversized_frames', 'inconsistent_frames')):
            notes.append('ERROR: Coin transition trace has changed owner addresses, inconsistent frame ticks or frames exceeding the recorder limit; affected comparisons were excluded.')
        return lines, notes

def audit_coin_sprites(folder):
    path = folder / 'M2DebugCoinSprites.csv'
    if not path.exists():
        return [], ['INFO: Resolved coin sprite trace absent; older captures cannot establish sprite state.']
    counts = collections.Counter()
    transitions = CoinTransitions()
    last = None
    try:
        with path.open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream, strict=True)
            if reader.fieldnames != FIELDS:
                return [], ['ERROR: Resolved coin sprite trace has an unsupported header.']
            for raw in reader:
                counts['rows'] += 1
                try:
                    if None in raw or any(v is None or v == '' for v in raw.values()):
                        raise ValueError('partial row')
                    r = {k: (v if k in TEXT else float(v) if k in FLOATS else int(v))
                         for k, v in raw.items()}
                    if not all(math.isfinite(r[k]) for k in FLOATS):
                        raise ValueError('nonfinite transform')
                    for k in ('frame', 'gameTick', 'resourceGeneration', 'disappearTimer'):
                        if r[k] < 0: raise ValueError(k)
                    if r['lifetimeId'] <= 0: raise ValueError('unknown owner lifetime')
                    for k in ('shellMode', 'mirror', 'colorized', 'paused', 'collected'):
                        if r[k] not in (0, 1): raise ValueError(k)
                    for k in ('red', 'green', 'blue', 'alpha'):
                        if not 0 <= r[k] <= 255: raise ValueError(k)
                    if r['coinType'] not in (1, 2, 8, 9): raise ValueError('untracked type')
                    if r['celRow'] != (0 if r['coinType'] in (1, 8) else 1):
                        raise ValueError('wrong family row')
                    if r['resource'] != ('IMAGE_SHELLS' if r['shellMode'] else 'IMAGE_MONEY'):
                        raise ValueError('wrong sheet')
                    if r['mirror'] != 0: raise ValueError('unsupported mirror')
                    for k in ('sheetCols', 'sheetRows', 'imageWidth', 'imageHeight'):
                        if r[k] <= 0: raise ValueError(k)
                    if not (0 <= r['celColumn'] < r['sheetCols'] and
                            0 <= r['celRow'] < r['sheetRows']):
                        raise ValueError('out of sheet')
                    if (r['imageWidth'] // r['sheetCols'] <= 0 or
                            r['imageHeight'] // r['sheetRows'] <= 0):
                        raise ValueError('empty cel')
                except (ValueError, TypeError, OverflowError):
                    counts['invalid'] += 1
                    transitions.invalidate()
                    last = None
                    continue
                now = r['frame'], r['gameTick']
                if last and (now[0] < last[0] or now[1] < last[1]):
                    counts['regressions'] += 1
                    transitions.invalidate()
                last = now
                transitions.observe(r)
                counts['valid'] += 1
                counts[r['resource']] += 1
                counts['paused'] += r['paused']
                counts['collected'] += r['collected']
                counts['fading'] += r['disappearTimer'] != 0
                counts['unknown_generation'] += r['resourceGeneration'] == 0
                counts['nonstandard_draw'] += r['drawMode'] != 0 or r['colorized'] != 0
    except (OSError, UnicodeError, csv.Error) as exc:
        return [], [f'ERROR: Unable to read complete coin sprite trace: {exc}']
    report = ['Resolved silver/gold coin draw requests (no animation smoothing):',
              f"- {counts['rows']:,} rows; {counts['valid']:,} valid; {counts['invalid']:,} invalid; {counts['regressions']:,} ordering regressions.",
              f"- Money/shell requests: {counts['IMAGE_MONEY']:,}/{counts['IMAGE_SHELLS']:,}; paused {counts['paused']:,}, collected {counts['collected']:,}, fading {counts['fading']:,}, colorized/non-normal draw {counts['nonstandard_draw']:,}.",
              f"- {counts['unknown_generation']:,} requests have unknown image generation. Image pointers do not establish resource continuity.",
              '- Other coin families are untracked. Up to 64 rows/frame and 350,000 rows/file; budget events indicate omissions.',
              '- Geometry describes the local request, transform and clip before rasterization; it does not prove visible pixels or blending safety.']
    notes = []
    if not counts['rows']:
        notes.append('INFO: Coin sprite file is empty; no silver/gold coverage established.')
    if counts['invalid'] or counts['regressions']:
        notes.append('ERROR: Coin sprite trace has invalid requests or ordering; inspect the CSV.')
    if counts['rows'] >= 350000:
        notes.append('INFO: Coin sprite file reached its row budget; later requests may be omitted.')
    transition_report, transition_notes = transitions.finish()
    report.extend(transition_report)
    notes.extend(transition_notes)
    return report, notes
