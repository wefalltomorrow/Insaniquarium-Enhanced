"""Count attempted coin composition outcomes; not a visual-acceptance audit."""
import csv
import math
from collections import Counter

HEADER = 'frame,gameTick,objectId,lifetimeId,timer,simulationCel,fromCel,toCel,mix,result'.split(',')
RESULTS = {'state','disabled','graphics','history','sequence','held','layout','nonresident',
           'identity','pixels','endpoint','composed','allocation'}


def audit_coin_blend(folder):
    path = folder / 'M2DebugCoinBlend.csv'
    if not path.is_file():
        return [], ['INFO: Coin blend results absent (older recording or unavailable stream).']
    counts = Counter()
    invalid = 0
    previous = (-1,-1)
    frame_rows = 0
    try:
        with path.open(encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            if reader.fieldnames != HEADER:
                return [], ['ERROR: Coin blend CSV header is not supported.']
            for row in reader:
                try:
                    if None in row or any(v is None for v in row.values()): raise ValueError()
                    frame,tick,identity,timer,cel,old,new = (int(row[k]) for k in
                        ('frame','gameTick','lifetimeId','timer','simulationCel','fromCel','toCel'))
                    mix = float(row['mix']); reason = row['result']
                    if (min(frame,tick) < 0 or not 0 < identity < 2**64 or
                        not row['objectId'].strip() or not 0 <= timer < 80 or
                        not math.isfinite(mix) or not 0 <= mix <= 1 or reason not in RESULTS or
                        frame < previous[0] or tick < previous[1] or
                        (frame == previous[0] and tick != previous[1])): raise ValueError()
                    frame_rows = frame_rows+1 if frame==previous[0] else 1
                    previous = frame,tick
                    if frame_rows > 64: raise ValueError()
                    if reason in {'composed','endpoint'}:
                        if not (0 <= old < new < 10 and new == old+1 and new == cel): raise ValueError()
                        if reason=='composed' and not 0 < mix < 1: raise ValueError()
                        if reason=='endpoint' and mix not in (0,1): raise ValueError()
                    elif old != cel or new != cel or mix != 1: raise ValueError()
                    counts[reason] += 1
                except (ValueError,TypeError,OverflowError): invalid += 1
    except (OSError,UnicodeError,csv.Error) as exc:
        return [], [f'ERROR: Cannot read coin blend results: {exc}']
    notes = [f'ERROR: {invalid} invalid coin blend result rows.'] if invalid else []
    if not counts['composed']:
        notes.append('INFO: No composed coin draws recorded; smoothing is unverified in this capture.')
    details = ['Coin composition outcomes (bounded per-frame samples):',
               ', '.join(f'{key}={value:,}' for key,value in sorted(counts.items())) or 'No samples.',
               'Composed means a CPU blend was submitted for drawing; appearance, GPU pixels and display pacing remain unverified.']
    return details,notes
