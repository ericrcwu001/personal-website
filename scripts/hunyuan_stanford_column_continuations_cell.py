# Stanford column-transition continuation proof.
# Paste into one Colab cell after the HunyuanVideo 1.5 utilities/loader cell.
# It restores the two completed 73-frame Drive clips and generates only the
# missing 49-frame physical approaches, then disconnects Colab automatically.
from IPython.display import Video, display
from PIL import Image, ImageDraw
from google.colab import drive as colab_drive, runtime as colab_runtime
import base64
import io
import threading

AUTO_DISCONNECT = True
MAX_RUNTIME_HOURS = 4.0
FORCE_UNASSIGN_AFTER_SECONDS = 180
ERROR_DISCONNECT_DELAY_SECONDS = 120
_shutdown_started = threading.Event()
_error_disconnect_timer = None


def _force_unassign():
    try:
        colab_runtime.unassign()
    except Exception as error:
        print("Forced runtime deletion warning:", repr(error))


def disconnect_runtime_safely(reason):
    if not AUTO_DISCONNECT or _shutdown_started.is_set():
        return
    _shutdown_started.set()
    print("AUTO-DISCONNECT:", reason)
    fallback = threading.Timer(FORCE_UNASSIGN_AFTER_SECONDS, _force_unassign)
    fallback.daemon = True
    fallback.start()
    try:
        root = globals().get("DRIVE_EXPERIMENT")
        if root is not None and "atomic_write_json" in globals():
            atomic_write_json(
                Path(root) / "runtime_shutdown.json",
                {"reason": reason, "requested_at_unix": time.time()},
            )
        colab_drive.flush_and_unmount()
    except Exception as error:
        print("Drive flush/unmount warning:", repr(error))
    try:
        colab_runtime.unassign()
    except Exception as error:
        print("Runtime deletion warning; fallback remains armed:", repr(error))


def _disconnect_on_uncaught_exception(shell, etype, evalue, traceback, tb_offset=None):
    shell.showtraceback((etype, evalue, traceback), tb_offset=tb_offset)
    global _error_disconnect_timer
    reason = f"uncaught error: {etype.__name__}: {evalue}"
    try:
        root = globals().get("DRIVE_EXPERIMENT")
        if root is not None and "atomic_write_json" in globals():
            atomic_write_json(
                Path(root) / "runtime_error.json",
                {
                    "reason": reason,
                    "recorded_at_unix": time.time(),
                    "disconnect_delay_seconds": ERROR_DISCONNECT_DELAY_SECONDS,
                },
            )
    except Exception as error:
        print("Could not persist runtime error record:", repr(error))
    _error_disconnect_timer = threading.Timer(
        ERROR_DISCONNECT_DELAY_SECONDS,
        disconnect_runtime_safely,
        args=(reason,),
    )
    _error_disconnect_timer.daemon = True
    print(
        f"ERROR RECORDED. Colab will disconnect in {ERROR_DISCONNECT_DELAY_SECONDS} seconds. "
        "To keep this runtime for debugging, run: _error_disconnect_timer.cancel()"
    )
    _error_disconnect_timer.start()
    return None


get_ipython().set_custom_exc((Exception,), _disconnect_on_uncaught_exception)


def _hard_cutoff():
    if not _shutdown_started.wait(MAX_RUNTIME_HOURS * 3600):
        disconnect_runtime_safely(f"hard cutoff after {MAX_RUNTIME_HOURS:.1f} hours")


threading.Thread(target=_hard_cutoff, name="colab-billing-failsafe", daemon=True).start()

SOURCE_EXPERIMENT = DRIVE_ROOT / "experiments" / "stanford_anchor_pair_base480_v1"
EXPERIMENT_ID = "stanford_column_continuations_base480_v1"
DRIVE_EXPERIMENT = DRIVE_ROOT / "experiments" / EXPERIMENT_ID
RUNTIME_EXPERIMENT = RUNTIME_ROOT / "experiments" / EXPERIMENT_ID
for directory in (DRIVE_EXPERIMENT, RUNTIME_EXPERIMENT):
    directory.mkdir(parents=True, exist_ok=True)

BASE_480_MODEL = {
    "repo_id": "hunyuanvideo-community/HunyuanVideo-1.5-Diffusers-480p_i2v",
    "revision": "5a700ee883ff4c1b3d887ec4188755a7a5e2f698",
    "width": 848,
    "height": 480,
    "steps": 50,
    "expected_gib": 50.52,
    "target_size": 640,
    "use_meanflow": False,
}

