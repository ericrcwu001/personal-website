# Homepage Intro Plan

Status: Working creative plan. Capture-free asset research is complete; no final source asset has been purchased and no production dataset has been downloaded yet.

Selected production direction: reconstruct the real Hong Kong and Stanford locations in 3D, choreograph the camera virtually, and render the sequence offline. The result should be as photorealistic as possible. It does not need to consist solely of unaltered camera footage.

Selected setting: late golden hour across both Braemar Hill Lookout and Stanford Memorial Church. The lighting should feel continuous across the transition, with warm directional light, preserved skyline detail, and no exaggerated orange grading.

## Design read

An identity-first AI systems portfolio for technical recruiters, collaborators, and research peers, with a cinematic documentary visual language. It should feel authored and technically precise, not like a themed developer template.

- `DESIGN_VARIANCE: 8` - asymmetric, place-led composition with carefully controlled copy placement
- `MOTION_INTENSITY: 8` - a scroll-scrubbed camera journey is the central interaction
- `VISUAL_DENSITY: 4` - enough information to establish Eric clearly, with room for the environment to carry emotion

## What the intro must accomplish

Within the first viewport, a visitor should understand:

- This is Eric Wu.
- He is `Stanford '29, AI Engineer & Researcher`.
- He builds AI systems across the full path from data and model behavior to evaluation and product.
- Hong Kong and Stanford are important parts of who he is.

The personal history is communicated through place and movement. The copy does not narrate a chronological autobiography.

## Core concept

**Two places, one continuous line of motion.**

The visitor begins inside a photorealistic Hong Kong environment. Vertical scrolling advances a deliberate rightward camera move. After the Hong Kong identity beats, the camera makes a pronounced crane rise and pitches into late-golden-hour haze and sky. The skyline and foreground foliage travel downward at different parallax rates until they physically leave the viewport. The same sun, clouds, exposure, lens, camera velocity, and volumetric motion persist through a brief sky-filled apex. The camera then descends as Stanford canopy and Memorial Church rise naturally from below.

This is not an architectural morph, image wipe, or object-hidden match cut. The Hong Kong and Stanford geometry changes only while the shared atmosphere contains no identifiable landmark pixels. The persistent sky and haze make the camera journey feel visually uninterrupted without pretending that the locations are physically adjacent.

The movement provides the subtext: Eric's background and present context inform the way he works, but the page speaks directly about who he is now.

## Proposed scroll sequence

The entire intro is one pinned visual sequence, provisionally 350-450vh on desktop. The exact duration should be set by the animatic, not by an arbitrary scroll length.

Braemar Hill and Memorial Church receive equal active scroll time. The shared atmospheric bridge between them is treated separately so neither location feels like a brief prelude to the other.

Each location contains exactly two full-screen identity compositions, but they are not separate shots. Hong Kong A and B are two readable moments along one uninterrupted Hong Kong camera path. Stanford A and B are two readable moments along one uninterrupted Stanford camera path. The environment continues moving between them with real 3D parallax; no image wipe, plate replacement, hidden internal cut, or forced photo-to-photo transition is allowed within either location.

| Location | View | Provisional purpose | Exact composition |
| --- | --- | --- | --- |
| Braemar Hill Lookout | Hong Kong A | Wide skyline establishing view | Phase 2 candidate A2: balanced approximately 70 mm composition with foreground at the lower edge and space for the opening title |
| Braemar Hill Lookout | Hong Kong B | Scroll-controlled telephoto push toward the Central skyline | Phase 2 candidate B2: approximately 155 mm compression on Bank of China Tower and Two IFC, with central negative space for the interests treatment |
| Memorial Church | Stanford A | Wide establishing approach | Selected Wide / Gliding composition: a broad, slightly off-axis Main Quad view with Memorial Church right of center and generous travel space as the Stanford canopy and haze clear |
| Memorial Church | Stanford B | Long arcade continuation for parallax and text masking | Selected Wide / Gliding composition: the longest credible oblique run beneath the Main Quad arcade, with the social links held late in the move and a new column catching the frame |

