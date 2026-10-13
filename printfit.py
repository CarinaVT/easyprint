"""
PrintFit - print PDFs with no white margins on office printers.
Never stretches: always uses ONE uniform scale factor.

Modes:
  1. Trim white + fill page  : removes the white border from the artwork, then scales
                               it up to cover the whole sheet (edges beyond the
                               printer's unprintable area are clipped).
  2. Fill page (no trim)     : scales the PDF page to cover the whole sheet.
  3. Fit printable area      : whole design visible, only white where aspect differs.

Install:   pip install pymupdf pillow pywin32
Run:       python printfit.py
Make .exe: pip install pyinstaller  &&  pyinstaller --onefile --noconsole printfit.py
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import fitz  # PyMuPDF
import win32con
import win32gui
import win32print
import win32ui
from PIL import Image, ImageChops, ImageWin

# GetDeviceCaps indexes
HORZRES, VERTRES = 8, 10
LOGPIXELSX = 88
PHYSICALWIDTH, PHYSICALHEIGHT = 110, 111
PHYSICALOFFSETX, PHYSICALOFFSETY = 112, 113

PAPERS = {"A4": 9, "A3": 8, "A5": 11, "Letter": 1, "Printer default": None}
MODES = ["Trim white + fill page", "Fill page (no trim)", "Fit printable area"]


def list_printers():
    flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    return [p[2] for p in win32print.EnumPrinters(flags)]


def render_page(page, dpi):
    pix = page.get_pixmap(dpi=dpi, alpha=False)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def content_bbox(img, tol=12):
    """Bounding box of non-white pixels."""
    white = Image.new("RGB", img.size, (255, 255, 255))
    diff = ImageChops.difference(img, white).convert("L")
    return diff.point(lambda p: 255 if p > tol else 0).getbbox()


def make_dc(printer, paper_id, landscape):
    h = win32print.OpenPrinter(printer)
    try:
        devmode = win32print.GetPrinter(h, 2)["pDevMode"]
    finally:
        win32print.ClosePrinter(h)
    devmode.Orientation = 2 if landscape else 1
    devmode.Fields |= win32con.DM_ORIENTATION
    if paper_id:
        devmode.PaperSize = paper_id
        devmode.Fields |= win32con.DM_PAPERSIZE
    hdc = win32gui.CreateDC("WINSPOOL", printer, devmode)
    return win32ui.CreateDCFromHandle(hdc)


def print_pdf(path, printer, paper, mode, copies, trim_tol):
    doc = fitz.open(path)
    first = doc[0].rect
    landscape = first.width > first.height
    paper_id = PAPERS[paper]

    dc = make_dc(printer, paper_id, landscape)
    dpi = min(dc.GetDeviceCaps(LOGPIXELSX), 1200)
    pw, ph = dc.GetDeviceCaps(PHYSICALWIDTH), dc.GetDeviceCaps(PHYSICALHEIGHT)
    ox, oy = dc.GetDeviceCaps(PHYSICALOFFSETX), dc.GetDeviceCaps(PHYSICALOFFSETY)
    rw, rh = dc.GetDeviceCaps(HORZRES), dc.GetDeviceCaps(VERTRES)

    dc.StartDoc(f"PrintFit - {path}")
    for _ in range(copies):
        for page in doc:
            img = render_page(page, dpi)
            if (img.width > img.height) != landscape:
                img = img.rotate(90, expand=True)

            if mode == MODES[0]:
                bbox = content_bbox(img, trim_tol)
                if bbox:
                    img = img.crop(bbox)

            iw, ih = img.size
            if mode == MODES[2]:
                s = min(rw / iw, rh / ih)
                dw, dh = int(iw * s), int(ih * s)
                x, y = (rw - dw) // 2, (rh - dh) // 2
            else:
                s = max(pw / iw, ph / ih)  # cover the entire physical sheet
                dw, dh = int(iw * s), int(ih * s)
                # device origin = top-left of printable area, paper starts at (-ox,-oy)
                x, y = -ox + (pw - dw) // 2, -oy + (ph - dh) // 2

            img = img.resize((dw, dh), Image.LANCZOS)  # same factor both axes
            dc.StartPage()
            ImageWin.Dib(img).draw(dc.GetHandleOutput(), (x, y, x + dw, y + dh))
            dc.EndPage()
    dc.EndDoc()
    dc.DeleteDC()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("PrintFit")
        self.resizable(False, False)
        pad = {"padx": 8, "pady": 5}

        self.path = tk.StringVar()
        self.printer = tk.StringVar()
        self.paper = tk.StringVar(value="A4")
        self.mode = tk.StringVar(value=MODES[0])
        self.copies = tk.IntVar(value=1)
        self.tol = tk.IntVar(value=12)

        printers = list_printers()
        try:
            self.printer.set(win32print.GetDefaultPrinter())
        except Exception:
            if printers:
                self.printer.set(printers[0])

        ttk.Label(self, text="PDF:").grid(row=0, column=0, sticky="e", **pad)
        ttk.Entry(self, textvariable=self.path, width=48).grid(row=0, column=1, **pad)
        ttk.Button(self, text="Browse", command=self.browse).grid(row=0, column=2, **pad)

        ttk.Label(self, text="Printer:").grid(row=1, column=0, sticky="e", **pad)
        ttk.Combobox(self, textvariable=self.printer, values=printers, width=45,
                     state="readonly").grid(row=1, column=1, columnspan=2, sticky="w", **pad)

        ttk.Label(self, text="Paper:").grid(row=2, column=0, sticky="e", **pad)
        ttk.Combobox(self, textvariable=self.paper, values=list(PAPERS), width=20,
                     state="readonly").grid(row=2, column=1, sticky="w", **pad)

        ttk.Label(self, text="Mode:").grid(row=3, column=0, sticky="e", **pad)
        ttk.Combobox(self, textvariable=self.mode, values=MODES, width=30,
                     state="readonly").grid(row=3, column=1, sticky="w", **pad)

        ttk.Label(self, text="Copies:").grid(row=4, column=0, sticky="e", **pad)
        ttk.Spinbox(self, from_=1, to=999, textvariable=self.copies,
                    width=6).grid(row=4, column=1, sticky="w", **pad)

        ttk.Label(self, text="White tolerance:").grid(row=5, column=0, sticky="e", **pad)
        ttk.Spinbox(self, from_=0, to=60, textvariable=self.tol,
                    width=6).grid(row=5, column=1, sticky="w", **pad)

        ttk.Button(self, text="Print", command=self.do_print).grid(
            row=6, column=1, sticky="w", **pad)

    def browse(self):
        f = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
        if f:
            self.path.set(f)

    def do_print(self):
        if not self.path.get() or not self.printer.get():
            messagebox.showwarning("PrintFit", "Choose a PDF and a printer.")
            return
        try:
            print_pdf(self.path.get(), self.printer.get(), self.paper.get(),
                      self.mode.get(), self.copies.get(), self.tol.get())
            messagebox.showinfo("PrintFit", "Sent to printer.")
        except Exception as e:
            messagebox.showerror("PrintFit", str(e))


if __name__ == "__main__":
    App().mainloop()
