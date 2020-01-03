from collections import Counter

from django.urls import reverse
from django.utils.text import slugify
from hagrid import settings
from io import BytesIO

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import black

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
    ready = False

    def __init__(self, filename: str, title: str, author: str, subject: str, side_label=""):
        self.page = 0
        self.ready = False
        self.watermark = ""
        self.bytes_buffer = BytesIO()
        self.canvas = canvas.Canvas(self.bytes_buffer, pagesize=A4, pageCompression=0)
        self.canvas.setTitle(title)
        self.w, self.h = A4
        self.canvas.setAuthor(author)
        self.canvas.setSubject(subject)
        self.side_label = side_label
        self.new_page()
        self.ready = True

    def bookmark_page(self, text: str):
        self.canvas.addOutlineEntry(text, "p" + str(self.page))
        self.canvas.bookmarkPage("p" + str(self.page))

    def render_page_hint(self):
        page_text = "Page " + str(self.page)
        self.canvas.drawString(self.w - 15 - self.get_text_width(page_text), self.h - 35, page_text)

    def apply_watermark(self):
        self.canvas.setFont("Helvetica", 30)
        self.canvas.rotate(45)
        self.canvas.setFillColorRGB(128, 128, 128, alpha=0.5)
        self.canvas.drawString(-75, 75, self.watermark)
        self.canvas.setFillColorRGB(0, 0, 0, alpha=1.0)
        self.canvas.rotate(360 - 45)
        self.canvas.setFont("Helvetica", 14)

    def set_watermark(self, watermark):
        self.watermark = str(watermark)
        self.apply_watermark()

    def get_text_width(self, text: str, text_size = 14):
        return pdfmetrics.stringWidth(text, "Helvetica", text_size)

    def new_page(self, bookmark=None):
        if self.ready:
            self.canvas.showPage()
        self.right_inset = 45
        self.page += 1
        self.cursor_y = self.h - 45
        self.cursor_x = 45
        self.canvas.setFont("Helvetica", 9)
        self.canvas.rotate(90)
        self.canvas.drawString(35, -25, self.side_label)
        self.canvas.rotate(270)
        self.canvas.setFont("Helvetica", 14)
        if bookmark is not None:
            self.bookmark_page(bookmark)
        self.apply_watermark()
        page_number_text = "Page " + str(self.page)
        self.canvas.drawString(self.w - self.right_inset - self.get_text_width(page_number_text), 50, page_number_text)
        self.canvas.setFillColorRGB(128, 128, 128, alpha=1.0)

    def wrap_up(self):
        self.canvas.showPage()
        self.canvas.save()
        pdf_bytes = self.bytes_buffer.getvalue()
        self.bytes_buffer.close()
        self.canvas = None
        self.bytes_buffer = None
        return pdf_bytes


def timestamp(filestr=True):
    timestring: str = str(datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S'))
    if filestr:
        return slugify(timestring)
    else:
        return timestring


def generate_qr_code(link: str):
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=30, border=4)
    qr.add_data(link)
    qr.make(fit=True)
    return qr.make_image()


def generate_collection_list(reservation: Reservation, distinct_required = False):
    groups = []
    titles = []

    sections = []

    if distinct_required:
        for part in reservation.parts.all():
            sections.append([part])
            titles.append("packing list for part {0}:".format(str(part.title)))
    else:
        sections = [reservation.parts.all()]
        titles.append("packing list:")

    for part in sections:
        variation_dict = Counter()
        for reservation_part in part:
            for position in reservation_part.positions.all():
                variation_dict[position.variation] += position.amount
        article_list = []
        for entry in variation_dict:
            article_list.append((entry, variation_dict[entry]))
        groups.append(sorted(article_list, key=lambda t: t[0].__str__()))

    return groups, titles


