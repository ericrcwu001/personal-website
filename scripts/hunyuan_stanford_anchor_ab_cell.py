# Stanford-only anchor-grounding proof. Paste into one Colab cell after the utilities/loader cell.
# This does not modify either complete proof run.
from IPython.display import Video, display
from PIL import Image, ImageDraw, ImageOps
import io
import threading
import urllib.request
from google.colab import drive as colab_drive, runtime as colab_runtime

# Billing fail-safe: disconnect immediately on success or an uncaught error, with a hard cap for hangs.
AUTO_DISCONNECT = True
MAX_RUNTIME_HOURS = 4.0
FORCE_UNASSIGN_AFTER_SECONDS = 180
_shutdown_started = threading.Event()


def _force_unassign():
    # Last-resort billing stop if Drive's FUSE flush stalls indefinitely.
    try:
        print("AUTO-DISCONNECT: forcing Colab runtime deletion after cleanup timeout")
        colab_runtime.unassign()
    except Exception as error:
        print("Forced runtime deletion warning:", repr(error))


def disconnect_runtime_safely(reason):
    if not AUTO_DISCONNECT or _shutdown_started.is_set():
        return
    _shutdown_started.set()
    print(f"AUTO-DISCONNECT: {reason}")
    fallback = threading.Timer(FORCE_UNASSIGN_AFTER_SECONDS, _force_unassign)
    fallback.daemon = True
    fallback.start()
    try:
        experiment_root = globals().get("DRIVE_EXPERIMENT")
        if experiment_root is not None and "atomic_write_json" in globals():
            atomic_write_json(
                Path(experiment_root) / "runtime_shutdown.json",
                {"reason": reason, "requested_at_unix": time.time(), "outputs_persisted": "see manifests"},
            )
        colab_drive.flush_and_unmount()
    except Exception as error:
        print("Drive flush/unmount warning:", repr(error))
    try:
        colab_runtime.unassign()
    except Exception as error:
        # Leave the fallback armed; it will retry runtime deletion.
        print("Runtime deletion warning; fallback remains armed:", repr(error))


def _disconnect_on_uncaught_exception(shell, etype, evalue, traceback, tb_offset=None):
    shell.showtraceback((etype, evalue, traceback), tb_offset=tb_offset)
    disconnect_runtime_safely(f"uncaught error: {etype.__name__}: {evalue}")
    return None


get_ipython().set_custom_exc((Exception,), _disconnect_on_uncaught_exception)


def _hard_cutoff():
    if not _shutdown_started.wait(MAX_RUNTIME_HOURS * 3600):
        disconnect_runtime_safely(f"hard cutoff after {MAX_RUNTIME_HOURS:.1f} hours")


threading.Thread(target=_hard_cutoff, name="colab-billing-failsafe", daemon=True).start()

EXPERIMENT_ID = "stanford_anchor_pair_modern_arcade_v2"
DRIVE_EXPERIMENT = DRIVE_ROOT / "experiments" / EXPERIMENT_ID
RUNTIME_EXPERIMENT = RUNTIME_ROOT / "experiments" / EXPERIMENT_ID
for path in (DRIVE_EXPERIMENT, RUNTIME_EXPERIMENT):
    path.mkdir(parents=True, exist_ok=True)

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

REAL_CHURCH_ARCADE_URL = (
    "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b6/"
    "Stanford_University_Arches_with_Memorial_Church_in_the_background.jpg/"
    "1280px-Stanford_University_Arches_with_Memorial_Church_in_the_background.jpg"
)
REAL_CHURCH_ARCADE_SHA256 = "5dc239ff312b9a86d4a434e711018b0ac824defe09260070ba1c60fd1d82cfbb"
REAL_CHURCH_ARCADE_DRIVE = DRIVE_INPUTS / "stanford-church-arcade-real-1280.jpg"

MODERN_ARCADE_URL = (
    "https://upload.wikimedia.org/wikipedia/commons/7/7a/"
    "Stanford_University_in_2025_03.jpg"
)
MODERN_ARCADE_SHA256 = "9d2f71b7c39d3f2f8f0e78a452cefa9db98765ede63afe1aa0bd0adee135456c"
MODERN_ARCADE_DRIVE = DRIVE_INPUTS / "stanford-main-quad-arcade-2025.jpg"