| Scroll beat | Environment and camera | Visible message | Purpose |
| --- | --- | --- | --- |
| Hong Kong A | The Braemar Hill skyline is established with subtle environmental motion. Camera is initially settled. | `Eric Wu` | Establishes identity immediately and simply. |
| Hong Kong B | After Hong Kong A is fully covered, a new object clears to reveal the interests treatment as the telephoto push moves toward the Bank of China Tower and Two IFC. The interests accumulate sequentially into a persistent list rather than arriving as one static block or replacing one another. | `Interested in:` followed sequentially by `AI Engineering & Research`, `Math`, `CS`, and `Public Policy` | Introduces the fields Eric is drawn to with a controlled internal rhythm rather than turning the intro into a résumé summary. |
| Atmospheric bridge | The Hong Kong camera continues right and tilts upward. Skyline geometry recedes into shared golden-hour haze until only the persistent sky and volumetric field remain. Stanford canopy enters with the same optical flow and the camera tilts down into the Main Quad. | No copy | Connects the two locations without a plate wipe, architectural morph, exposure flash, or motion reset. |
| Stanford A | Stanford foliage and haze clear to reveal the selected wide, slightly off-axis Memorial Church view. The camera continues the same apparent rightward glide rather than settling into a disconnected still. | `Stanford` above `Class of 2029` on two lines | States the present context after the location has already communicated it visually. |
| Stanford B | The camera physically continues from the Main Quad into the long arcade corridor. Church, ground plane, arcade, columns, lighting, and parallax remain continuously rendered. A real column can pass over the HTML copy, but it does not hide a background or camera swap. | Recognizable icons for `GitHub`, `LinkedIn`, `X`, `Instagram`, and `Email` | Gives the visitor direct ways to continue before the project chooser. |
| Work reveal | In the final Stanford arcade view, a sandstone column moves across and fills the viewport. The Work chooser is already rendered behind it. | The project chooser is revealed as the column clears. | Hands the visitor directly from identity into a non-linear choice of work without a crossfade or page jump. |

### Braemar Hill zoom treatment

Hong Kong A establishes the complete skyline from Braemar Hill Lookout. Hong Kong B then moves into a telephoto view of selected notable buildings.

- The effect is tied to scroll progress and feels like a controlled optical push rather than a CSS crop becoming larger.
- Hong Kong A and B must be one continuous camera move through the same reconstructed skyline. A foreground branch or railing may cover text, but it cannot conceal a background or camera swap.
- The telephoto view requires its own high-resolution licensed source coverage so windows, facade detail, haze, and lighting remain credible when enlarged.
- Do not rely on AI sharpening or stretching the wide panorama to manufacture missing building detail.
- The telephoto move lands on the Central skyline cluster, using the Bank of China Tower and Two IFC as visual anchors while retaining enough Victoria Harbour to preserve geographic context.
- After the completed interests hold, the camera continues right and tilts gently upward. Foreground foliage and natural atmospheric depth remove the skyline from view without a flat wipe. The shared sky and haze then carry the transition into Stanford.

Phase 2 camera decision: use `hk_a_02_balanced` as the Hong Kong A base and `hk_b_02_tele` as the Hong Kong B base. The heavily obstructed A1/B1 studies are not identity frames; retain their foreground coverage only as reference for the reveal and hidden-cut endpoints. The tighter A3/B3 pair remains an alternate crop, not the selected base.

Stanford camera decision: use the `Wide / Gliding` pair as the base. Stanford A is the broad Memorial Church reveal; Stanford B is the longest viable arcade run. The Balanced / Readable and Tight / Occlusion-led pairs remain composition references only. The final column-to-Work cover may borrow the stronger foreground coverage tested in the Tight study without changing the selected wide camera rhythm.

The strategic positioning remains an internal guide for project selection, descriptions, and detail pages. It is not displayed as explanatory copy in the cinematic intro:

> Eric builds AI systems end to end, from data and model behavior to evaluation and product. He applies them across difficult environments and designs the tests that determine whether they actually work.

## Initial viewport composition

