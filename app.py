from flask import Flask, render_template, send_file, request, jsonify
from xhtml2pdf import pisa
from io import BytesIO
import os

app = Flask(__name__)

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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)