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
full pixel continuity is **untracked**. The v2 stamps below separately identify
image lifetimes and explicit pixel-change notifications. This trace does not
establish blending eligibility.

## Image stamps (v2) - October 25, 2026

The CSV appends imageLifetimeId and reportedPixelRevision, for 39 columns.
The analyzer still accepts the original 37-column v1 format and explicitly
reports its missing stamps as unknown. IDs cannot be compared across processes.

imageLifetimeId is fresh on construction, copying, moving and non-self
assignment. Reconstructing an image at the same address produces a different
ID. Assignment creates a new observation identity even if the allocation stays
in place; self-assignment preserves it. The base Image member also covers
MemoryImage and SDLImage, including their explicit copy constructors. The global
allocator is thread-safe; per-image mutation follows existing ownership rules.
If the 64-bit ID space is exhausted, subsequent IDs remain zero (unknown).

reportedPixelRevision starts at one and increments only when the existing
MemoryImage::BitsChanged method is called. Overflow permanently produces zero
(unknown) for that identity. Raw writes through public mBits/GetBits can bypass
this notification. Matching stamps do not certify unchanged pixels, texture
residency, renderer state, purge/recovery behavior or safe blending.

The hook adds no missing BitsChanged calls, reads no pixels, performs no texture
recovery and leaves original pixel operations and the old signed counter intact.
For example, pinned BonusScreen.cpp writes shell-image alpha pixels directly
without a following notification. This demonstrates a framework limitation;
it is not evidence that the recorded coin sheet changed during a capture.

Changed image IDs or reported revisions exclude numeric cel comparisons. A
known ID with a changed address or decreasing nonzero revision is an error and
that pair is excluded. Unknown stamps remain explicitly observational.

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
Windows CI 40097480779 passed for commit
d85c37fdb9fea0b7d90b0e327a71bc5d39a7e255, including the same tests and full
game build. The published m2-coin-sprite-trace-20261024 ZIP was downloaded and
checked for source/run/tag metadata, CRCs, x64 executable, launcher settings
and bundled analyzer content. Its SHA256 is
0a90d99673e5ab5f2b19ce65e65898fbb82bd62c19702aa655890125b92198f6.

## Transition analyzer update - October 25, 2026

The updated Python analyzer also compares requests for the same lifetime ID
and owner address in consecutive presentation frames. It keeps at most two
frames of 64 requests each. An owner absent from the preceding frame starts a
new observation segment; it is never joined across that absence. Frame gaps
and scheduler tick differences other than zero or one are excluded and counted.

Same-frame duplicate lifetime IDs or owner addresses exclude every affected
request, including an earlier request in that frame. A changed owner address
for one lifetime is excluded and reported as an error. Frames exceeding the
recorder's 64-row limit or containing inconsistent scheduler ticks are discarded
and reported as errors. Malformed rows discard pending history and quarantine
the next observed frame, because their frame cannot be trusted. An ordering
regression discards pending history and quarantines the regressed frame.
These conservative barriers can undercount otherwise usable observations.

For retained pairs, the report separately counts changes in sheet descriptors,
position, transform, clip, appearance and owner state; categories can overlap.
Only matching sheet descriptors and recorded image stamps receive a numeric
cel-column classification (unknown stamps are allowed):
unchanged, +1, or other, separated by same/next scheduler tick. Sheet descriptors
include coin family, shell mode, resource name/pointer/generation, row and grid.
A numeric +1 is not a verified animation advance, and a decrease is not a
verified wrap. Paused/collected/fading pairs are observations, not blend targets.

Resource continuity remains unverified for **every** pair. Generation zero is
counted explicitly, and matching nonzero values are also not certified:
the v2 lifetime and notification contract does not cover every pixel mutation.
No pairing enables smoothing.

The earlier standalone transition analyzer contains only Python tools, a
launcher and this guide. The new m2-image-lifetime-20261025 game package records
v2 stamps and bundles the transition analyzer. Preserve original capture files.
Missing coin traces in older recordings remain explicit rather than becoming
zero-motion evidence.

For the image-stamp increment, 94 Python tests and ten native C++ programs
passed locally and in Windows CI, including same-address reconstruction, copies,
assignment, concurrent ID allocation, exhaustion and v1/v2 parsing. CI run
40107229558 compiled the full game at commit
44be31993d81bf9a3f0d8220c566a3c5b01aa083. The downloaded release passed CRC,
inventory, x64 executable, metadata, updater tag and launcher-setting checks.
Its bundled analyzer launcher passed historical, v1/v2 and synthetic image-change
fixtures from another working directory with spaces in the package path.
Original capture hashes remained unchanged. Release ZIP SHA256:
9857f69731a774a297e852cc0e7b10af001e264f16a9f2895dc57df9282d81cb.

New gameplay recordings and visual acceptance remain outstanding. Compilation
and synthetic recorder tests do not verify appearance, audio or display pacing.
