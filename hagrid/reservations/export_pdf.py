from io import import BytesIO
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle

import datetime
import loggin
import qrcode
import time

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
    bytes_buffer = None
    canvas: canvas = None
    side_label: str = ""
    cursor_v = 0
    cursor_h = 0


    def __init__(self, filename: str, title: str, author: str, subject: str, side_label = ""):
        self.page = 0
        self.bytes_buffer = BytesIO()
        self.canvas = canvas.Canvas(self.bytes_buffer, pagesize=A4, pageCompression=0)
        self.canvas.setTitle(title)
        self.w, self.h = A4
        self.canvas.setAuthor(author)
        self.canvas.setSubject(subject)
        self.side_label = side_label
        self.newpage()


    def bookmark_page(self, text: str):
        self.canvas.addOutlineEntry(text, "p" + str(self.page))
        self.canvas.bookmarkPage("p" + str(self.page))


    def render_page_hint(self):
        self.canvas.drawString(self.w - 75, self.h - 35, "Page " + str(self.page))


    def newpage(self, bookmark = None):
        self.canvas.showPage()
        self.page += 1
        self.cursor_v = h - 75
        self.cursor_h = 75
        self.canvas.setFont("Helvetica", 9)
        self.canvas.rotate(90)
        self.canvas.drawString(self.side_label)
        self.canvas.setFont("Helvetica", 14)
        if bookmark is not None:
            self.bookmark_page(bookmark)


    def wrap_up(self):
        self.canvas.showPage()
        self.canvas.save()
        pdfbytes = self.bytes_buffer.getvalue()
        self.bytes_buffer.close()
        self.canvas = None
        self.bytes_buffer = None
        return pdfbytes


def timestamp(filestr=True):
    if filestr:
        return datetime.datetime.fromtimestamp(time.time()).strftime('%d_%m_%Y__%H_%M_Uhr')
    else:
        return datetime.datetime.fromtimestamp(time.time()).strftime('%m/%d/%Y %H:%M:%S Uhr')


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
    return d.wrap_up()
