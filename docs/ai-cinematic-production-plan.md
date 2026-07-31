# AI cinematic production plan

Status: creative direction locked; the still-image pacing proxy was rejected as
non-seamless and will not be integrated.

## Locked creative contract

- One uninterrupted impossible camera move.
- Bidirectional scroll control: stopping scroll pauses the exact frame; upward
  scrolling reverses the same film.
- Real source photographs anchor Hong Kong, Memorial Church, and the Main Quad.
- The final runtime uses one master video. Generation begins from the Hong Kong
  reference frame and then uses cumulative video extensions, so later stages
  inherit the complete prior film rather than starting as independent clips.
- No visible architectural morph, location crossfade, portal, whip pan, white
  flash, or browser-rendered 3D.
- The two geographic handoffs are motivated occlusions: moving golden-hour
  clouds and a dark Stanford arch.

## Timing map

| Time | Beat | Camera and environment | Copy |
| ---: | --- | --- | --- |
| 0.0–3.5 s | Hong Kong A | Establish the full Braemar Hill panorama with a slow rightward drift | `Eric Wu` and role line |
| 3.5–6.3 s | Hong Kong B | Accelerate into a much tighter Central skyline view: Two IFC and Bank of China Tower grow roughly 2.5–3× in frame before the crane rise | Sequential interests |
| 5.4–9.5 s | Atmospheric bridge | Skyline exits below; cloud field reaches full coverage; Stanford sky replaces it underneath | None |
| 9.2–12.2 s | Stanford A | Descend and tilt onto Memorial Church | `Stanford` / `Class of 2029` |
| 12.2–15.4 s | Architectural bridge | Push into a dark church arch; switch underlying location only at full darkness | None |
| 15.4–18.0 s | Stanford B | Emerge beneath the Main Quad arcade and continue the glide | Social links |

## Generation jobs

The final film should not be requested as unrelated shots. Use the OpenAI
Videos API to create an initial 8-second Hong Kong clip, then extend that exact
completed video by 8 seconds and 4 seconds. The extension endpoint uses the
full source video as context to preserve camera direction and scene continuity.
The returned cumulative 20-second master is retimed to 18 seconds without any
visual transition effect.

### Job 1 — Hong Kong into cloud cover (8-second creation)

Input anchors: Hong Kong opening and Hong Kong crane.

Prompt:

> Photorealistic late-golden-hour view from Braemar Hill overlooking Hong Kong.
> One continuous stabilized cinema-camera move. Begin on the full Braemar Hill
> panorama with a slow rightward drift, then accelerate decisively forward
> across Victoria Harbour toward Central. This is a major change of scale, not
> a gentle Ken Burns zoom: transition from a wide establishing view to a tight
> telephoto-feeling composition where Two IFC and Bank of China Tower become
> roughly 2.5 to 3 times larger in frame. Preserve real depth and parallax as
> foreground foliage clears and the harbour expands beneath the camera. After
> the close skyline beat, continue the same velocity into a pronounced crane
> rise and pitch upward; the landmark towers travel downward and leave the
> frame naturally as the camera enters moving volumetric cloud cover.
> Preserve the real skyline and building identities until they leave frame.
> Natural exposure, realistic motion blur, coherent evolving lens perspective,
> no flat image scaling, no morphing,
> no invented buildings, no text, no people, no cut, no flash.

### Job 2 — Clouds into Memorial Church and darkness (8-second extension)

Input anchors: full cloud cover and Memorial Church reveal.

Prompt:

> Continue the exact same stabilized camera motion through dense moving
> late-golden-hour clouds. Keep cloud optical flow, sun direction, exposure,
> lens, camera roll, and velocity continuous. As the camera descends and pitches
> down, the real Stanford Memorial Church and Main Quad rise from below the
> frame. Land in a broad slightly off-axis Memorial Church composition. Do not
> morph clouds into architecture; architecture becomes visible only as the
> clouds thin. Photorealistic stone and mosaic detail, no people, no text, no
> cut, no exposure flash.

### Job 3 — Darkness into the arcade (4-second extension)

Input anchors: Memorial Church reveal, dark arch, and Main Quad arcade.

Prompt:

> Continue one physical camera path from the Memorial Church approach toward a
> dark sandstone arch. The camera moves forward into architectural darkness;
> motion and lens remain continuous while the frame is fully dark. It emerges
> naturally beneath the Stanford Main Quad arcade and continues a shallow
> rightward glide with strong nearby-column parallax. Preserve the real
> Romanesque architecture and sandstone texture. No morphing façade, no
> dissolve, no flash, no people, no text, no cut visible to the viewer.

## Review gates

1. Produce and approve the 8-second true-video Hong Kong scale-change test
   before executing either extension.
2. Generate low-cost `sora-2` motion candidates; use `sora-2-pro` only after
   the path and landmark behavior pass review.
3. Reject any candidate with landmark drift, camera reset, exposure reset,
   static cloud texture, or unstable reverse scrubbing.
4. Stitch the approved candidates into a single 18-second 1080p master.
5. Encode a frequent-keyframe MP4/WebM pair and replace the current Three.js
   environment only after the film passes normal, fast, and reverse scrolling.

## Current capability boundary

The production runner is implemented at
`scripts/generate_sora_cinematic.py`. Its local dry run prepares the exact
1280x720 Hong Kong reference and generation manifest without making a billable
request. The configured TrueFoundry profile exposes 220 models but no video
model, so execution requires a direct OpenAI Platform key with Videos API
access. The rejected still-image proxy will not be integrated.

Official implementation references:

- https://developers.openai.com/api/docs/guides/video-generation
- https://developers.openai.com/api/reference/resources/videos/methods/extend