def download_verified_once(url, destination, expected_sha256):
    destination = Path(destination)
    if destination.is_file() and sha256_file(destination) == expected_sha256:
        return destination
    last_error = None
    for attempt in range(5):
        try:
            request = urllib.request.Request(
                url,
                headers={"User-Agent": "Eric-Wu-portfolio-reference-acquisition/1.0"},
            )
            with urllib.request.urlopen(request, timeout=180) as response:
                payload = response.read()
            if hashlib.sha256(payload).hexdigest() != expected_sha256:
                raise RuntimeError("Downloaded reference hash mismatch")
            temporary = destination.with_name(destination.name + f".part-{uuid.uuid4().hex}")
            temporary.write_bytes(payload)
            os.replace(temporary, destination)
            return destination
        except Exception as error:
            last_error = error
            if attempt < 4:
                time.sleep(2**attempt)
    raise RuntimeError(f"Reference download failed after retries: {last_error}")


real_church_arcade = download_verified_once(
    REAL_CHURCH_ARCADE_URL,
    REAL_CHURCH_ARCADE_DRIVE,
    REAL_CHURCH_ARCADE_SHA256,
)
modern_arcade = download_verified_once(
    MODERN_ARCADE_URL,
    MODERN_ARCADE_DRIVE,
    MODERN_ARCADE_SHA256,
)

reference_a = ImageOps.fit(
    Image.open(real_church_arcade).convert("RGB"),
    (848, 480),
    method=Image.Resampling.LANCZOS,
    centering=(0.52, 0.50),
)
reference_b = ImageOps.fit(
    Image.open(modern_arcade).convert("RGB"),
    (848, 480),
    method=Image.Resampling.LANCZOS,
    centering=(0.50, 0.44),
)

local_a = RUNTIME_EXPERIMENT / "reference_a_real_church_arcade.png"
local_b = RUNTIME_EXPERIMENT / "reference_b_real_arcade.png"
reference_a.save(local_a, "PNG", optimize=True)
reference_b.save(local_b, "PNG", optimize=True)
atomic_publish_file(local_a, DRIVE_EXPERIMENT / local_a.name)
atomic_publish_file(local_b, DRIVE_EXPERIMENT / local_b.name)
atomic_write_json(
    DRIVE_EXPERIMENT / "reference_manifest.json",
    {
        "reference_a": {
            "role": "real combined Memorial Church, connected arcade, and foreground columns",
            "source": "Wikimedia Commons",
            "source_url": "https://commons.wikimedia.org/wiki/File:Stanford_University_Arches_with_Memorial_Church_in_the_background.jpg",
            "author": "Jawed",
            "license": "CC BY-SA 4.0",
            "download_sha256": REAL_CHURCH_ARCADE_SHA256,
            "crop_sha256": sha256_file(local_a),
        },
        "reference_b": {
            "role": "current Stanford Main Quad long arcade with Hoover Tower",
            "source": "Wikimedia Commons",
            "source_url": "https://commons.wikimedia.org/wiki/File:Stanford_University_in_2025_03.jpg",
            "author": "Christopher P. Michel (Cmichel67)",
            "captured": "2025-11-20",
            "license": "CC BY-SA 4.0",
            "download_sha256": MODERN_ARCADE_SHA256,
            "color_provenance": "native color photograph; no AI colorization",
            "crop_sha256": sha256_file(local_b),
        },
        "purpose": "local evaluation proof only; production licensing and color continuity remain review gates",
    },
)

sheet = Image.new("RGB", (1696, 520), "#111111")
sheet.paste(reference_a, (0, 0))
sheet.paste(reference_b, (848, 0))
draw = ImageDraw.Draw(sheet)
draw.rectangle((0, 480, 1696, 520), fill="#111111")
draw.text((12, 492), "A — real combined Church + arcade", fill="white")
draw.text((860, 492), "B — real 2025 Main Quad arcade (native color)", fill="white")
display(sheet)

NEGATIVE_BASE = (
    "drone, quadcopter, aircraft, helicopter, propeller, camera rig, filming equipment, boom, "
    "floating object, CGI, illustration, miniature, warped architecture, altered facade, duplicated arch, "
    "melting stone, morph, dissolve, fade, opacity transition, camera cut, jitter, flicker, text, watermark"
)

PROMPT_A = (
    "The camera begins nearly stationary at pedestrian height. It then trucks diagonally left and forward toward "
    "the already-visible nearest sandstone column while panning slightly left. The Memorial Church facade moves "
    "steadily toward the right side of the frame; nearby arches and column edges cross the frame faster than the "
    "distant church, creating layered lateral parallax. The movement accelerates smoothly, then brakes as the lens "
    "approaches within centimeters of the opaque sandstone column. During the final six frames, textured stone "
    "covers the entire image. Preserve the exact architecture, mosaic, arches, roofline, color, and daylight from "
    "the reference photograph. Photorealistic live-action footage at normal speed."
)

