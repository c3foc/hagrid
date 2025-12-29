from reportlab.lib.units import mm
from hagrid import settings
from io import BytesIO

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import black
from reportlab.platypus import Paragraph
from reportlab.pdfbase.ttfonts import TTFont

import logging
import qrcode
import os.path


logger = logging.getLogger(__name__)


NOTES_STYLE = ParagraphStyle(
    "notesstyle",
    fontSize=14,
    leading=18,
    fontName="SpaceMono",
)

FONTS_DIR = os.path.join(
    os.path.dirname(__file__),
    "..",
    "static",
    "fonts",
)
pdfmetrics.registerFont(
    TTFont(
        "SpaceMono",
        os.path.join(
            FONTS_DIR,
            "space-mono",
            "SpaceMono-Regular.ttf",
        ),
    )
)
pdfmetrics.registerFont(
    TTFont(
        "SpaceMonoBold",
        os.path.join(
            FONTS_DIR,
            "space-mono",
            "SpaceMono-Bold.ttf",
        ),
    )
)
pdfmetrics.registerFontFamily("SpaceMono", normal="SpaceMono", bold="SpaceMonoBold")


class Document:
    def __init__(self, filename: str):
        self.bytes_buffer = BytesIO()

        # create canvas and set some defaults
        self.canvas = canvas.Canvas(self.bytes_buffer, pagesize=A4, pageCompression=0)
        self.canvas.setTitle(filename)
        self.canvas.setFont("SpaceMono", 12)
        self.canvas.setFillColor(black)

        # track dimensions and cursor position
        self.page = 0
        self.ml = self.mt = self.mr = self.mb = 40
        self.x = 0
        self.y = 0
        self.w, self.h = A4

        self.new_page()

    def get_text_width(self, text: str):
        return pdfmetrics.stringWidth(text, "Helvetica", 12)

    def new_page(self):
        if self.page >= 1:
            self.canvas.showPage()

        self.page += 1
        self.y = self.h - self.mt
        self.x = self.ml

    def wrap_up(self):
        self.canvas.showPage()
        self.canvas.save()

        pdf_bytes = self.bytes_buffer.getvalue()
        self.bytes_buffer.close()

        # cleanup
        self.canvas = None
        self.bytes_buffer = None

        return pdf_bytes


def generate_qr_code(link: str):
    qr = qrcode.QRCode(
        version=None,
        # error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=20,
        border=4,
    )
    qr.add_data(link)
    qr.make(fit=True)
    return qr.make_image()


def generate_access_code_pdf(request, access_codes, filename: str):
    doc = Document(filename)

    # Render QR Code next to the comment
    for access_code in access_codes:
        url = "{}{}".format(
            settings.SITE_URL,
            access_code.get_absolute_url()
        )
        qr_image = generate_qr_code(url)
        qr_code_size = 50 * mm
        if doc.y < qr_code_size + doc.mb:
            doc.new_page()
        doc.canvas.drawInlineImage(
            qr_image,
            doc.x,
            doc.y - qr_code_size,
            qr_code_size,
            qr_code_size,
        )
        doc.canvas.rect(
            doc.x,
            doc.y - qr_code_size,
            qr_code_size,
            qr_code_size,
            fill=0,
        )

        html = "<font size=20>Count me!</font><br /><br />"

        products = access_code.products.all()
        if products:
            html += "<b>Products:</b> "
            html += ", ".join(map(str, products))
            html += "<br />"

        sizegroups = access_code.sizegroups.all()
        if sizegroups:
            html += "<b>Size Groups:</b> "
            html += ", ".join(map(str, sizegroups))
            html += "<br />"

        sizes = access_code.sizes.all()
        if sizes:
            html += "<b>Sizes:</b> "
            html += ", ".join(map(str, sizes))
            html += "<br />"

        if not products and not sizegroups and not sizes:
            html += "<b>All items</b><br />"
        if access_code.as_queue:
            html += "<b>VIA QUEUE</b><br />"

        text = Paragraph(html, style=NOTES_STYLE)
        _, text_height = text.wrap(
            doc.w - qr_code_size - 20 - doc.mr - doc.ml,
            10000000,
        )
        text.drawOn(doc.canvas, doc.x + qr_code_size + 20, doc.y - text_height)

        doc.y = min(doc.y - text_height, doc.y - qr_code_size) - 20 * mm

    return doc.wrap_up()
