from math import ceil, floor
from io import BytesIO
from pathlib import Path
import fitz
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.colors import black
from PyPDF2 import PdfMerger, PdfReader

def _calc_layout(paper_width_mm, paper_height_mm, kupon_width_mm, kupon_height_mm, crop_mark_extra_mm=5, outer_gap_mm=3, orientation_label="Normal"):
    effective_width = paper_width_mm - 2 * (outer_gap_mm + crop_mark_extra_mm)
    effective_height = paper_height_mm - 2 * (outer_gap_mm + crop_mark_extra_mm)
    cols = max(1, floor(effective_width / kupon_width_mm))
    rows = max(1, floor(effective_height / kupon_height_mm))
    total = cols * rows
    used_area = cols * kupon_width_mm * rows * kupon_height_mm
    paper_area = max(1, paper_width_mm * paper_height_mm)
    efficiency = (used_area / paper_area) * 100
    leftover_width = effective_width - (cols * kupon_width_mm)
    leftover_height = effective_height - (rows * kupon_height_mm)
    return {
        "cols": cols,
        "rows": rows,
        "total": total,
        "orientation_label": orientation_label,
        "kupon_width_used_mm": round(kupon_width_mm, 2),
        "kupon_height_used_mm": round(kupon_height_mm, 2),
        "efficiency_percent": round(efficiency, 2),
        "leftover_width_mm": round(leftover_width, 2),
        "leftover_height_mm": round(leftover_height, 2),
    }

def analyze_pdf_v2(input_pdf, page_width_mm=325, page_height_mm=485, crop_mark_extra_mm=5, outer_gap_mm=3, allow_rotate=True):
    doc = fitz.open(input_pdf)
    if len(doc) == 0:
        raise ValueError("PDF kosong")
    page = doc[0]
    original_width_mm = page.rect.width * 25.4 / 72
    original_height_mm = page.rect.height * 25.4 / 72
    normal = _calc_layout(page_width_mm, page_height_mm, original_width_mm, original_height_mm, crop_mark_extra_mm, outer_gap_mm, "Normal")
    rotated = _calc_layout(page_width_mm, page_height_mm, original_height_mm, original_width_mm, crop_mark_extra_mm, outer_gap_mm, "Rotated 90°")
    candidates = [normal, rotated] if allow_rotate else [normal]
    best = sorted(candidates, key=lambda x: (x["total"], x["efficiency_percent"], -(x["leftover_width_mm"] + x["leftover_height_mm"])), reverse=True)[0]
    return {
        "kupon_width_mm": round(original_width_mm, 2),
        "kupon_height_mm": round(original_height_mm, 2),
        "paper_width_mm": page_width_mm,
        "paper_height_mm": page_height_mm,
        "normal": normal,
        "rotated": rotated,
        "best": best,
    }

def generate_coupon_layout(input_pdf, output_folder, page_width_mm=325, page_height_mm=485, cols=3, rows=11, crop_mark_extra_mm=5, kupon_per_file=500, use_cropmark=True):
    doc = fitz.open(input_pdf)
    if len(doc) == 0:
        raise ValueError("PDF kosong")
    if cols < 1 or rows < 1:
        raise ValueError("Kolom dan baris minimal 1")
    if kupon_per_file < 1:
        raise ValueError("Kupon per file minimal 1")

    original_width_mm = doc[0].rect.width * 25.4 / 72
    original_height_mm = doc[0].rect.height * 25.4 / 72

    def fits(w, h):
        return (cols * w <= page_width_mm) and (rows * h <= page_height_mm)

    rotate_item = False
    kupon_width_mm = original_width_mm
    kupon_height_mm = original_height_mm

    if not fits(original_width_mm, original_height_mm) and fits(original_height_mm, original_width_mm):
        rotate_item = True
        kupon_width_mm = original_height_mm
        kupon_height_mm = original_width_mm

    total_width = cols * kupon_width_mm
    total_height = rows * kupon_height_mm

    if total_width > page_width_mm or total_height > page_height_mm:
        raise ValueError("Ukuran grid kupon melebihi ukuran kertas. Coba kurangi kolom/baris.")

    x_margin = (page_width_mm - total_width) / 2
    y_margin = (page_height_mm - total_height) / 2
    out = Path(output_folder)
    out.mkdir(parents=True, exist_ok=True)

    def draw_cropmark(c):
        mark_len = crop_mark_extra_mm * mm
        gap = 3 * mm
        c.setStrokeColor(black)
        c.setLineWidth(0.5)
        start_x = x_margin * mm
        start_y = (page_height_mm - y_margin - total_height) * mm
        end_x = start_x + total_width * mm
        end_y = start_y + total_height * mm
        for i in range(cols + 1):
            x = start_x + i * kupon_width_mm * mm
            c.line(x, start_y - gap - mark_len, x, start_y - gap)
            c.line(x, end_y + gap, x, end_y + gap + mark_len)
        for j in range(rows + 1):
            y = start_y + j * kupon_height_mm * mm
            c.line(start_x - gap - mark_len, y, start_x - gap, y)
            c.line(end_x + gap, y, end_x + gap + mark_len, y)

    total_kupon = len(doc)
    positions_per_page = cols * rows
    batches = ceil(total_kupon / kupon_per_file)
    generated_files = []

    for batch in range(batches):
        start_index = batch * kupon_per_file
        end_index = min(start_index + kupon_per_file, total_kupon)
        pages_needed = ceil((end_index - start_index) / positions_per_page)
        buffers = [BytesIO() for _ in range(pages_needed)]
        canvases = [canvas.Canvas(buf, pagesize=(page_width_mm * mm, page_height_mm * mm)) for buf in buffers]
        counter = start_index

        for pos in range(positions_per_page):
            row = pos // cols
            col = pos % cols
            x = (x_margin + col * kupon_width_mm) * mm
            y = (page_height_mm - y_margin - (row + 1) * kupon_height_mm) * mm
            for page_num in range(pages_needed):
                if counter >= end_index:
                    break
                page = doc.load_page(counter)
                matrix = fitz.Matrix(200 / 72, 200 / 72)
                if rotate_item:
                    matrix = matrix.prerotate(90)
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                temp_img = out / f"temp_{counter+1:06}.png"
                pix.save(str(temp_img))
                canvases[page_num].drawImage(str(temp_img), x, y, width=kupon_width_mm * mm, height=kupon_height_mm * mm, preserveAspectRatio=True, mask="auto")
                temp_img.unlink(missing_ok=True)
                counter += 1

        for c in canvases:
            if use_cropmark:
                draw_cropmark(c)
            c.showPage()
            c.save()

        temp_pdfs = []
        for i, buf in enumerate(buffers):
            temp_pdf = out / f"temp_batch_{batch+1}_page_{i+1}.pdf"
            temp_pdf.write_bytes(buf.getvalue())
            temp_pdfs.append(temp_pdf)

        merger = PdfMerger()
        for temp_pdf in temp_pdfs:
            merger.append(PdfReader(str(temp_pdf), "rb"))
        output_filename = f"Kupon_{start_index+1:06}-{end_index:06}.pdf"
        merger.write(str(out / output_filename))
        merger.close()

        for temp_pdf in temp_pdfs:
            temp_pdf.unlink(missing_ok=True)
        generated_files.append(output_filename)

    return {"success": True, "generated_files": generated_files, "output_folder": str(out), "total_input_pages": total_kupon, "rotate_item": rotate_item}
