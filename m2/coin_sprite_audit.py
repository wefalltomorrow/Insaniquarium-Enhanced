"""Coverage of resolved silver/gold draw requests; never infer blend eligibility."""
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

def audit_coin_sprites(folder):
    path = folder / 'M2DebugCoinSprites.csv'
    if not path.exists():
        return [], ['INFO: Resolved coin sprite trace absent; older captures cannot establish sprite state.']
    counts = collections.Counter()
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
                    last = None
                    continue
                now = r['frame'], r['gameTick']
                if last and (now[0] < last[0] or now[1] < last[1]):
                    counts['regressions'] += 1
                last = now
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
    return report, notes