SOURCE_SPECS = {
    "A": {"label": "A_church_to_column", "seed": 81003},
    "B": {"label": "B_arcade_to_column", "seed": 82011},
}


def restore_source_clip(role):
    spec = SOURCE_SPECS[role]
    source_directory = SOURCE_EXPERIMENT / spec["label"] / str(spec["seed"])
    manifest_path = source_directory / "manifest.json"
    local = RUNTIME_EXPERIMENT / f"source_{role}.mp4"
    source_kind = None
    source_sha256 = None

    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            record = manifest.get("artifacts", {}).get("clip.mp4")
            source_clip = source_directory / "clip.mp4"
            if manifest.get("status") != "complete" or not record or not source_clip.is_file():
                raise RuntimeError("candidate is incomplete")
            if source_clip.stat().st_size != record["bytes"] or sha256_file(source_clip) != record["sha256"]:
                raise RuntimeError("clip size/hash verification failed")
            shutil.copy2(source_clip, local)
            source_kind = "verified prior Drive candidate"
            source_sha256 = record["sha256"]
        except Exception as error:
            print(f"Ignoring unusable prior Drive source for {role}:", repr(error))

    if source_kind is None:
        embedded = globals().get("EMBEDDED_SOURCE_CLIPS", {}).get(role)
        if not embedded:
            raise RuntimeError(
                f"No Drive source manifest and no embedded {role} clip. "
                "Use the complete continuation notebook rather than pasting only its final cell."
            )
        payload = base64.b64decode(embedded["base64"])
        digest = hashlib.sha256(payload).hexdigest()
        if len(payload) != embedded["bytes"] or digest != embedded["sha256"]:
            raise RuntimeError(f"Embedded {role} source failed size/hash verification")
        temporary = local.with_name(local.name + f".part-{uuid.uuid4().hex}")
        temporary.write_bytes(payload)
        os.replace(temporary, local)
        source_kind = f"embedded from {embedded['origin_archive']}"
        source_sha256 = digest
        print(f"Restored {role} from the source clip embedded in this notebook")

    probe = probe_video(local)
    if (probe["width"], probe["height"], probe["frames"]) != (848, 480, 73):
        raise RuntimeError(f"Unexpected source structure for {role}: {probe}")
    manifest = {
        "status": "complete",
        "role": role,
        "source_kind": source_kind,
        "sha256": source_sha256,
        "probe": probe,
    }
    durable_source = DRIVE_EXPERIMENT / "sources" / local.name
    published_digest = atomic_publish_file(local, durable_source)
    if published_digest != source_sha256:
        raise RuntimeError(f"Published {role} source digest changed unexpectedly")
    return local, manifest


source_a, manifest_a = restore_source_clip("A")
source_b, manifest_b = restore_source_clip("B")

# Keep B's pixels and motion intact while matching its overall exposure and warmth
# more closely to A before using the continuation anchor.
graded_b = RUNTIME_EXPERIMENT / "source_B_warm_grade.mp4"
subprocess.run(
    [
        "ffmpeg", "-y", "-v", "error", "-i", str(source_b),
        "-vf", "eq=gamma=1.08:brightness=0.025:contrast=1.02:saturation=1.05,"
               "colorbalance=rs=.03:gs=.01:bs=-.03",
        "-an", "-r", "24", "-c:v", "libx264", "-preset", "slow", "-crf", "16",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(graded_b),
    ],
    check=True,
)


def extract_frame(video_path, frame_index, destination):
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error", "-i", str(video_path),
            "-vf", f"select=eq(n\\,{frame_index})", "-frames:v", "1", str(destination),
        ],
        check=True,
    )
    image = Image.open(destination).convert("RGB")
    if image.size != (848, 480):
        raise RuntimeError(f"Unexpected extracted anchor size: {image.size}")
    return image


anchor_a_path = RUNTIME_EXPERIMENT / "A_continuation_anchor_frame56.png"
anchor_b_path = RUNTIME_EXPERIMENT / "B_continuation_anchor_frame56_warm.png"
anchor_a = extract_frame(source_a, 56, anchor_a_path)
anchor_b = extract_frame(graded_b, 56, anchor_b_path)
for anchor_path in (anchor_a_path, anchor_b_path):
    atomic_publish_file(anchor_path, DRIVE_EXPERIMENT / anchor_path.name)

