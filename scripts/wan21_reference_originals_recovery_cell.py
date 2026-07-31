# Recovery cell for a live Wan FLF2V Colab runtime after a Wikimedia thumbnail hash mismatch.
# Paste this over the failed reference-acquisition cell and run it once.

REFERENCES["first"].update({
    "filename": "stanford_church_arcade_real_original.jpg",
    "url": "https://upload.wikimedia.org/wikipedia/commons/b/b6/Stanford_University_Arches_with_Memorial_Church_in_the_background.jpg",
    "sha256": "17601f44f530af14e7f25a1d3a8d0894e81494d98d68eec6bc5c71546dff4a51",
})
REFERENCES["last"].update({
    "filename": "stanford_arches_main_quad_real_original.jpg",
    "url": "https://upload.wikimedia.org/wikipedia/commons/0/0a/Stanford_University_Arches_of_Main_Quad.jpg",
    "sha256": "65205f306652e41c31b91d7bccb61c06f40edd574b8e007dd3f4fdcd0a49b864",
})
STABLE_CONFIG["references"] = REFERENCES
CONFIG_FINGERPRINT = hashlib.sha256(
    json.dumps(STABLE_CONFIG, sort_keys=True, separators=(",", ":")).encode()
).hexdigest()


def download_verified(record, destination):
    destination = Path(destination)
    if destination.is_file() and sha256_file(destination) == record["sha256"]:
        return destination
    last_error = None
    for attempt in range(5):
        try:
            request = urllib.request.Request(
                record["url"],
                headers={"User-Agent": "Eric-Wu-portfolio-reference/1.0"},
            )
            with urllib.request.urlopen(request, timeout=180) as response:
                payload = response.read()
            actual = hashlib.sha256(payload).hexdigest()
            if actual != record["sha256"]:
                raise RuntimeError(
                    f"Reference hash mismatch: expected {record['sha256']}, received {actual}, bytes={len(payload)}"
                )
            temporary = destination.with_name(destination.name + f".part-{uuid.uuid4().hex}")
            temporary.write_bytes(payload)
            os.replace(temporary, destination)
            return destination
        except Exception as error:
            last_error = error
            if attempt < 4:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Original reference download failed after retries: {last_error}")


ENDPOINTS = {}
provenance = {}
for role, record in REFERENCES.items():
    drive_original = download_verified(record, DRIVE_INPUTS / record["filename"])
    image = ImageOps.fit(
        Image.open(drive_original).convert("RGB"),
        (WIDTH, HEIGHT),
        method=Image.Resampling.LANCZOS,
        centering=tuple(record["centering"]),
    )
    local_endpoint = RUNTIME_INPUTS / f"{role}_endpoint_1280x720.png"
    drive_endpoint = DRIVE_EXPERIMENT / local_endpoint.name
    image.save(local_endpoint, "PNG", optimize=True)
    endpoint_digest = atomic_publish_file(local_endpoint, drive_endpoint)
    ENDPOINTS[role] = image
    provenance[role] = {
        **{key: value for key, value in record.items() if key != "centering"},
        "endpoint_sha256": endpoint_digest,
        "endpoint_size": [WIDTH, HEIGHT],
    }

atomic_write_json(DRIVE_EXPERIMENT / "reference_provenance.json", provenance)
sheet = Image.new("RGB", (1280, 760), "#111111")
sheet.paste(ENDPOINTS["first"].resize((640, 360), Image.Resampling.LANCZOS), (0, 0))
sheet.paste(ENDPOINTS["last"].resize((640, 360), Image.Resampling.LANCZOS), (640, 0))
draw = ImageDraw.Draw(sheet)
draw.text((12, 370), "FIRST — Memorial Church framed by arcade", fill="white")
draw.text((652, 370), "LAST — exact long-arcade composition", fill="white")
draw.text((12, 420), "Path: track right + foreground column parallax + gradual turn right into corridor", fill="white")
sheet_path = RUNTIME_EXPERIMENT / "first_last_endpoint_sheet.jpg"
sheet.save(sheet_path, "JPEG", quality=93, optimize=True)
atomic_publish_file(sheet_path, DRIVE_EXPERIMENT / sheet_path.name)
display(sheet)
print("Recovered verified original references. New configuration:", CONFIG_FINGERPRINT)
