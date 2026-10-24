# Resolved coin sprite recording — October 24, 2026

This build adds debug recording, not coin animation blending. It preserves the
original 28 ms simulation and existing draws. The optional smoke experiment
remains off by default. Stable M1.2 is unchanged.

## Capture

1. Extract the test ZIP beside your own original game asset folders.
2. Run **Start M2 Debug.cmd**. Play for about 60 seconds with silver/gold coins.
   Collect some, let others disappear, and pause/resume while coins are present.
3. Save and load a game with coins present when that mode permits it.
4. Close the game normally. Preserve **all M2Debug*.csv**, **M2Timing.log** and
   **BUILD_INFO.json** in a separate folder before starting another debug run.
5. Make a separate short recording in Virtual Tank or a bonus round to cover
   silver/gold shell drawings. Record which mode and actions were tested.
6. Run **Analyze M2 Logs.cmd** (Python 3 required). Include the report with the
   logs. A short video is still needed to judge appearance.

Logs are overwritten on the next debug launch. A normal launcher does not emit
this trace. Existing logs in that folder may belong to an earlier run.

## Coverage and identity

M2DebugCoinSprites.csv records the resolved DrawImageCel request in the silver
and gold branches: COIN_SILVER_C, COIN_GOLD_C, SHELL_SILVER and SHELL_GOLD.
It captures both ordinary money and shell mode, including paused, collected
and fading states. Other coin families and all fish bodies are untracked here.

Each coin receives a monotonically increasing, session-local lifetime ID at
construction and on reading a save. Saving does not change it. The field is
never serialized; IDs cannot be compared across sessions. Zero means unknown.
No gameplay callback, RNG, counter or movement is invoked by the recorder.

Resource names identify the selected IMAGE_MONEY or IMAGE_SHELLS branch;
imageId is only the current pointer. resourceGeneration is always zero, meaning
**untracked**. Same-address resource replacement or in-place pixel changes are
not detectable. This trace does not establish blending eligibility.

## Geometry and state

The file includes requested cel/row, full sheet dimensions and grid counts.
The pinned renderer obtains cel dimensions using integer width/columns and
height/rows, then offsets the source rectangle by cel and row.

drawX/drawY are local draw arguments. Translation, scale, scale origin and clip
are copied from the graphics context after M2 position interpolation. These
describe the request before rasterization, not measured screen coordinates.
The pinned renderer truncates translated integer positions before scaling and
clipping. No visibility or physical presentation claim follows from a row.

Mirror is zero for these calls. RGBA is the effective image tint (white when
colorization is off); colorized and drawMode are recorded separately. Pause,
collection and disappearance state come from the owner at that drawing site.
The recorder reads these fields and does not change the graphics state.

## Limits and validation

The stream has independent limits of 64 requests per presentation frame and
350,000 rows per session, without progressive sampling. The first exceeded
frame budget and the first exceeded file budget emit INFO events. They do not
count every dropped row. A full row budget or absent rows is incomplete evidence.
Frame/gameTick numbering follows the existing debug recorder, including its
scheduler tick convention during pause; it is not an owner update counter.

The analyzer validates schema, numeric fields, tracked type/row/sheet mapping,
cel bounds and order, and reports money/shell, pause, collection and fade coverage.
It does not join shared image pointers to other streams or infer verified wraps,
resource continuity, smoothness or safe crossfades. An absent/empty new file is
reported explicitly when analyzing older recordings.

Local verification: 70 Python tests and nine native C++ programs passed. The
coin descriptor test covers disabled operation, fresh identities at the same
address, effective tint, transforms and independent per-frame limits. The patch
was applied to the pinned generated Coin source; its complete Update function,
graphics calls and serialized fields were compared with the prior source.
Full Windows build evidence is recorded separately when CI finishes.

New gameplay recordings and visual acceptance remain outstanding. Compilation
and synthetic recorder tests do not verify appearance, audio or display pacing.
