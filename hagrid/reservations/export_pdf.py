from io import BytesIO

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle

import datetime
import logging
import qrcode
import time

from .models import Reservation, ReservationPosition, ReservationPart
from hagrid.products.models import Variation

logger = logging.getLogger(__name__)

NOTES_STYLE = ParagraphStyle('notesstyle', fontSize=11)
ARTICLE_NOTES_STYLE = ParagraphStyle('articlestyle', fontSize=11)
INFO_STYLE = ParagraphStyle(
        'infostyle', fontSize=9,
        border_color="#000000",
        border_width=1,
        border_padding=(7, 2, 20),
        word_wrap='LTR',
        border_radius=None)


class Document:

    page = 0
    w = 0
    h = 0
    right_inset = 75
    bytes_buffer = None
    canvas: canvas = None
    side_label: str = ""
    watermark: str = ""
    cursor_y = 0
    cursor_x = 0

    def __init__(self, filename: str, title: str, author: str, subject: str, side_label=""):
        self.page = 0
        self.watermark = ""
        self.bytes_buffer = BytesIO()
        self.canvas = canvas.Canvas(self.bytes_buffer, pagesize=A4, pageCompression=0)
        self.canvas.setTitle(title)
        self.w, self.h = A4
        self.canvas.setAuthor(author)
        self.canvas.setSubject(subject)
        self.side_label = side_label
        self.new_page()

    def bookmark_page(self, text: str):
        self.canvas.addOutlineEntry(text, "p" + str(self.page))
        self.canvas.bookmarkPage("p" + str(self.page))

    def render_page_hint(self):
        self.canvas.drawString(self.w - 75, self.h - 35, "Page " + str(self.page))

    def apply_watermark(self):
        self.canvas.setFont("Helvetica", 30)
        self.canvas.rotate(45)
        self.canvas.setFillColorRGB(225, 225, 225, alpha=0.5)
        self.canvas.drawString(75, 75, self.watermark)
        self.canvas.setFillColorRGB(255, 255, 255, alpha=1.0)
        self.canvas.rotate(360 - 45)
        self.canvas.setFont("Helvetica", 14)

    def set_watermark(self, watermark):
        self.watermark = str(watermark)
        self.apply_watermark()

    def get_text_width(self, text: str):
        return pdfmetrics.stringWidth(text, "Helvetica", 14)

    def new_page(self, bookmark=None):
        self.canvas.showPage()
        self.right_inset = 45
        self.page += 1
        self.cursor_y = self.h - 45
        self.cursor_x = 45
        self.canvas.setFont("Helvetica", 9)
        self.canvas.rotate(90)
        self.canvas.drawString(35, -25, self.side_label)
        self.canvas.rotate(-270)
        self.canvas.setFont("Helvetica", 14)
        if bookmark is not None:
            self.bookmark_page(bookmark)
        self.apply_watermark()
        page_number_text = "Page " + str(self.page)
        self.canvas.drawString(self.w - self.right_inset - self.get_text_width(page_number_text), 50, page_number_text)

    def wrap_up(self):
        self.canvas.showPage()
        self.canvas.save()
        pdf_bytes = self.bytes_buffer.getvalue()
        self.bytes_buffer.close()
        self.canvas = None
        self.bytes_buffer = None
        return pdf_bytes


def timestamp(filestr=True):
    if filestr:
        return datetime.datetime.fromtimestamp(time.time()).strftime('%d_%m_%Y__%H_%M_Uhr')
    else:
        return datetime.datetime.fromtimestamp(time.time()).strftime('%m/%d/%Y %H:%M:%S Uhr')


def generate_qr_code(link: str):
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=30, border=4)
    qr.add_data(link)
    qr.make(fit=True)
    return qr.make_image()


def generate_collection_list(reservation: Reservation):
    variation_dict = {}
    for res_part in ReservationPart.objects.all().filter(reservation=reservation):
        for p in ReservationPosition.objects.all().filter(part=res_part):
            if p.variation in variation_dict:
                variation_dict[p.variation] += p.amount
            else:
                variation_dict[p.variation] = p.amount
    article_list = []
    for entry in variation_dict:
        article_list.append((entry, variation_dict[entry]))
    return sorted(article_list, key=lambda t: t[0].__str__())


