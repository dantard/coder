#!/usr/bin/env python
import argparse
import os
import re
import sys

from PyPDF2 import PdfReader, PdfWriter
from pygments.lexer import include
from reportlab.pdfgen import canvas
from reportlab.lib.colors import white, red, black, Color
from io import BytesIO

def add_text_to_page(page, text, position, page_size):
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=page_size)
    custom_color = Color(0.894, 0.118, 0.118)

    # Draw red background for text
    text_width = 35  # Approximate width of the text background
    text_height = 20  # Height of the text background
    can.setFillColor(custom_color)
    can.setStrokeColor(custom_color)
    can.rect(position[0]-10 , position[1] -5, text_width, text_height, fill=1)

    # Draw white text
    can.setFillColor(white)
    can.setFont("Helvetica-Bold", 16)
    can.drawString(position[0], position[1], text)
    can.save()

    packet.seek(0)
    new_pdf = PdfReader(packet)
    overlay_page = new_pdf.pages[0]

    page.merge_page(overlay_page)
    return page

def process_pdf(input_path, base_output_path, suffix, exclude):
    reader = PdfReader(input_path)
    output_count = 0
    writer = None
    count = 1
    filename = None

    for i, page in enumerate(reader.pages):
        page_text = page.extract_text()
        page_size = (page.mediabox.width, page.mediabox.height)

        #print(page_text)
        if "Grado en Estudios para la Defensa y Seguridad".lower() in page_text.lower():
            if writer is not None and len(writer.pages) > 0:
                print("filename: ", filename)

                if filename is None:
                    filename = f"{base_output_path}_{output_count}{suffix}.pdf"
                else:
                    filename = base_output_path + filename + suffix + ".pdf"
                with open(filename, "wb") as output_file:
                    writer.write(output_file)
                    filename = None

                output_count += 1

            writer = PdfWriter()
            count = 1


        if "bloque" in page_text.lower() and "tema" in page_text.lower():
            for line in page_text.split("\n"):
                if "BLOQUE" in line and "TEMA" in line:
                    matches = re.findall(r'\d+', line)
                    next_line = page_text.split("\n")[page_text.split("\n").index(line) + 1]
                    block = matches[0]  # Extracts '2'
                    topic = matches[1]  # Extracts '5'

                    filename = f"B{block}_T{topic}_{next_line.strip()}"



        if "LAB:" in page_text:
            for line in page_text.split("\n"):
                if "LAB:" in line:
                    filename = line.strip()


        if writer is not None:
            if exclude is not None and exclude.lower() in page_text.lower():
                continue

            if count > 2:
                new_page = add_text_to_page(page, str(count), (930, 6), page_size)
            else:
                new_page = add_text_to_page(page, "", (930, 6), page_size)
            writer.add_page(new_page)
            count = count + 1

    if writer is not None and len(writer.pages) > 0:
        if filename is None:
            filename = f"{base_output_path}_{output_count}.pdf"
        with open(filename, "wb") as output_file:
            writer.write(output_file)

def main():
    # add switches instead of positional arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="Suffix to add to the output files", type=str)
    parser.add_argument("dir", help="Suffix to add to the output files", type=str)
    parser.add_argument("-s", "--suffix", help="Suffix to add to the output files", type=str, default="")
    parser.add_argument("-x", "--exclude", help="Exclude pages with this text", type=str, default=None)

    args = parser.parse_args()

    suffix = ("_" if args.suffix != "" else "")  + args.suffix

    process_pdf(args.file, args.dir +"/", suffix , args.exclude)

if __name__ == "__main__":
    main()