anchor_sheet = Image.new("RGB", (1696, 520), "#111111")
anchor_sheet.paste(anchor_a, (0, 0))
anchor_sheet.paste(anchor_b, (848, 0))
anchor_draw = ImageDraw.Draw(anchor_sheet)
anchor_draw.text((12, 490), "A continuation anchor — exact source frame 56", fill="white")
anchor_draw.text((860, 490), "B continuation anchor — exact source frame 56, warm grade", fill="white")
display(anchor_sheet)

NEGATIVE_PROMPT = (
    "optical zoom, digital zoom, zoom lens, dolly zoom, drone, quadcopter, aircraft, helicopter, propeller, "
    "camera rig, filming equipment, morph, dissolve, fade, opacity transition, camera cut, frozen frame, "
    "warped architecture, bending column, duplicated arch, melting stone, jitter, flicker, text, watermark"
)

PROMPT_A = (
    "Continue from this exact frame with no cut and a fixed focal length. The camera is already beside the nearest "
    "fluted Stanford sandstone column. It immediately translates physically forward and slightly left by about one "
    "meter toward the middle of that same column shaft; this is real camera translation, never a lens zoom. The "
    "column expands rapidly from perspective while the distant Memorial Church and courtyard slide behind it with "
    "strong layered parallax. Accelerate smoothly toward the obstruction. By frame 35 the column covers at least "
    "ninety percent of the view. Frames 40 through 48 contain only an extreme close-up of opaque sandstone texture "
    "edge-to-edge: no sky, church, trees, pavement, arch opening, or background remains visible. Preserve the exact "
    "architecture and late-golden-hour color of the starting frame. Photorealistic live-action footage."
)

PROMPT_B = (
    "Continue from this exact frame with no cut and a fixed focal length. The camera is already beside the nearest "
    "Stanford sandstone column. It immediately translates physically forward and slightly downward by about one "
    "meter toward the plain cylindrical shaft below the capital; this is real camera translation, never a lens "
    "zoom. The shaft expands rapidly from perspective while the distant Main Quad arcade and courtyard slide behind "
    "it with strong layered parallax. Accelerate smoothly toward the obstruction. By frame 35 the column covers at "
    "least ninety percent of the view. Frames 40 through 48 contain only an extreme close-up of opaque warm sandstone "
    "texture edge-to-edge: no sky, tower, roof, courtyard, arch opening, people, or background remains visible. "
    "Preserve rigid Stanford geometry and the warm daylight of the starting frame. Photorealistic live-action footage."
)


def continuation_valid(directory):
    manifest_path = directory / "manifest.json"
    if not manifest_path.is_file():
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for name, record in manifest["artifacts"].items():
            path = directory / name
            if not path.is_file() or path.stat().st_size != record["bytes"]:
                return False
            if sha256_file(path) != record["sha256"]:
                return False
        probe = probe_video(directory / "clip.mp4")
        return (probe["width"], probe["height"], probe["frames"]) == (848, 480, 49)
    except Exception:
        return False