def render_invoice_header(r: Reservation, d: Document):
    # render reservation header
    d.canvas.setFillColor(black)
    d.canvas.setFont("Helvetica", 14)
    d.canvas.drawString(d.cursor_x, d.cursor_y, "Main reservation [" + str(r.id) + "] of " + str(r.team_name))
    d.canvas.setFont("Helvetica", 11)
    d.cursor_y -= 30
    
    # Render reservation comment
    text = Paragraph(r.comment.replace("\n", "<br />"), style=NOTES_STYLE)
    textwidth, textheight = text.wrapOn(d.canvas, d.w - 200, d.h - 250)
    text.drawOn(d.canvas, d.cursor_x, d.cursor_y - textheight)
    d.canvas.line(d.cursor_x, d.cursor_y + 5, d.w - 145, d.cursor_y + 5)
    if len(r.comment.replace(" ", "").replace("\n", "").replace("\t", "")) > 0:
        d.canvas.line(d.cursor_x, (d.cursor_y - textheight) - 5, d.w - 145, \
                (d.cursor_y - textheight) - 5)
    d.cursor_y -= textheight + 20

    # Render QR Code next to the comment
    i = generate_qr_code("{}{}".format(
        settings.SITE_URL,
        reverse('actionsetpacked', args=[r.secret, r.action_secret])
    ))
    d.canvas.drawInlineImage(i, d.w - 150, d.h - 175, 125, 125)

    # Render Contact info below comment if short
    # Render below QR code if comment is long
    d.canvas.setFont("Helvetica", 9)
    if textheight + 25 > 160:
        # Render below QR code
        d.canvas.drawString(d.w - 150, d.h - 180, "Contact: " + str(r.contact_name))
        d.canvas.drawString(d.w - 150, d.h - 195, "DECT: " + str(r.contact_dect))
        d.canvas.drawString(d.w - 150, d.h - 210, "MAIL: " + str(r.contact_mail))
    else:
        # Render below Notes
        d.canvas.drawString(d.cursor_x, d.cursor_y + 5, "Contact: " + str(r.contact_name) + \
                " DECT: " + str(r.contact_dect) + " MAIL: " + str(r.contact_mail))
        if d.cursor_y > d.h - 180:
            d.cursor_y = d.h - 180
    d.canvas.setFont("Helvetica", 11)


def render_collection_table_header(d: Document, title: str):
    d.canvas.setFillColor(black)
    d.canvas.setFont("Helvetica", 11)
    d.canvas.drawString(d.cursor_x, d.cursor_y - 5, title)
    d.cursor_y -= 15

    d.canvas.line(d.cursor_x, d.cursor_y, d.w - d.right_inset, d.cursor_y)
    d.canvas.line(d.cursor_x, d.cursor_y, d.cursor_x, d.cursor_y - 15)
    d.canvas.line(d.w - d.right_inset, d.cursor_y, d.w - d.right_inset, d.cursor_y - 15)
    d.canvas.line(d.cursor_x, d.cursor_y - 15, d.w - d.right_inset, d.cursor_y - 15)

    d.canvas.drawString(d.cursor_x + 10, d.cursor_y - 10, "Article")
    d.canvas.drawString(d.cursor_x + 310, d.cursor_y - 10, "Quantity")
    # d.canvas.drawString(d.cursor_x + 290, d.cursor_y - 10, "Notes?")
    d.canvas.drawString(A4[0] - 81, d.cursor_y - 10, "C1")
    d.canvas.drawString(A4[0] - 61, d.cursor_y - 10, "C2")

    d.canvas.line(d.cursor_x + 5, d.cursor_y, d.cursor_x + 5, d.cursor_y - 15)
    d.canvas.line(d.cursor_x + 305, d.cursor_y, d.cursor_x + 305, d.cursor_y - 15)
    # d.canvas.line(d.cursor_x + 285, d.cursor_y, d.cursor_x + 285, d.cursor_y - 15)
    d.canvas.line(d.w - d.right_inset - 18, d.cursor_y, d.w - d.right_inset - 18, d.cursor_y - 15)
    d.canvas.line((d.w - d.right_inset) - 38, d.cursor_y, (d.w - d.right_inset) - 38, d.cursor_y - 15)

    d.cursor_y -= 15