PROMPT_B = (
    "The camera begins nearly stationary in the real Stanford Main Quad courtyard shown in the photograph. It then "
    "trucks decisively left and slightly forward toward the nearest sandstone arcade column at the left edge while "
    "panning along the long row of arches. The closest column expands much faster than the receding arches, courtyard, "
    "and Hoover Tower, producing strong physical parallax while all architecture stays rigid and straight. The move "
    "accelerates smoothly, then brakes within centimeters of the opaque sandstone column. During the final six frames, "
    "textured stone covers the entire image. Preserve the exact native-color stonework, arches, tiled roofs, Hoover "
    "Tower, vegetation, spatial layout, overcast daylight, and camera perspective from the reference photograph. "
    "Photorealistic live-action footage at normal speed."
)


def candidate_valid(directory):
    manifest_path = directory / "manifest.json"
    if not manifest_path.is_file():
        return False
    try:
        manifest = json.loads(manifest_path.read_text())
        for name, record in manifest["artifacts"].items():
            path = directory / name
            if not path.is_file() or path.stat().st_size != record["bytes"] or sha256_file(path) != record["sha256"]:
                return False
        probe = probe_video(directory / "clip.mp4")
        return (probe["width"], probe["height"], probe["frames"]) == (848, 480, 73)
    except Exception:
        return False


def render_candidate(pipe, label, image, prompt, seed):
    drive_directory = DRIVE_EXPERIMENT / label / str(seed)
    runtime_directory = RUNTIME_EXPERIMENT / label / str(seed)
    if candidate_valid(drive_directory):
        runtime_directory.mkdir(parents=True, exist_ok=True)
        for name in ("clip.mp4", "contact_sheet.jpg", "final_frame.png"):
            shutil.copy2(drive_directory / name, runtime_directory / name)
        print("Restored", label, seed)
        return runtime_directory / "clip.mp4", drive_directory

    runtime_directory.mkdir(parents=True, exist_ok=True)
    generator = torch.Generator(device="cuda").manual_seed(seed)
    started = time.time()
    output = pipe(
        image=image,
        prompt=prompt,
        negative_prompt=NEGATIVE_BASE,
        num_frames=73,
        num_inference_steps=50,
        generator=generator,
        output_type="np",
    )
    frames = normalize_output(output)
    if len(frames) != 73:
        raise RuntimeError(f"{label} returned {len(frames)} frames")
    frames[0] = np.asarray(image, dtype=np.uint8)

    clip = runtime_directory / "clip.mp4"
    contact = runtime_directory / "contact_sheet.jpg"
    final_frame = runtime_directory / "final_frame.png"
    encode_video(frames, clip, crf=16)
    write_contact_sheet(frames, contact, f"{label} | seed {seed} | native 73 frames")
    Image.fromarray(frames[-1]).save(final_frame, "PNG", optimize=True)

    artifacts = {}
    for path in (clip, contact, final_frame):
        digest = atomic_publish_file(path, drive_directory / path.name)
        artifacts[path.name] = {"bytes": path.stat().st_size, "sha256": digest}
    manifest = {
        "status": "complete",
        "label": label,
        "seed": seed,
        "model": BASE_480_MODEL,
        "prompt": prompt,
        "negative_prompt": NEGATIVE_BASE,
        "native_frames": 73,
        "fps": 24,
        "rgb_retiming": False,
        "pixel_crossfade": False,
        "started_at_unix": started,
        "completed_at_unix": time.time(),
        "artifacts": artifacts,
        "license": "local evaluation only",
    }
    atomic_write_json(drive_directory / "manifest.json", manifest)
    return clip, drive_directory


model_directory = acquire_model(BASE_480_MODEL, "stanford-anchor-pair-base480")
pipe = load_hunyuan(model_directory, BASE_480_MODEL, "stanford-anchor-pair-base480")
if abs(float(pipe.guider.guidance_scale) - 6.0) > 1e-6:
    raise RuntimeError(f"Expected active CFG 6, found {pipe.guider.guidance_scale}")

try:
    clip_a, drive_a = render_candidate(pipe, "A_church_to_column", reference_a, PROMPT_A, 81003)
    display(Image.open(drive_a / "contact_sheet.jpg"))
    clip_b, drive_b = render_candidate(pipe, "B_arcade_to_column", reference_b, PROMPT_B, 82011)
    display(Image.open(drive_b / "contact_sheet.jpg"))
