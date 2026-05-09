from flask import Flask, render_template, send_file
from xhtml2pdf import pisa
from io import BytesIO
import os

app = Flask(__name__)

@app.route("/")
def hello():
    return "PDF service is alive"

@app.route("/pdf/test")
def pdf_test():
    html = render_template("test.html")
    pdf_buffer = BytesIO()
    pisa.CreatePDF(html, dest=pdf_buffer)
    pdf_buffer.seek(0)
    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="test.pdf"
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