def render_continuation(pipe, label, image, prompt, seed):
    drive_directory = DRIVE_EXPERIMENT / label / str(seed)
    runtime_directory = RUNTIME_EXPERIMENT / label / str(seed)
    if continuation_valid(drive_directory):
        runtime_directory.mkdir(parents=True, exist_ok=True)
        for name in ("clip.mp4", "contact_sheet.jpg", "final_frame.png"):
            shutil.copy2(drive_directory / name, runtime_directory / name)
        print("Restored completed continuation:", label, seed)
        return runtime_directory / "clip.mp4", drive_directory

    runtime_directory.mkdir(parents=True, exist_ok=True)
    started = time.time()
    result = pipe(
        image=image,
        prompt=prompt,
        negative_prompt=NEGATIVE_PROMPT,
        num_frames=49,
        num_inference_steps=50,
        generator=torch.Generator(device="cuda").manual_seed(seed),
        output_type="np",
    )
    frames = normalize_output(result)
    if len(frames) != 49:
        raise RuntimeError(f"{label} returned {len(frames)} frames instead of 49")
    frames[0] = np.asarray(image, dtype=np.uint8)

    clip_path = runtime_directory / "clip.mp4"
    contact_path = runtime_directory / "contact_sheet.jpg"
    final_path = runtime_directory / "final_frame.png"
    encode_video(frames, clip_path, crf=16)
    write_contact_sheet(frames, contact_path, f"{label} | seed {seed} | native 49 frames")
    Image.fromarray(frames[-1]).save(final_path, "PNG", optimize=True)

    artifacts = {}
    for path in (clip_path, contact_path, final_path):
        digest = atomic_publish_file(path, drive_directory / path.name)
        artifacts[path.name] = {"bytes": path.stat().st_size, "sha256": digest}
    atomic_write_json(
        drive_directory / "manifest.json",
        {
            "status": "complete",
            "label": label,
            "seed": seed,
            "model": BASE_480_MODEL,
            "prompt": prompt,
            "negative_prompt": NEGATIVE_PROMPT,
            "native_frames": 49,
            "fps": 24,
            "source_frame": 56,
            "fixed_focal_length_requested": True,
            "started_at_unix": started,
            "completed_at_unix": time.time(),
            "artifacts": artifacts,
            "visual_status": "manual_review_required",
        },
    )
    return clip_path, drive_directory


model_directory = acquire_model(BASE_480_MODEL, "stanford-column-continuations-base480")
pipe = load_hunyuan(model_directory, BASE_480_MODEL, "stanford-column-continuations-base480")
if abs(float(pipe.guider.guidance_scale) - 6.0) > 1e-6:
    raise RuntimeError(f"Expected active CFG 6, found {pipe.guider.guidance_scale}")

try:
    continuation_a, drive_a = render_continuation(pipe, "A_physical_column_finish", anchor_a, PROMPT_A, 81107)
    display(Image.open(drive_a / "contact_sheet.jpg"))
    continuation_b, drive_b = render_continuation(pipe, "B_physical_column_finish", anchor_b, PROMPT_B, 82109)
    display(Image.open(drive_b / "contact_sheet.jpg"))
finally:
    dispose_pipeline(pipe)
    pipe = None


def splice_continuation(source, continuation, destination):
    subprocess.run(
        [
            "ffmpeg", "-y", "-v", "error", "-i", str(source), "-i", str(continuation),
            "-filter_complex",
            "[0:v]trim=start_frame=0:end_frame=56,setpts=PTS-STARTPTS[p];"
            "[1:v]trim=start_frame=1:end_frame=49,setpts=PTS-STARTPTS[c];"
            "[p][c]concat=n=2:v=1:a=0[v]",
            "-map", "[v]", "-an", "-r", "24", "-c:v", "libx264", "-preset", "slow", "-crf", "16",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(destination),
        ],
        check=True,
    )
    probe = probe_video(destination)
    if (probe["width"], probe["height"], probe["frames"]) != (848, 480, 104):
        raise RuntimeError(f"Invalid extended clip: {destination}: {probe}")


extended_a = RUNTIME_EXPERIMENT / "A_church_to_full_column_extended.mp4"
extended_b = RUNTIME_EXPERIMENT / "B_arcade_to_full_column_extended.mp4"
splice_continuation(source_a, continuation_a, extended_a)
splice_continuation(graded_b, continuation_b, extended_b)

reversed_b = RUNTIME_EXPERIMENT / "B_full_column_to_arcade_reversed.mp4"
subprocess.run(
    [
        "ffmpeg", "-y", "-v", "error", "-i", str(extended_b),
        "-vf", "reverse,setpts=PTS-STARTPTS", "-an", "-r", "24",
        "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(reversed_b),
    ],
    check=True,
)

joined = RUNTIME_EXPERIMENT / "stanford_physical_column_transition.mp4"
subprocess.run(
    [
        "ffmpeg", "-y", "-v", "error", "-i", str(extended_a), "-i", str(reversed_b),
        "-filter_complex", "[0:v]setpts=PTS-STARTPTS[a];[1:v]setpts=PTS-STARTPTS[b];"
                           "[a][b]concat=n=2:v=1:a=0[v]",
        "-map", "[v]", "-an", "-r", "24", "-c:v", "libx264", "-preset", "slow", "-crf", "16",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(joined),
    ],
    check=True,
)
joined_probe = probe_video(joined)
if (joined_probe["width"], joined_probe["height"], joined_probe["frames"]) != (848, 480, 208):
    raise RuntimeError(f"Invalid joined proof: {joined_probe}")