def render_collection_list_entry(pos: Variation, amount: int, d: Document):
    # Draw table boxes
    d.canvas.line(d.cursor_x, d.cursor_y, d.w - d.right_inset, d.cursor_y)
    d.canvas.line(d.cursor_x, d.cursor_y, d.cursor_x, d.cursor_y - 15)
    d.canvas.line(d.w - d.right_inset, d.cursor_y, d.w - d.right_inset, d.cursor_y - 15)
    d.canvas.line(d.cursor_x, d.cursor_y - 15, d.w - d.right_inset, d.cursor_y - 15)

    # Draw table separation lines
    d.canvas.line(d.cursor_x + 5, d.cursor_y, d.cursor_x + 5, d.cursor_y - 15)
    d.canvas.line(d.cursor_x + 305, d.cursor_y, d.cursor_x + 305, d.cursor_y - 15)
    # d.canvas.line(d.cursor_x + 285, d.cursor_y, d.cursor_x + 285, d.cursor_y - 15)
    d.canvas.line(d.w - d.right_inset - 18, d.cursor_y, d.w - d.right_inset - 18, d.cursor_y - 15)
    d.canvas.line((d.w - d.right_inset) - 38, d.cursor_y, (d.w - d.right_inset) - 38, d.cursor_y - 15)

    # Draw hollow rect for package checking
    for i in range(2):
        d.canvas.line((d.w - d.right_inset - 2) - i * 20, d.cursor_y - 2, (d.w - d.right_inset - 2) - i * 20, d.cursor_y - 13)
        d.canvas.line((d.w - d.right_inset - 13) - i * 20, d.cursor_y - 2, (d.w - d.right_inset - 13) - i * 20, d.cursor_y - 13)
        d.canvas.line((d.w - d.right_inset - 13) - i * 20, d.cursor_y - 2, (d.w - d.right_inset - 2) - i * 20, d.cursor_y - 2)
        d.canvas.line((d.w - d.right_inset - 13) - i * 20, d.cursor_y - 13, (d.w - d.right_inset - 2) - i * 20, d.cursor_y - 13)

    d.canvas.drawString(d.cursor_x + 10, d.cursor_y - 13, str(pos))
    d.canvas.drawString(d.cursor_x + 460 - d.get_text_width(str(amount), text_size=11), d.cursor_y - 10, str(amount))
    d.cursor_y -= 15


def render_collection_list(l, d: Document, title: str = "packing list:"):
    render_collection_table_header(d, title)
    for request in l:
        if d.cursor_y < (75 + 15):
            d.canvas.drawString(d.cursor_x, d.cursor_y - 15, "Please continue on next page.")
            d.new_page()
            render_collection_table_header(d, title)
        render_collection_list_entry(request[0], request[1], d)
    d.cursor_y -= 15


def render_settlement_head(d: Document):
    d.canvas.setFont("Helvetica", 11)
    d.canvas.setFillColor(black)
    d.cursor_y -= 30
    if d.cursor_y < (75 + 15):
        d.new_page()
    d.canvas.drawString(d.cursor_x, d.cursor_y - 5, "settlement: ")
    d.cursor_y -= 20

    # Render table head
    p = d.canvas
    p.line(45, d.cursor_y, 45, d.cursor_y - 15)
    p.line(d.w - 45, d.cursor_y, d.w - 45, d.cursor_y - 15)
    p.line(45, d.cursor_y, d.w - 45, d.cursor_y)
    p.line(45, d.cursor_y - 15, d.w - 45, d.cursor_y - 15)
    p.drawString(50, d.cursor_y - 10, "Amount")
    p.drawString(100, d.cursor_y - 10, "Article")
    p.drawString(250, d.cursor_y - 10, "Single Item price")
    p.drawString(d.w - 175, d.cursor_y - 10, "Sum")
    d.cursor_y -= 15
    d.canvas.setFont("Helvetica", 9)


