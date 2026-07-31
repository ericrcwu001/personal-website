# Paste this entire file into one Colab cell after the utilities/loader cell.
# It creates a separate proof and does not overwrite the first proof.
from IPython.display import Video, display

PHYSICAL_PROOF_RUN_ID = "intro_480proof_v2_physical_camera"
PROOF_RUN_ID = PHYSICAL_PROOF_RUN_ID
DRIVE_PROOF = DRIVE_ROOT / "runs" / PROOF_RUN_ID
RUNTIME_PROOF = RUNTIME_ROOT / "runs" / PROOF_RUN_ID
PROOF_GATE = DRIVE_PROOF / "proof_gate.json"
for path in (DRIVE_PROOF, RUNTIME_PROOF):
    path.mkdir(parents=True, exist_ok=True)
    
NEGATIVE_PROMPT = (
    "static camera, locked camera, hovering, Ken Burns effect, digital zoom, rotating flat photograph, "
    "crossfade, dissolve, fade in, fade out, opacity transition, ghosted double exposure, superimposition, "
    "morph, portal, teleportation, melting architecture, buildings appearing from transparency, floating tram, "
    "airborne car, impossible vehicle, duplicated building, bent facade, warped street, camera cut, jitter, "
    "flicker, title, caption, logo, watermark, illustration"
)

# Each pair is one slow-in/slow-out physical movement:
# S0 accelerates -> S1 decelerates; S2 accelerates -> S3 decelerates;
# S4 accelerates -> S5 decelerates.
SEGMENTS = [
    {
        "id": "S0_hk_drone_launch",
        "display_frames": 72,
        "request_frames": 121,
        "mode": "forward_anchor",
        "anchor": "hk_braemar_wide",
        "ease": "accelerate",
        "motion_min": 0.45,
        "seeds": [71003],
        "prompt": (
            "One uninterrupted photorealistic FPV drone shot over Hong Kong at late golden hour. The drone begins "
            "with a gentle physical launch from Braemar Hill, then continuously accelerates forward and downward "
            "toward Central on a smooth flight spline. Nearby hillside trees and apartment roofs sweep rapidly "
            "past the lower and side edges with strong differential parallax while Two IFC and Bank of China "
            "Tower grow through real translation. Wide 18mm cinema lens, level horizon, realistic shutter motion "
            "blur, rigid architecture. This is forward flight, never a lens zoom or moving photograph."
        ),
    },
    {
        "id": "S1_hk_tower_canyon",
        "parent": "S0_hk_drone_launch",
        "display_frames": 72,
        "request_frames": 121,
        "mode": "forward_parent",
        "ease": "decelerate",
        "motion_min": 0.55,
        "seeds": [72011],
        "prompt": (
            "Continue the exact same drone, lens, lighting, direction, and velocity with no cut. Begin fast, fly "
            "physically through a broad safe gap between Central skyscrapers, and descend into the street canyon. "
            "Near glass and concrete facades rush outward along both edges with strong real parallax; the distant "
            "street expands in the center. Follow a smooth descending arc and gradually decelerate near rooftop "
            "height. Stable straight buildings, no new objects popping in, no floating vehicles, no orbit or zoom."
        ),
    },
    {
        "id": "S2_hk_vertical_whip",
        "parent": "S1_hk_tower_canyon",
        "display_frames": 60,
        "request_frames": 121,
        "mode": "forward_parent",
        "ease": "accelerate",
        "motion_min": 0.70,
        "min_sky_end": 6,
        "max_sky_end": 20,
        "seeds": [73013],
        "prompt": (
            "Continue from the exact Hong Kong street-canyon frame in one physical drone move. Start gently, "
            "accelerate hard forward between the buildings, then perform a powerful smooth crane climb and pitch "
            "the camera upward through more than ninety degrees. Facades and rooflines sweep downward and leave "
            "through the bottom edge because of camera rotation and translation. End with twelve to eighteen "
            "frames of only textured blue-gold sky and authentic fast vertical shutter blur. No tram, aircraft, "
            "fade, flash, dissolve, morph, portal, or opacity change."
        ),
    },
    {
        "id": "S3_sky_dive_to_church",
        "parent": "S2_hk_vertical_whip",
        "display_frames": 72,
        "request_frames": 121,
        "mode": "reverse_anchor",
        "anchor": "stanford_memorial_church",
        "ease": "decelerate",
        "motion_min": 0.50,
        "min_sky_start": 6,
        "max_sky_start": 20,
        "seeds": [74007],
        "prompt": (
            "A single physically plausible drone departure beginning on the recognizable Stanford Memorial Church "
            "mosaic facade at late golden hour. Start nearly settled, then accelerate backward and upward on a "
            "smooth crane arc while pitching the camera toward the sky. The church, sandstone arcades, and trees "
            "move downward and shrink only through real perspective and parallax. Finish with twelve to eighteen "
            "frames containing only textured blue-gold sky with fast vertical shutter blur. Rigid architecture; "
            "no fade, dissolve, transparency, morph, portal, or building appearing from mist."
        ),
    },
    {
        "id": "S4_church_pan_to_arcade",
        "parent": "S3_sky_dive_to_church",
        "display_frames": 72,
        "request_frames": 121,
        "mode": "forward_parent",
        "ease": "accelerate",
        "motion_min": 0.55,
        "seeds": [75017],
        "prompt": (
            "Continue from the exact Memorial Church view with no cut. Begin a slow stabilized rightward drone "
            "strafe, then accelerate along a smooth curved path while naturally yawing the camera right. Memorial "
            "Church slides out through the left edge; the connected Main Quad sandstone arcade enters from the "
            "right as a real part of the same environment. Fly toward the arcade so one near column sweeps rapidly "
            "past the right side with strong parallax. No fade, dissolve, transparent overlay, morph, or teleport."
        ),
    },
    {
        "id": "S5_arcade_flythrough",
        "parent": "S4_church_pan_to_arcade",
        "display_frames": 84,
        "request_frames": 121,
        "mode": "forward_parent",
        "ease": "decelerate",
        "motion_min": 0.50,
        "seeds": [76019],
        "prompt": (
            "Continue the identical camera path and momentum through Stanford Main Quad arcade with no cut. Begin "
            "fast as the nearest sandstone column clears the lens naturally, then glide forward slightly off axis. "
            "Close columns sweep past both edges with pronounced physical parallax while distant repeating arches "
            "remain stable and straight. Gradually decelerate into a composed long arcade vista. Continuous real "
            "camera translation, no fade, dissolve, transparency, morph, geometry replacement, or static hold."
        ),
    },
]