- Full-bleed environment, never a 3D scene inside a card or browser frame.
- Copy uses masked screen text. It remains crisp and screen-aligned while reconstructed foreground objects move over it and hide it during scroll.
- Eric does not appear on camera in the intro. The environments and copy carry the identity moment.
- Each of the four full-screen views presents one identity facet: name, interests, Stanford, and social links.
- Every facet exits through full foreground-object occlusion and the next is revealed when a new object clears.
- One localized gradient or scrim protects text contrast without visibly tinting the whole environment.
- Navigation is minimal and stays on one line: Eric Wu, Work, About, Resume.
- No loading spectacle, intro gate, “enter” button, or scroll instruction.
- The first frame works as a complete static hero before the visitor moves.
- `Eric Wu` is treated as a large cinematic title that dominates Hong Kong A, not as a restrained signature or small editorial label.

## Typography direction

Spatial typography was rejected after visual comparison. Both the flat-in-depth and extruded versions made the words compete with Memorial Church and pushed the intro toward a movie-title aesthetic.

The selected direction is **masked screen text**:

- The text itself is flat semantic HTML positioned in screen space.
- It does not move in perspective, pretend to be a physical object, or attach to a landmark.
- Foreground objects from the reconstructed environment pass between the viewer and the typography as scrolling advances.
- Where an object overlaps the copy, the covered letters become genuinely hidden. This is object-shaped occlusion, not a rectangular wipe.
- Each message begins fully readable and receives a deliberate hold before an object starts covering it.
- A foreground object can completely cover the copy and become its transition out, avoiding an unnecessary opacity fade.
- Once fully covered during forward scrolling, the prior message is permanently retired and does not reappear when the object clears.
- Deliberately scrolling backward through the previous beat may reverse the timeline and restore it, but normal forward progression never does.
- Hong Kong A begins with `Eric Wu` visible immediately, without requiring the visitor to scroll first.
- Each view's copy is fully hidden by a real foreground object before that view ends.
- After a brief environment-only pause, a new object moves away to reveal the next view's identity text.
- The reveal follows the object's real silhouette. It is not a rectangular wipe and does not use an opacity fade.
- Within Hong Kong B, `Interested in:` appears first as a temporary prompt. A foreground silhouette then covers and permanently retires it as the first interest is revealed. Each interest appears on its own line and remains visible as the later lines accumulate beneath it. The completed list contains only the four interests and is retired as one group when the tower-edge transition covers the frame.
- `AI Engineering & Research`, `Math`, `CS`, and `Public Policy` receive equal visual weight: the same New York size, weight, color, and line treatment. Their order does not create a separate typographic tier.
- Text position can change between views to use the strongest available revealing object and negative space.
- Desktop and mobile may use different positions, line breaks, and occluding objects because the scene geometry and crop change.

### Opening-title type studies

Two controlled studies compare the large one-line `Eric Wu` title over the same temporary Braemar Hill composition. Size, placement, color, and background are held constant; only the type style changes. The generated skyline plate is a comparison aid, not an approved final environment asset.

- [Side-by-side comparison](../output/imagegen/typography-studies/00-serif-vs-sans.png)
- [Sharp editorial serif](../output/imagegen/typography-studies/01-editorial-serif.png)
- [Modern sans-serif](../output/imagegen/typography-studies/02-modern-sans.png)
- [Six additional font directions](../output/imagegen/typography-studies/00-six-more-font-directions.png): New York, Bodoni 72 Bold, Baskerville Semibold, Optima Bold, Futura Medium, and DIN Condensed Bold

**Selected:** use New York as the visual direction for all visible identity typography across the four cinematic frames: `Eric Wu`, the interests treatment, the two-line Stanford treatment, and any visible social-link labels. Maintain hierarchy through scale, spacing, position, and timing rather than changing type families. The typography used after the cinematic intro remains unselected.

Implementation note: New York is an Apple system typeface and its font files must not be copied into or distributed with the public website without appropriate web-embedding rights. Before production, verify an authorized delivery route or present Eric with a close, legally embeddable equivalent for explicit approval. Do not silently substitute another font.

Current four-frame copy map:

| View | Identity facet | Current copy |
| --- | --- | --- |
| Hong Kong A | Name | `Eric Wu` |
| Hong Kong B | Interests | `Interested in:` plus sequential reveals of `AI Engineering & Research`, `Math`, `CS`, and `Public Policy` |
| Stanford A | Education | Two lines: a larger `Stanford` above a smaller `Class of 2029` |
| Stanford B | Contact | Recognizable icons for `GitHub`, `LinkedIn`, `X`, `Instagram`, and `Email` |

This is identity copy, not explanatory positioning copy. Final line breaks will be composed separately for desktop and mobile. Each Stanford B item is a real semantic link using the destinations below.

Social-icon treatment:

- Use recognizable official brand SVGs for GitHub, LinkedIn, X, and Instagram.
- Use a clear envelope icon for Email.
- Keep every icon monochrome off-white with identical visual weight. Do not use platform brand colors.
- Do not place the icons inside decorative pills or cards.
- Desktop uses one horizontal row in this order: GitHub, LinkedIn, X, Instagram, Email.
- Mobile uses a centered 3-over-2 arrangement while preserving the same reading order.
- Every icon link receives an accessible name and a visible label on hover or keyboard focus.
- The entire icon group participates in the same foreground-object reveal and cover choreography as the other identity treatments.

Exact destinations:

- GitHub: `https://github.com/ericrcwu001`
- LinkedIn: `https://linkedin.com/in/ericrcwu`
- X: `https://x.com/ericrcwu17`
- Instagram: `https://instagram.com/ericrcwu`
- Email: `mailto:ericrcwu@stanford.edu`

Production layering:

1. Full reconstructed environment sequence
2. Semantic HTML typography
3. A synchronized transparent foreground-object pass rendered from the same camera

The third layer repeats only the designated foreground occluders, such as branches, railing, a column, or an architectural edge. Because it is rendered from the exact same camera, it sits perfectly over the full environment while covering the HTML between the two visual layers.

Implementation constraints:

- **Locked:** all copy and social icons remain semantic webpage elements; no AI-generated or rendered background video may contain the website typography.
- The environment stays visually dominant.
- Every identity treatment remains legible without becoming a billboard.
- Text appears only long enough to read and clears before the next message.
- Desktop, mobile, and reduced-motion compositions are designed separately.

### Alternative text-placement studies

All seven options use the same Memorial Church base frame and exact copy so placement can be compared without background or spelling changes.

- [All options contact sheet](../output/imagegen/text-placement-studies/00-all-text-placement-options.png)
- [Cinematic lower-third](../output/imagegen/text-placement-studies/01-cinematic-lower-third.png)
- [Scene-aware editorial](../output/imagegen/text-placement-studies/02-scene-aware-editorial.png)
- [Masked screen text - selected](../output/imagegen/text-placement-studies/03-masked-screen-text.png)
- [Camera-pause text](../output/imagegen/text-placement-studies/04-camera-pause-storyboard.png)
- [Caption rail](../output/imagegen/text-placement-studies/05-caption-rail.png)
- [Cinematic letterbox](../output/imagegen/text-placement-studies/06-cinematic-letterbox.png)
- [Separate identity frame](../output/imagegen/text-placement-studies/07-separate-identity-frame.png)

These are composition studies, not final typography, color, or reconstruction assets.

## Homepage structure after the intro

The intro hands directly into Work. There is no intermediate section explaining how Eric thinks or builds. The homepage order is:

1. Cinematic identity intro
2. Interactive project chooser
3. Personal section
4. Compact contact and navigation footer

### Interactive project chooser

The visitor should be able to see the available work and choose which project to enter first. The homepage does not play every project in a mandatory sequence.

Approved section copy:

> **Projects**  
> AI systems I’ve built across research, evaluation, and product.

Desktop direction:

- A concise header identifies the section as Eric's projects, and the project titles are visible immediately with it.
- A project index occupies one side of the viewport and a large preview stage occupies the other.
- All project titles remain visible and directly selectable.
- Every project receives identical visual weight: the same title scale, space, metadata allowance, and preview capability.
- There are no flagship, featured, or secondary project treatments for now.
- Hovering, focusing, or moving through the index changes the preview stage.
- Each entry includes only the project name, one concrete sentence, and a small amount of useful metadata.
- Clicking or pressing Enter opens that project's dedicated page.
- The selected preview may move, but the specific preview format remains TBD for every project.
- The preview stage begins in a neutral overview state with no project preselected.
- CES remains the final entry until Eric's contribution is complete.
- There is no separate `Work` title screen, introductory animation, or extra action before the chooser.