def decode_frame(path, index):
    result = subprocess.run(
        [
            "ffmpeg", "-v", "error", "-i", str(path), "-vf", f"select=eq(n\\,{index})",
            "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-",
        ],
        check=True,
        capture_output=True,
    )
    return np.asarray(Image.open(io.BytesIO(result.stdout)).convert("RGB"))


left = decode_frame(extended_a, 103)
right = decode_frame(reversed_b, 0)
mse = float(np.mean((left.astype(np.float32) - right.astype(np.float32)) ** 2))
seam_psnr = float("inf") if mse == 0 else float(10.0 * np.log10((255.0 ** 2) / mse))
seam_mae = float(np.abs(left.astype(np.float32) - right.astype(np.float32)).mean())


def outdoor_color_fraction(frame):
    rgb = frame.astype(np.float32) / 255.0
    red, green, blue = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    blue_sky = (blue > 0.35) & (blue > red * 1.14) & (blue > green * 1.05)
    vegetation = (green > 0.18) & (green > red * 1.12) & (green > blue * 1.04)
    return float(np.mean(blue_sky | vegetation))


diagnostic = Image.new("RGB", (1696, 520), "#111111")
diagnostic.paste(Image.fromarray(left), (0, 0))
diagnostic.paste(Image.fromarray(right), (848, 0))
diagnostic_draw = ImageDraw.Draw(diagnostic)
diagnostic_draw.text((12, 490), "A terminal frame", fill="white")
diagnostic_draw.text(
    (860, 490),
    f"reversed B initial frame | PSNR {seam_psnr:.2f} dB | MAE {seam_mae:.2f}",
    fill="white",
)
diagnostic_path = RUNTIME_EXPERIMENT / "column_seam_diagnostic.jpg"
diagnostic.save(diagnostic_path, "JPEG", quality=94)

final_artifacts = {}
for local_path in (extended_a, extended_b, reversed_b, joined, diagnostic_path):
    digest = atomic_publish_file(local_path, DRIVE_EXPERIMENT / local_path.name)
    final_artifacts[local_path.name] = {"bytes": local_path.stat().st_size, "sha256": digest}

report_path = DRIVE_EXPERIMENT / "experiment_report.json"
atomic_write_json(
    report_path,
    {
        "status": "complete_persistence_verified_visual_review_required",
        "experiment_id": EXPERIMENT_ID,
        "source_experiment": str(SOURCE_EXPERIMENT),
        "source_frame": 56,
        "continuation_frames": 49,
        "joined_probe": joined_probe,
        "seam_psnr_db": seam_psnr,
        "seam_mae": seam_mae,
        "A_terminal_outdoor_color_fraction": outdoor_color_fraction(left),
        "B_terminal_outdoor_color_fraction": outdoor_color_fraction(right),
        "pixel_crossfade": False,
        "rgb_retiming": False,
        "post_camera_zoom": False,
        "B_global_color_grade": True,
        "visual_gate": (
            "Reject unless both terminal frames contain only opaque sandstone edge-to-edge, the seam is hidden, "
            "and both continuations show physical parallax rather than a lens zoom."
        ),
        "artifacts": final_artifacts,
    },
)

for name, record in final_artifacts.items():
    persisted = DRIVE_EXPERIMENT / name
    if not persisted.is_file() or persisted.stat().st_size != record["bytes"]:
        raise RuntimeError(f"Persisted artifact failed size verification: {persisted}")
    if sha256_file(persisted) != record["sha256"]:
        raise RuntimeError(f"Persisted artifact failed hash verification: {persisted}")

success_path = DRIVE_EXPERIMENT / "_PERSISTENCE_SUCCESS.json"
atomic_write_json(
    success_path,
    {
        "status": "outputs_complete_and_hash_verified_visual_review_still_required",
        "completed_at_unix": time.time(),
        "experiment_report_sha256": sha256_file(report_path),
        "artifacts": final_artifacts,
    },
)

display(diagnostic)
display(Video(str(joined), embed=True, width=848))
print("PERSISTED EXPERIMENT:", DRIVE_EXPERIMENT)
print("PERSISTENCE MARKER:", success_path)
disconnect_runtime_safely("continuation experiment completed and Drive artifacts verified")