if sum(segment["display_frames"] for segment in SEGMENTS) != 432:
    raise RuntimeError("Physical proof must remain exactly 432 frames")
if any(segment["request_frames"] % 4 != 1 for segment in SEGMENTS):
    raise RuntimeError("Hunyuan requests must be 4n+1 frames")

STABLE_CONFIG = {
    "logic_version": "hunyuan15-physical-camera-v2.0.0",
    "fps": FPS,
    "diffusers_commit": DIFFUSERS_COMMIT,
    "proof_model": PROOF_MODEL,
    "production_model": PRODUCTION_MODEL,
    "segments": SEGMENTS,
    "negative_prompt": NEGATIVE_PROMPT,
    "captions": CAPTION_TIMELINE,
    "anchors": {name: data["sha256"] for name, data in anchor_manifest.items()},
    "license_scope": "local evaluation only; not cleared for unrestricted global deployment",
}
CONFIG_FINGERPRINT = hashlib.sha256(
    json.dumps(STABLE_CONFIG, sort_keys=True, separators=(",", ":")).encode()
).hexdigest()
write_locked_config(DRIVE_PROOF, PROOF_RUN_ID, "480p_step_distilled_physical_camera")
atomic_write_json(
    DRIVE_PROOF / "camera_plan.json",
    {
        "run_id": PROOF_RUN_ID,
        "config_fingerprint": CONFIG_FINGERPRINT,
        "principle": "paired slow-in/slow-out physical camera moves",
        "hidden_location_seam": "fast full-sky vertical whip; no pixel crossfade",
        "segments": SEGMENTS,
    },
)