def render_invoice_end(l, d: Document):
    render_settlement_head(d)
    total = 0
    for request in l:
        if d.cursor_y < (75 + 15):
            d.canvas.line(45, d.cursor_y, d.w - 45, d.cursor_y)
            d.canvas.drawString(d.cursor_x, d.cursor_y - 15, "Please continue on next page.")
            d.new_page()
            render_settlement_head(d)
        amount: int = request[1]
        a: Variation = request[0]
        price = a.product.price
        total += price * amount
        d.canvas.line(45, d.cursor_y, 45, d.cursor_y - 15)
        d.canvas.line(d.w - 45, d.cursor_y, d.w - 45, d.cursor_y - 15)
        d.canvas.drawString(100, d.cursor_y - 10, str(a))
        d.canvas.drawString(50, d.cursor_y - 10, str(amount))
        d.canvas.drawString(250, d.cursor_y - 10, '{:20,.2f} €'.format(price))
        d.canvas.drawString(d.w - 175, d.cursor_y - 10, '{:20,.2f} €'.format(price * amount))
        d.cursor_y -= 15
    cy = d.cursor_y
    d.canvas.line(45, cy, d.w - 45, cy)
    d.canvas.line(45, cy, 45, cy - 15)
    d.canvas.line(d.w - 45, cy, d.w - 45, cy - 15)
    d.canvas.line(45, cy - 15, d.w - 45, cy - 15)
    d.canvas.drawString(50, cy - 10, "TOTAL:")
    d.canvas.drawString(100, cy - 10, "[EUR]")
    d.canvas.drawString(d.w - 175, cy - 10, '{:20,.2f} €'.format(total))
    # Signature of person who packed and person who checked
    d.cursor_y -= 75
    d.canvas.line(55, d.cursor_y, 235, d.cursor_y)
    d.canvas.drawString(60, d.cursor_y - 10, "Signature of person who packed")
    d.canvas.line(255, d.cursor_y, 435, d.cursor_y)
    d.canvas.drawString(260, d.cursor_y - 10, "Signature of person who checked")


def render_reservation(r: Reservation, d: Document):
    if r.state == Reservation.STATE_SUBMITTED:
        d.set_watermark("")
    else:
        d.set_watermark(str(r.state))
    articles, titles = generate_collection_list(r, r.packing_mode == Reservation.PACKING_MODE_SEPERATED_PARTS)
    render_invoice_header(r, d)
    for i in range(len(articles)):
        article_group = articles[i]
        title = titles[i]
        render_collection_list(article_group, d, title)
    if len(articles) > 1:
        # We need to regenerate the list (this time without separation)
        # As we still want a single sum
        articles, titles = generate_collection_list(r, False)
        render_invoice_end(articles[0], d)
    else:
        render_invoice_end(articles[0], d)


def get_side_stip_text(r: Reservation):
    return "Reservation ID: {2}, Reservation state: {0}, Printed at {1}".format(
            str(r.state), timestamp(), r.id)


def generate_packing_pdf(reservations, filename: str, username = "nobody", title = "C3FOC - Reservations"):
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
    if (len(reservations) < 1):
        raise Exception("There needs to be at least one reservation to export.")
    logger.debug("Exporting reservations: " + str(reservations))
    d: Document = Document(filename, title, "The robots in slavery by {0}.".format(str(username)),
            "This document, originally created at {0}, contains the requested reservations.".format(timestamp(filestr=False)),
            side_label=get_side_stip_text(reservations[0]))
    reservation_counter = 0
    for r in reservations:
        reservation_counter += 1

        # Test for document appending
        if reservation_counter != 1:
            d.side_label = get_side_stip_text(r)
            d.page = 0
            d.new_page()
        
        render_reservation(r, d)
    return d.wrap_up()
