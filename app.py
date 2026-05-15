from flask import Flask, render_template, send_file, request, jsonify
from flask_cors import CORS
from xhtml2pdf import pisa
from io import BytesIO
import os
import re
from datetime import datetime

app = Flask(__name__)
CORS(app)

@app.route("/")
def hello():
    return "PDF service is alive"

@app.route("/pdf/test", methods=["GET", "POST"])
def pdf_test():
    if request.method == "POST":
        data = request.get_json() or {}
    else:
        data = request.args.to_dict()
    
    show_name = data.get("show_name", "Untitled Show")
    venue = data.get("venue", "Unknown Venue")
    
    html = render_template("test.html", show_name=show_name, venue=venue)
    pdf_buffer = BytesIO()
    pisa.CreatePDF(html, dest=pdf_buffer)
    pdf_buffer.seek(0)
    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="test.pdf"
    )

@app.route("/pdf/pull-list", methods=["POST"])
def pdf_pull_list():
    data = request.get_json() or {}
    
    show_name = data.get("show_name", "Untitled Show")
    document_date = data.get("document_date", "")
    items = data.get("items", [])
    
    if not items:
        return jsonify({"error": "No items provided"}), 400
    
    items_by_category = {}
    for item in items:
        category = item.get("category", "Uncategorized")
        if category not in items_by_category:
            items_by_category[category] = []
        items_by_category[category].append(item)
    
    html = render_template(
        "pull_list.html",
        show_name=show_name,
        document_date=document_date,
        items_by_category=items_by_category
    )
    
    pdf_buffer = BytesIO()
    pisa.CreatePDF(html, dest=pdf_buffer)
    pdf_buffer.seek(0)
    
    safe_name = show_name.replace(" ", "_").lower()
    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"{safe_name}_pull_list.pdf"
    )

@app.route("/pdf/tech-spec", methods=["POST"])
def pdf_tech_spec():
    data = request.get_json() or {}

    show_name = data.get("show_name", "Untitled Show")
    document_date = data.get("document_date", "")
    items = data.get("items", [])

    if not items:
        return jsonify({"error": "No items provided"}), 400

    items_by_category = {}
    for item in items:
        category = item.get("category", "Uncategorized")
        if category not in items_by_category:
            items_by_category[category] = []
        items_by_category[category].append(item)

    html = render_template(
        "tech_spec.html",
        show_name=show_name,
        document_date=document_date,
        items_by_category=items_by_category
    )

    pdf_buffer = BytesIO()
    pisa.CreatePDF(html, dest=pdf_buffer)
    pdf_buffer.seek(0)

    safe_name = show_name.replace(" ", "_").lower()
    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"{safe_name}_tech_spec.pdf"
    )


# ═══════════════════════════════════════
# SCREENSHOT TO PDF
# ═══════════════════════════════════════

# Reject base64 payloads bigger than this to protect the service from being
# DoS'd by enormous images. 12 MB of base64 ~= 9 MB binary image, which is
# more than any screenshot needs.
MAX_IMAGE_B64_BYTES = 12 * 1024 * 1024

# Only accept the image formats xhtml2pdf is known to handle reliably.
_DATA_URI_RX = re.compile(
    r"^data:image/(?P<mime>png|jpeg|jpg|gif);base64,(?P<data>[A-Za-z0-9+/=\s]+)$",
    re.IGNORECASE
)


def _safe_filename(s, fallback="screenshot"):
    """Strip filesystem-unsafe characters, collapse whitespace, cap length."""
    if not s:
        return fallback
    cleaned = re.sub(r'[/\\?%*:|"<>]', "", s).strip()
    cleaned = re.sub(r"\s+", "_", cleaned)
    cleaned = cleaned[:80]
    return cleaned or fallback


@app.route("/pdf/screenshot", methods=["POST"])
def pdf_screenshot():
    data = request.get_json() or {}

    title = (data.get("title") or "").strip() or "Untitled Screenshot"
    caption = (data.get("caption") or "").strip()
    image_data = (data.get("image_data") or "").strip()

    if not image_data:
        return jsonify({"error": "No image_data provided"}), 400

    # Reject payloads that are too large before doing further work.
    if len(image_data) > MAX_IMAGE_B64_BYTES:
        return jsonify({"error": "Image too large; please use a smaller screenshot"}), 413

    # Validate that the image is a recognized data URI in a format xhtml2pdf
    # supports. This prevents the renderer from silently dropping the image
    # or, worse, raising an opaque error during PDF generation.
    if not _DATA_URI_RX.match(image_data):
        return jsonify({
            "error": "image_data must be a PNG, JPEG, or GIF data URI "
                     "(e.g. 'data:image/png;base64,...')"
        }), 400

    document_date = data.get("document_date") or datetime.now().strftime(
        "%B %-d, %Y at %-I:%M %p"
    )

    html = render_template(
        "screenshot.html",
        title=title,
        caption=caption,
        image_data=image_data,
        document_date=document_date,
    )

    # PIL raises OSError on malformed image data (e.g. corrupted base64 or
    # a header that claims PNG but contains different bytes). Catch it here
    # rather than letting Flask return a generic 500, since the client can
    # act on a clear error message.
    pdf_buffer = BytesIO()
    try:
        result = pisa.CreatePDF(html, dest=pdf_buffer)
    except (OSError, ValueError) as exc:
        return jsonify({
            "error": "Could not render image — file may be corrupted or in an "
                     "unsupported format. Try copying the screenshot again.",
            "detail": str(exc),
        }), 400
    if result.err:
        return jsonify({"error": "PDF generation failed"}), 500
    pdf_buffer.seek(0)

    safe_name = _safe_filename(title)
    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"{safe_name}.pdf"
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