def render_collection_table_header(d: Document):
    d.canvas.line(d.cursor_x, d.cursor_y, d.w - canvas.right_inset, d.cursor_y)
    d.canvas.line(d.cursor_x, d.cursor_y, d.cursor_x, d.cursor_y - 15)
    d.canvas.line(d.w - canvas.right_inset, d.cursor_y, d.w - canvas.right_inset, d.cursor_y - 15)
    d.canvas.line(d.cursor_x, d.cursor_y - 15, d.w - canvas.right_inset, d.cursor_y - 15)

    d.canvas.drawString(d.cursor_x + 10, d.cursor_y - 10, "Article")
    d.canvas.drawString(d.cursor_x + 110, d.cursor_y - 10, "Quantity")
    d.canvas.drawString(d.cursor_x + 190, d.cursor_y - 10, "Notes?")
    d.canvas.drawString(A4[0] - 61, d.cursor_y - 10, "X")

    d.canvas.line(d.cursor_x + 5, d.cursor_y, d.cursor_x + 5, d.cursor_y - 15)
    d.canvas.line(d.cursor_x + 105, d.cursor_y, d.cursor_x + 105, d.cursor_y - 15)
    d.canvas.line(d.cursor_x + 185, d.cursor_y, d.cursor_x + 185, d.cursor_y - 15)

    d.cursor_y -= 15


def render_collection_list_entry(pos: Variation, amount: int, d: Document):
    # Draw table boxes
    d.canvas.line(d.cursor_x, d.cursor_y, d.w - canvas.right_inset, d.cursor_y)
    d.canvas.line(d.cursor_x, d.cursor_y, d.cursor_x, d.cursor_y - 15)
    d.canvas.line(d.w - canvas.right_inset, d.cursor_y, d.w - canvas.right_inset, d.cursor_y - 15)
    d.canvas.line(d.cursor_x, d.cursor_y - 15, d.w - canvas.right_inset, d.cursor_y - 15)

    # Draw table separation lines
    d.canvas.line(d.cursor_x + 5, d.cursor_y, d.cursor_x + 5, d.cursor_y - 15)
    d.canvas.line(d.cursor_x + 105, d.cursor_y, d.cursor_x + 105, d.cursor_y - 15)
    d.canvas.line(d.cursor_x + 185, d.cursor_y, d.cursor_x + 185, d.cursor_y - 15)

    # Draw hollow rect for package checking
    d.canvas.line(d.w - d.right_inset - 2, d.cursor_y - 2, d.w - d.right_inset - 2, d.cursor_y - 13)
    d.canvas.line(d.w - d.right_inset - 13, d.cursor_y - 2, d.w - d.right_inset - 13, d.cursor_y - 13)
    d.canvas.line(d.w - d.right_inset - 13, d.cursor_y - 2, d.w - d.right_inset - 2, d.cursor_y - 2)
    d.canvas.line(d.w - d.right_inset - 13, d.cursor_y - 13, d.w - d.right_inset - 2, d.cursor_y - 13)

    d.canvas.drawString(d.cursor_x + 10, d.cursor_y - 13, str(pos))
    d.canvas.drawString(d.cursor_x + 110, d.cursor_y - 10, str(amount))
    d.cursor_y -= 15


def render_collection_list(l, d: Document):
    render_collection_table_header(d)
    for request in l:
        if d.cursor_y < (75 + 15):
            d.new_page()
            render_collection_table_header(d)
        render_collection_list_entry(request[0], request[1], d)


def render_reservation(r: Reservation, d: Document):
    if r.state == r.STATE_SUBMITTED:
        d.set_watermark("")
    else:
        d.set_watermark(str(r.state))
    articles = generate_collection_list(r)
    render_collection_list(articles, d)


def export_invoices_as_pdf(reservations, filename: str, username = "nobody", title = "C3FOC - Reservations"):
    """
    This method turns an array of reservations into a PDF file and returns its bytes.

    Parameters
    ----------
    reservations: [Reservation]
        An array containing the reservations that should receive an invoice

    filename: str
        The original file name

    username: str
        Optional. But recommended. The username of the user creating this report.

    title: str
        Optional. The title of the PDF being generated.

    Returns
    -------
    bytes:
        The bytes of the PDF file
    """
    logger.debug("Exporting reservations: " + str(reservations))
    d: Document = Document(filename, title, "The robots in slavery by " + str(username),
            "This document, originally created at " + timestamp(filestr=False) + ", contains the requested reservations")
    reservation_counter = 0
    for r in reservations:
        reservation_counter += 1

        # Test for document appending
        if reservation_counter != 1:
            d.page = 0
            d.new_page()
        
        render_reservation(r, d)
    return d.wrap_up()