def eased_resample(source_frames, output_count, profile):
    source = [frame_to_uint8(frame) for frame in source_frames]
    u = np.linspace(0.0, 1.0, output_count, dtype=np.float32)
    if profile == "accelerate":
        progress = 0.12 * u + 0.88 * (u**2)
    elif profile == "decelerate":
        progress = 0.12 * u + 0.88 * (1.0 - (1.0 - u) ** 2)
    else:
        progress = 3.0 * (u**2) - 2.0 * (u**3)

    positions = progress * (len(source) - 1)
    result = []
    for position in positions:
        left = int(math.floor(float(position)))
        right = min(left + 1, len(source) - 1)
        alpha = float(position - left)
        frame = source[left].astype(np.float32) * (1.0 - alpha) + source[right].astype(np.float32) * alpha
        result.append(np.clip(frame, 0, 255).astype(np.uint8))
    return result


def vertical_whip_blur(frame, strength):
    size = 31
    kernel = np.zeros((size, size), dtype=np.float32)
    kernel[:, size // 2] = 1.0 / size
    blurred = cv2.filter2D(frame, -1, kernel)
    return np.clip(
        frame.astype(np.float32) * (1.0 - strength) + blurred.astype(np.float32) * strength,
        0,
        255,
    ).astype(np.uint8)


def render_physical_segment(pipe, run_root, runtime_root, segment, seed):
    model = PROOF_MODEL
    parent_frame = None
    if segment.get("parent"):
        parent_path = restore_accepted(run_root, segment["parent"], "final_frame.png")
        parent_frame = np.asarray(Image.open(parent_path).convert("RGB"), dtype=np.uint8)

    if segment["mode"] in {"forward_anchor", "reverse_anchor"}:
        input_image = Image.open(ANCHOR_PATHS[segment["anchor"]]).convert("RGB")
    else:
        input_image = Image.fromarray(parent_frame)
    input_image = input_image.resize((model["width"], model["height"]), Image.Resampling.LANCZOS)

    generator = torch.Generator(device="cuda").manual_seed(seed)
    started = time.time()
    output = pipe(
        image=input_image,
        prompt=segment["prompt"],
        negative_prompt=NEGATIVE_PROMPT,
        num_frames=segment["request_frames"],
        num_inference_steps=model["steps"],
        generator=generator,
        output_type="np",
    )
    raw = normalize_output(output)
    if len(raw) != segment["request_frames"]:
        raise RuntimeError(f"Hunyuan returned {len(raw)} frames for {segment['id']}")

    input_exact = np.asarray(input_image, dtype=np.uint8)
    raw[0] = input_exact
    if segment["mode"] == "forward_anchor":
        source = raw
    elif segment["mode"] == "forward_parent":
        source = raw[1:]
    elif segment["mode"] == "reverse_anchor":
        source = list(reversed(raw))
        # A hard full-sky match, not a dissolve. The following rapid frames carry the whip motion.
        source[0] = parent_frame.copy()
    else:
        raise ValueError(segment["mode"])

    frames = eased_resample(source, segment["display_frames"], segment["ease"])

    # Physically motivated shutter blur hides only the full-sky location cut.
    if segment["id"] == "S2_hk_vertical_whip":
        count = min(8, len(frames))
        for index in range(count):
            strength = 0.25 + 0.70 * (index / max(1, count - 1))
            frames[-count + index] = vertical_whip_blur(frames[-count + index], strength)
    elif segment["id"] == "S3_sky_dive_to_church":
        count = min(8, len(frames))
        for index in range(count):
            strength = 0.95 - 0.70 * (index / max(1, count - 1))
            frames[index] = vertical_whip_blur(frames[index], strength)
        frames[0] = parent_frame.copy()

    generation = {
        "model": model,
        "diffusers_commit": DIFFUSERS_COMMIT,
        "started_at_unix": started,
        "completed_at_unix": time.time(),
        "source_frames": segment["request_frames"],
        "display_frames": segment["display_frames"],
        "temporal_profile": segment["ease"],
        "frame_policy": segment["mode"],
        "pixel_crossfade": False,
        "license": "local evaluation only",
    }
    return publish_candidate(
        run_root, runtime_root, segment, seed, "proof", frames, generation, parent_frame
    )


model_dir = None
pipe = None
proof_complete = False
try:
    if not all(accepted_candidate(DRIVE_PROOF, segment) is not None for segment in SEGMENTS):
        model_dir = acquire_model(PROOF_MODEL, "physical-camera-proof")
        pipe = load_hunyuan(model_dir, PROOF_MODEL, "physical-camera-proof")

    for segment in SEGMENTS:
        existing = accepted_candidate(DRIVE_PROOF, segment)
        if existing is not None:
            print("Restored:", segment["id"], "seed", existing[0])
            continue

        seed = segment["seeds"][0]
        ok, reason, manifest = validate_candidate(
            DRIVE_PROOF,
            segment,
            seed,
            "proof",
            PROOF_MODEL["width"],
            PROOF_MODEL["height"],
        )
        if not ok:
            print("Generating", segment["id"], "seed", seed, "because", reason)
            manifest = render_physical_segment(pipe, DRIVE_PROOF, RUNTIME_PROOF, segment, seed)

        display(Image.open(candidate_dir(DRIVE_PROOF, segment, seed, "proof") / "contact_sheet.jpg"))
        print(segment["id"], json.dumps(manifest["metrics"], indent=2))
        if not manifest["metrics"]["usable"]:
            raise RuntimeError(f"Catastrophic proof failure at {segment['id']}: {manifest['metrics']}")
        accept_candidate(DRIVE_PROOF, segment, seed, manifest, "proof")

    proof_complete = True
finally:
    dispose_pipeline(pipe)
    pipe = None
    if proof_complete and model_dir is not None:
        purge_runtime_model(model_dir)

deliverables = DRIVE_PROOF / "deliverables"
deliverables.mkdir(parents=True, exist_ok=True)
clips = [restore_accepted(DRIVE_PROOF, segment["id"], "clip.mp4") for segment in SEGMENTS]
master = RUNTIME_PROOF / "proof_physical_camera_480p24.mp4"
master.parent.mkdir(parents=True, exist_ok=True)
filters = []
labels = []
for index in range(len(clips)):
    filters.append(f"[{index}:v]scale=848:480:flags=lanczos,setsar=1,setpts=PTS-STARTPTS[v{index}]")
    labels.append(f"[v{index}]")
filters.append("".join(labels) + f"concat=n={len(clips)}:v=1:a=0,format=yuv420p[vout]")
command = ["ffmpeg", "-y", "-v", "error"]
for clip in clips:
    command += ["-i", str(clip)]
command += [
    "-filter_complex",
    ";".join(filters),
    "-map",
    "[vout]",
    "-an",
    "-r",
    str(FPS),
    "-c:v",
    "libx264",
    "-crf",
    "17",
    "-pix_fmt",
    "yuv420p",
    "-movflags",
    "+faststart",
    str(master),
]
subprocess.run(command, check=True)
probe = probe_video(master)
if (probe["width"], probe["height"], probe["frames"]) != (848, 480, 432):
    raise RuntimeError(f"Physical proof assembly failed: {probe}")

digest = atomic_publish_file(master, deliverables / master.name)
accepted_hashes = {
    segment["id"]: accepted_candidate(DRIVE_PROOF, segment)[1]["manifest_file_sha256"]
    for segment in SEGMENTS
}
atomic_write_json(
    PROOF_GATE,
    {
        "status": "passed_structural_review_pending",
        "config_fingerprint": CONFIG_FINGERPRINT,
        "master_sha256": digest,
        "accepted_manifest_hashes": accepted_hashes,
        "frames": 432,
        "fps": 24,
        "duration_seconds": 18.0,
        "camera_principle": "paired slow-in/slow-out physical moves",
        "pixel_crossfade": False,
        "license": "local evaluation only",
    },
)

display(Video(str(deliverables / master.name), embed=True, width=848))
print("NEW PHYSICAL-CAMERA PROOF:", deliverables / master.name)
print("SHA-256:", digest)
print("The original proof remains untouched in its previous Drive run directory.")
