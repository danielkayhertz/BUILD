import shutil, json, zipfile, pathlib, re

SRC = pathlib.Path(r"C:\Users\bpi\Downloads\PDFs-20260527T234638Z-3-001\PDFs")
DEST = pathlib.Path(__file__).parent / "pdfs"

manifest = []

for chamber, label in (("House", "lower"), ("Senate", "upper")):
    src_dir = SRC / chamber
    dst_dir = DEST / chamber.lower()
    pdf_count = sum(1 for _ in src_dir.glob("*.pdf"))
    assert pdf_count > 0, f"No PDFs found in {src_dir}"
    if dst_dir.exists():
        shutil.rmtree(dst_dir)
    dst_dir.mkdir(parents=True, exist_ok=True)
    for f in sorted(src_dir.glob("*.pdf")):
        dest_name = f.name.lower()
        assert re.match(r'^il-[lu]-\d{3}\.pdf$', dest_name), f"Unexpected filename: {f.name}"
        dst = dst_dir / dest_name
        shutil.copy2(f, dst)
        district_num = int(dest_name.split('-')[2].split('.')[0])
        manifest.append({
            "chamber": chamber.lower(),
            "org_classification": label,
            "district": district_num,
            "filename": dest_name,
            "size": dst.stat().st_size
        })

manifest.sort(key=lambda x: (x["chamber"], x["district"]))
(DEST / "manifest.json").write_text(json.dumps(manifest, indent=2))

zip_path = DEST / "all-district-one-pagers.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for entry in manifest:
        f = DEST / entry["chamber"] / entry["filename"]
        zf.write(f, f"{entry['chamber']}/{entry['filename']}")

print(f"Done. {len(manifest)} PDFs copied.")
print(f"ZIP: {zip_path} ({zip_path.stat().st_size / 1_000_000:.1f} MB)")
print("Upload the ZIP to a GitHub Release using the 'Attach binaries' drop zone.")