Mobile direction:

- Collapse to a single-column visual index.
- Each project has a real thumbnail or lightweight preview placed next to or immediately above its title.
- Tapping anywhere in the entry opens the project page.
- No interaction depends on hover, precise dragging, or a pinned desktop layout.

The chooser should feel like a visual table of contents, not a grid of generic equal cards. Project-specific media, copy, ordering, and showcase formats remain unassigned until the project inventory is verified.

### Column-to-Work handoff

- Stanford B ends with a Main Quad arcade column crossing the viewport.
- Once the column fully covers the screen, the reconstructed media layer is replaced by the Work section behind the same foreground pass.
- As the column continues and clears, the project chooser is revealed in place.
- The Work surface is dark charcoal rather than pure black, with off-white typography and no final accent color assigned yet.
- A compact projects header and all project titles appear together as soon as the column clears.
- The chooser begins in its neutral state with no project preselected and every project given equal visual weight.
- The intro pin releases only after the column clears, preventing a visible jump between cinematic and normal page scrolling.
- No crossfade, morph, or loading interstitial is used.
- Mobile requires its own column path and timing so the wipe still covers the full narrow viewport.

### Personal section

A personal section appears after the project chooser. Its purpose is to reveal dimensions of Eric beyond technical work without interrupting the path into the portfolio.

The section's title, subjects, content, photography, layout, and interactions are all TBD. No hobbies or personal formats are assigned yet.

## Transition design

The selected transition is a shared late-golden-hour atmospheric bridge. Its detailed render contract is in [Atmospheric Bridge Specification](./atmospheric-bridge-spec.md).

Match the following before final rendering:

- Camera travel direction and apparent speed
- Lens, roll, and motion-blur character
- Sun screen position, light direction, exposure, and color temperature
- Cloud shape, haze density, volumetric-noise phase, and atmospheric motion
- The rate at which the Hong Kong horizon disappears and Stanford canopy enters
- Motion blur and shutter character
- Absence of identifiable architecture at the geometry-handoff point

The Hong Kong environment remains the skyline viewed from Braemar Hill Lookout, and the Stanford environment remains Memorial Church. The final Hong Kong telephoto moment frames the Bank of China Tower and Two IFC before the camera continues right, cranes upward, and pitches toward the sky. The skyline and foreground foliage leave through the lower frame edge at different parallax rates; neither layer fades out. Once the atmosphere contains no recognizable Hong Kong geometry, the fully opaque underlying environment changes at the sky-filled apex while the same sky dome, volumetric field, sun, exposure, lens, and camera-velocity curve continue. The camera then descends and pitches down so Stanford oak canopy and Memorial Church enter naturally from below into the selected Wide / Gliding composition.

Both scenes take place at late golden hour specifically so the bridge can use one believable atmospheric state. The grade must remain natural rather than pushing both locations into an artificial orange palette. There is no white flash, whip pan, architecture dissolve, or full-frame object wipe.

### Stanford A-to-B continuity

The selected Wide / Gliding Stanford pair is one physical camera journey through the same reconstructed Main Quad environment. Stanford A and B are composition beats along that path, not separate scenes. It must never look like photographs sliding, wiping, dissolving, or cutting into one another.