finally:
    dispose_pipeline(pipe)
    pipe = None

# Reverse B without interpolation, blending, motion blur, or parent-frame replacement.
reversed_b = RUNTIME_EXPERIMENT / "B_column_to_arcade_reversed.mp4"
subprocess.run(
    [
        "ffmpeg", "-y", "-v", "error", "-i", str(clip_b),
        "-vf", "reverse,setpts=PTS-STARTPTS", "-an", "-r", "24",
        "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(reversed_b),
    ],
    check=True,
)

joined = RUNTIME_EXPERIMENT / "stanford_anchor_pair_hardcut.mp4"
subprocess.run(
    [
        "ffmpeg", "-y", "-v", "error", "-i", str(clip_a), "-i", str(reversed_b),
        "-filter_complex", "[0:v]setpts=PTS-STARTPTS[a];[1:v]setpts=PTS-STARTPTS[b];[a][b]concat=n=2:v=1:a=0[v]",
        "-map", "[v]", "-an", "-r", "24", "-c:v", "libx264", "-preset", "slow", "-crf", "16",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(joined),
    ],
    check=True,
)


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


left = decode_frame(clip_a, 72)
right = decode_frame(reversed_b, 0)
seam_mae = float(np.abs(left.astype(np.float32) - right.astype(np.float32)).mean())
diagnostic = Image.new("RGB", (1696, 520), "#111111")
diagnostic.paste(Image.fromarray(left), (0, 0))
diagnostic.paste(Image.fromarray(right), (848, 0))
ddraw = ImageDraw.Draw(diagnostic)
ddraw.rectangle((0, 480, 1696, 520), fill="#111111")
ddraw.text((12, 492), "A final frame", fill="white")
ddraw.text((860, 492), f"reversed B first frame | seam MAE {seam_mae:.2f}", fill="white")
diagnostic_path = RUNTIME_EXPERIMENT / "column_seam_diagnostic.jpg"
diagnostic.save(diagnostic_path, "JPEG", quality=92)

final_artifacts = {}
for local_path in (reversed_b, joined, diagnostic_path):
    drive_path = DRIVE_EXPERIMENT / local_path.name
    digest = atomic_publish_file(local_path, drive_path)
    final_artifacts[local_path.name] = {
        "bytes": local_path.stat().st_size,
        "sha256": digest,
    }

atomic_write_json(
    DRIVE_EXPERIMENT / "experiment_report.json",
    {
        "status": "visual_review_required",
        "experiment_id": EXPERIMENT_ID,
        "model": BASE_480_MODEL,
        "frames_per_source_clip": 73,
        "fps": 24,
        "rgb_retiming": False,
        "pixel_crossfade": False,
        "seam_mae": seam_mae,
        "artifacts": final_artifacts,
        "acceptance_gate": (
            "Both source clips must end with at least two consecutive frames of 98–100% opaque sandstone coverage; "
            "the hard join must read as one column pass; Church and arcade geometry must remain recognizable."
        ),
        "license": "local evaluation only",
    },
)

# Re-read every final artifact from Drive and publish the success marker last.
for name, record in final_artifacts.items():
    persisted_path = DRIVE_EXPERIMENT / name
    if not persisted_path.is_file():
        raise RuntimeError(f"Final Drive artifact is missing: {persisted_path}")
    if persisted_path.stat().st_size != record["bytes"]:
        raise RuntimeError(f"Final Drive artifact size mismatch: {persisted_path}")
    if sha256_file(persisted_path) != record["sha256"]:
        raise RuntimeError(f"Final Drive artifact hash mismatch: {persisted_path}")

report_path = DRIVE_EXPERIMENT / "experiment_report.json"
success_path = DRIVE_EXPERIMENT / "_SUCCESS.json"
atomic_write_json(
    success_path,
    {
        "status": "complete_and_verified",
        "experiment_id": EXPERIMENT_ID,
        "completed_at_unix": time.time(),
        "experiment_report_sha256": sha256_file(report_path),
        "artifacts": final_artifacts,
    },
)
if json.loads(success_path.read_text(encoding="utf-8")).get("status") != "complete_and_verified":
    raise RuntimeError("Drive success marker verification failed")

display(diagnostic)
display(Video(str(joined), embed=True, width=848))
print("PERSISTED EXPERIMENT:", DRIVE_EXPERIMENT)
print("VERIFIED SUCCESS MARKER:", success_path)
print("The temporary local model snapshot will be deleted when Colab disconnects:", model_directory)
disconnect_runtime_safely("experiment completed and Drive artifacts verified")
