# Atmospheric Bridge Specification

Status: proxy motion approved; ready for transfer to reconstructed assets.

## Intent

Connect Braemar Hill and Stanford Memorial Church as one visually continuous
camera journey without morphing architecture, sliding photographs, hiding a
plate swap behind a flat object, or using an exposure flash.

The transition is intentionally atmospheric rather than literally geographic.
The sky, haze, light, lens, and camera motion remain continuous while the
source-grounded location geometry changes only when no landmark pixels are
visible.

## Choreography

The bridge occupies its own scroll interval between the completed Hong Kong
interests and the Stanford identity reveal.

1. **Leave Hong Kong:** the telephoto skyline remains readable while the camera
   continues its established rightward glide. The completed interests have
   already been removed and no new copy appears.
2. **Rise into atmosphere:** the camera makes a pronounced vertical crane rise
   while pitching upward. Hong Kong architecture and foreground foliage travel
   downward at different parallax rates until they physically exit below the
   viewport. They do not dissolve. No object moves like a screen wipe.
3. **Shared atmospheric center:** the persistent sky dome and volumetric field
   occupy the frame. The sun stays in the same screen direction, cloud noise
   continues advancing, exposure does not reset, and camera velocity remains
   continuous. The location geometry handoff happens only here.
4. **Enter Stanford:** the camera descends and gradually pitches down while
   maintaining its rightward travel. Memorial Church and Stanford oak canopy
   rise naturally from below the viewport, with stronger near-field canopy
   parallax than the distant architecture.
5. **Land on Stanford A:** Memorial Church resolves slightly right of center in
   the selected Wide / Gliding composition. The environment receives a brief
   copy-free hold before `Stanford` and `Class of 2029` are revealed.

The center of the bridge should be brief enough that the visitor does not feel
parked inside a cloud, but long enough to prevent the location change from
reading as a flash or disguised cut. Exact duration belongs to the geometry
animatic rather than this document.

## Render architecture

- Use one continuous master camera motion curve across the complete bridge.
  Position, rotation, velocity, and acceleration must remain continuous.
- Keep the lens fixed through the center of the bridge. If the Hong Kong
  telephoto move needs to relax before Stanford, perform that change gradually
  before landmark visibility reaches zero.
- Render one persistent sky dome and volumetric atmosphere for the entire
  bridge. Lock the sun vector, cloud layout, volumetric-noise seed and phase,
  wind direction, exposure, white balance, shutter, and motion blur.
- Keep Hong Kong and Stanford as separate source-grounded geometry collections.
  Their visibility handoff is allowed only after a depth or object-ID test
  confirms that haze and sky contain no identifiable architecture.
- Do not animate either environment's opacity. Keep each collection fully
  opaque and switch collections only at the sky-filled apex, after the outgoing
  collection is below frame and before the incoming collection enters it.
- Carry at least one persistent optical-flow cue through the center, such as a
  cloud edge, fine volumetric particulate, or a subtle high-altitude foliage
  silhouette. It must belong to the atmospheric layer rather than either city.
- Render the beauty, depth, object-ID, atmosphere, and foreground-alpha passes
  from synchronized frame ranges. The web timeline must scrub all passes from
  one normalized progress value.
- Keep semantic HTML copy absent throughout the bridge. Typography resumes only
  after Stanford A has visually established itself.

## Prohibited shortcuts

- No crossfade between Hong Kong and Stanford beauty plates.
- No full-screen building, column, or rectangle used to hide a hard cut.
- No whip pan, radial blur, white flash, or abrupt exposure bloom.
- No morphing Hong Kong towers into Stanford arches, trees, or church geometry.
- No generated landmark pixels or invented architecture.
- No independent camera curves that merely end and restart at matching speeds.
- No static cloud image that remains fixed while the environments change.

## Acceptance tests

The atmospheric bridge passes only when all of the following are true:

- With all typography removed, the sequence still feels like one uninterrupted
  movement rather than two clips joined by an effect.
- Frame stepping reveals no jump in sky detail, cloud phase, sun position,
  exposure, lens distortion, camera roll, or motion blur.
- Hong Kong landmark pixels reach zero before Stanford landmark pixels appear.
- Hong Kong exits through the lower frame boundary and Stanford later enters
  through that boundary; neither environment becomes transparent on-screen.
- Optical flow continues in the same direction through the bridge center.
- Fast scrubbing and reverse scrolling do not expose a pop or a one-frame plate
  overlap.
- The camera descends into a physically plausible Stanford position and can
  continue uninterrupted from Stanford A into the long arcade route.
- The mobile render uses its own vertical-safe camera path while preserving the
  same atmospheric logic.
- Reduced motion skips the atmospheric travel and presents static source-grounded
  identity frames without autoplayed movement.

## Approved proof

The first neutral proxy proof has been rendered:

- [Motion proof](../output/proofs/atmospheric-bridge/atmospheric_bridge_proxy_proof.mp4)
- [Diagnostic keyframes](../output/proofs/atmospheric-bridge/atmospheric_bridge_keyframes.jpg)
- [Continuity report](../output/proofs/atmospheric-bridge/report.md)

It uses neutral source-shaped massing because the complete official geometry
caches are not present on the local Mac. Automated checks confirm zero landmark
overlap, a 21-frame shared-atmosphere center, 11 proxy units of vertical camera
lift, continuous pan velocity, bounded pitch and sun displacement, and
consistent sky optical-flow direction. Eric approved the vertical motion on
July 18, 2026. This authorizes transfer of the same crane, pitch, pan, forward
travel, sky, and atmosphere contract to the authoritative Hong Kong and
Stanford reconstruction assets.