- Build Memorial Church, the visible Main Quad ground plane, and the connecting arcade in one shared coordinate system with one sun, sky, exposure model, and late-golden-hour grade.
- Choreograph one rightward master camera spline from the wide church reveal toward the arcade. The camera can slow for the Stanford A copy and again for the social links, but its position, rotation, and velocity curves remain continuous with no snap or dead stop.
- Preserve a believable pedestrian camera height and avoid an impossible flat image pan. The selected motion now uses a restrained opening, an aggressive curved rightward translation plus decisive yaw through the foreground column, and a controlled deceleration into the arcade. The middle must feel like a cinematic speed ramp rather than a constant-speed glide.
- Let nearby sandstone columns pass through frame with accelerating parallax as the camera approaches the arcade. They may occlude the HTML typography, but the beauty pass behind them remains the same continuous render.
- Do not permit a camera-corridor cut inside Stanford, even under full column coverage. If the route exceeds reliable source coverage, shorten the physical path or improve the reconstruction rather than swapping plates.
- Do not crossfade, morph architecture, interpolate unrelated photographs, or change focal length discontinuously. Any lens adjustment must happen gradually as part of the same virtual camera move.
- Render the beauty pass and foreground-object alpha pass from the same camera and frame range. This keeps the column edge, HTML text masking, environment, and motion blur registered to the pixel.
- Validate the continuous path first as a low-resolution geometry animatic. Review it at normal scrolling speed, fast scrubbing, reverse scrolling, and the closest-column parallax moment before committing to final reconstruction detail.

Transition acceptance test: when all text and annotations are removed, the Stanford section must still read as one camera gliding from the Main Quad toward and beneath its arcade. There must be no internal cut to locate frame by frame.

The first Wan FLF2V Stanford take (`stanford_wan21_flf2v_720p_v1`, seed `94117`) is rejected for final use: its uniform, elementary pan remains insufficiently cinematic even after stabilization and 32 fps interpolation. Post-processing may remove residual shake, but it cannot substitute for the required camera choreography.

## Selected reconstruction approach

The selected route is a capture-free, source-grounded hybrid. Eric does not need to photograph, scan, record, or prepare either location. The detailed source and licensing audit is in [Reconstruction and Asset Feasibility Audit](./reconstruction-asset-audit.md).

Hong Kong and Stanford intentionally use different reconstruction methods:

1. **Hong Kong:** use the Hong Kong Lands Department's official territory-wide textured 3D data for geography, landmark silhouettes, parallax, and camera alignment. Project licensed real Braemar Hill sunset photography or footage onto the visible geometry for final appearance. Use a limited-view Gaussian representation only where a licensed moving clip contains adequate real parallax.
2. **Stanford:** use public-domain 2020 Santa Clara County LiDAR for terrain, roofs, scale, and alignment. Rebuild the Memorial Church facade and Main Quad arcade as clean, camera-specific geometry from public-domain/CC0 HABS, Highsmith, and Wikimedia photography. Do not rely on a one-click NeRF from inconsistent internet images.
3. **AI assistance:** use source-grounded camera/depth estimation, restoration, upscale, haze continuity, foliage/sky completion, and projection-seam repair. Never generate recognizable tower or church geometry, window arrangements, mosaics, arches, columns, or rooflines.
4. Render a persistent sky and volumetric atmosphere across the Hong Kong-to-Stanford bridge, with continuous camera velocity, lens, light, exposure, cloud motion, and volumetric-noise phase.
5. Render the final camera paths and synchronized foreground-object passes offline at high quality, then optimize them for scroll-controlled web playback.

The reconstruction only needs to support two continuous camera corridors, one in Hong Kong and one at Stanford, with two identity compositions along each path. Building complete explorable versions of either location would add cost without improving the homepage.

The browser will not render the complete photorealistic environment live in version one. It will play an optimized pre-rendered sequence tied to scroll position. This keeps the camera feeling three-dimensional while avoiding device-dependent frame-rate drops and loading a full reconstruction into every visitor's browser.

Purely AI-generated city or campus imagery remains out of scope. AI-assisted pixels are allowed only when they are constrained by real source data and kept outside protected landmark geometry.

## Playback architecture for a future prototype

This is an implementation direction, not a commitment:

- Next.js and TypeScript for the site.
- A pinned media layer dedicated to the intro.
- GSAP ScrollTrigger to map scroll progress to the camera sequence and copy beats.
- A synchronized transparent foreground-object pass sits above the semantic text and creates the object-shaped occlusion.
- The full environment, HTML copy, and foreground pass share one scrubbed timeline so their alignment cannot drift.
- Real semantic HTML for all text, navigation, and actions. Text is never baked into the render.
- Native browser scrolling. Avoid a global smooth-scroll replacement.
- A poster frame renders immediately while enhanced media is loading.
- The sequence loads progressively and does not decode every frame at once.
- A low-resolution animatic determines whether video scrubbing, an image sequence, or another delivery format is smoothest before final assets are produced.

## Performance budgets for the prototype

- LCP poster target: roughly 300 KB or less.
- Desktop intro media target: approximately 8-12 MB total for the initially required sequence.
- Mobile intro media target: approximately 3 MB, with a shorter or differently cropped path.
- Do not show low-frame-rate live 3D as a fallback. Use a controlled pre-rendered or static experience instead.
- Reserve all media dimensions to avoid layout shift.
- Test on an ordinary phone and an integrated-GPU laptop, not only a high-end development machine.

These are starting constraints, not permission to sacrifice visible quality. The animatic should tell us whether the desired shot fits them.

## Mobile version

Mobile needs its own composition rather than a center crop of the desktop sequence.

- Shorten the camera travel while preserving one identity facet per full-screen view.
- Choose vertical-safe Hong Kong and Stanford views during location planning.
- Keep `Eric Wu` in the first viewport. Reflow the interests, Stanford, and social-link treatments for the narrower compositions.
- Use the same hidden-cut logic, but allow a different occluding object or cut timing.
- Prefer a pre-rendered sequence over live 3D.
- If the device cannot play the enhanced sequence smoothly, crossfade between a small set of real keyframes while the page scrolls normally.

## Reduced-motion version

- No scrubbed camera movement, parallax, or long pinned region.
- Present the four identity facets in a short static sequence using the same Hong Kong and Stanford imagery, followed by Projects.
- Preserve the same information hierarchy and real imagery.
- Never autoplay audio. The main experience is silent in every mode.

## Creative-control gates

No later phase begins until Eric approves the prior one.

1. **Approved:** use real-world 3D reconstruction with photorealism as the priority.
2. **Approved:** use the skyline from Braemar Hill Lookout for Hong Kong.
3. **Approved:** use Stanford Memorial Church for Stanford.
4. **Approved:** use late golden hour across both environments.
5. **Approved:** keep Eric off-camera during the intro.
6. **Superseded:** the earlier combined opening role line has been redistributed across the four identity frames.
7. **Approved:** hand directly into a non-linear project chooser, followed by a personal section.
8. **Approved:** give every project identical visual weight for now.
9. **Approved:** keep the Hong Kong-to-Stanford biography as visual subtext rather than explicit narration.
10. **Superseded:** the earlier fade-out is replaced by full foreground-object occlusion.
11. **Rejected after visual study:** spatial and extruded typography.
12. **Approved:** use masked screen text with reconstructed foreground objects hiding the copy during scroll.
13. **Approved:** full occlusion permanently transitions away from the prior message during forward scrolling.
14. **Approved:** place a brief environment-only pause before the next message enters.
15. **Approved:** reveal each later identity facet when a new foreground object moves away from it, with no opacity fade.
16. **Approved:** position each identity treatment wherever the strongest revealing object and composition exist.
17. **Approved:** give Hong Kong and Stanford equal active scroll time.
18. **Approved:** use two full-screen identity compositions per location rather than layered photo panels.
19. **Clarified:** the two compositions in each location are anchor moments along one continuous 3D camera path, not separate scenes or plates.
20. **Approved:** make Hong Kong B a scroll-controlled telephoto push toward notable skyline buildings.
21. **Selected by design direction:** target the Bank of China Tower and Two IFC while retaining Victoria Harbour.
22. **Approved:** use a frontal Memorial Church establishing view followed by an oblique Main Quad arcade view.
23. **Superseded:** the tower-edge to sandstone-column match cut is replaced by a shared sky-and-haze atmospheric bridge.
24. **Approved:** reveal Memorial Church slightly off-axis, positioned right of center as Stanford canopy and haze clear from the continuous atmospheric bridge.
25. **Approved:** use a final Stanford arcade column to cover the scene and reveal the Work chooser.
26. **Approved:** reveal a dark charcoal Work surface with off-white typography.
27. **Approved:** reveal a concise projects header and the full project-title chooser immediately, with no intermediary Work screen.
28. **Approved:** use `Projects` with `AI systems I’ve built across research, evaluation, and product.`
29. **Superseded:** the intro is no longer limited to one opening text treatment.
30. **Superseded:** line breaks are now determined separately for each of the four identity frames.
31. **Approved:** map the four views to name, interests, Stanford, and social links.
32. **Approved:** include GitHub, LinkedIn, X, Instagram, and Email in Stanford B.
33. **Approved:** represent the Stanford B links with recognizable icons rather than written names.
34. **Approved:** use a horizontal desktop row and centered 3-over-2 mobile arrangement.
35. **Approved:** use the GitHub, LinkedIn, and email destinations from Eric's CV, plus `@ericrcwu17` on X and `@ericrcwu` on Instagram.
36. **Approved for the storyboard:** make `Eric Wu` a large cinematic opening title.
37. **Approved for the storyboard:** use New York consistently across all four identity frames, subject to a legal cross-platform web-delivery decision before production.
38. **Approved for the storyboard:** reveal the Hong Kong B interests sequentially rather than displaying them as one static group.
39. **Approved for the storyboard:** accumulate each revealed interest into a growing list; do not replace prior interests.
40. **Approved for the storyboard:** retire `Interested in:` when the first interest appears; it does not remain in the completed list.
41. **Approved for the storyboard:** give all four interests identical visual weight.
42. **Approved for the storyboard:** split the Stanford A copy into `Stanford` and `Class of 2029` on two lines.
43. **Approved for the storyboard:** make `Stanford` larger than `Class of 2029`.
44. **Approved and clarified:** use the Wide / Gliding Stanford pair as one source-grounded, uninterrupted 3D camera move. No image wipe, background swap, or fully column-hidden internal cut is allowed between Stanford A and Stanford B.
45. **Approved:** connect Hong Kong and Stanford with a continuous shared late-golden-hour sky and volumetric-haze bridge; no tower-to-column cut, image wipe, architectural morph, exposure flash, or motion reset.
46. **Approved:** use the pronounced vertical bridge motion from the proxy proof: crane upward until fully opaque Hong Kong exits below frame, hold a brief sky-only apex, then descend until fully opaque Stanford rises from below. Do not animate either environment's opacity.
47. **Approved:** keep every title, interest line, and social icon in semantic HTML/CSS; never ask a video model to generate the website text.
48. Approve a storyboard with final candidate copy.
49. Approve a low-resolution geometry animatic using the real reconstructed environments and shared atmospheric pass.
50. Build and approve one transition and typography proof on desktop and mobile.
51. Capture or reconstruct the final environments and their foreground occlusion passes.
52. Integrate the optimized media and perform device testing.
53. Verify the project inventory and design the chooser content.
54. Define and approve the personal section.

## Major decisions still owned by Eric

These are the remaining high-leverage questions. They should be resolved one at a time; minor typographic and spacing decisions can be handled later in the storyboard and visual proof.

- **Primary outcome — deferred, non-blocking:** audience prioritization will later shape project-page evidence and calls to action, but the identity intro can serve multiple audiences and does not require a single primary visitor yet.
- **Capture and reconstruction plan — resolved:** use the capture-free hybrid route in [Reconstruction and Asset Feasibility Audit](./reconstruction-asset-audit.md). Eric is not responsible for gathering inputs.
- **Production constraints:** the real time, budget, equipment, and collaborator capacity available for reconstruction, cleanup, rendering, optimization, and device testing.
- **Launch scope:** whether the first public release must include the complete homepage and project pages or whether a polished cinematic-intro prototype should be validated before the full site is built.
- **Device promise:** which classes of desktop and mobile hardware must receive the full scrubbed experience and where a lighter version is acceptable.
- **Project inventory and chooser:** which verified projects ship at launch and what evidence each dedicated page needs, while retaining equal homepage weight.
- **Personal section:** what non-technical dimensions of Eric belong on the site and how much privacy or specificity is appropriate.

## Explicitly deferred

- Specific project order, preview media, copy, and showcase interactions
- Project-specific 3D scenes
- Detailed project pages
- Final typography, color tokens, and navigation styling
- Personal-section media and any later portrait placement
- Final asset acquisition, reconstruction, rendering, or implementation
