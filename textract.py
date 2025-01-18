import fitz  # PyMuPDF
import sys

import fitz  # PyMuPDF

def extract_text_and_fonts(pdf_path):
    lines = []
    try:
        # Open the PDF document
        doc = fitz.open(pdf_path)
        
        # Loop through each page in the document

        for page_num in range(len(doc)):
            page = doc[page_num]
            print(f"\nPage {page_num + 1}")
            
            # Extract blocks of text
            blocks = page.get_text("dict")['blocks']
            for block in blocks:
                if 'lines' in block:  # Ensure the block contains text
                    print("\nBlock:")
                    block_bbox = block['bbox']  # Get block position
                    print(f"Block Position: {block_bbox}")
                    for line in block['lines']:
                        for span in line['spans']:
                            lines.append((span['text'], span['bbox']))
                            text = span['text']
                            font = span['font']
                            position = span['bbox']  # Get position of the span
                            print(f"Text: {text}")
                            print(f"Font: {font}")
                            print(f"Position: {position}")
    except Exception as e:
        print(f"An error occurred: {e}")
    xs = set()
    for text, pos in lines:
        x1,y1,x2,y2 = pos
        x1 = int(x1)
        xs.add(x1)
    xs = list(xs)
    xs.sort()
    print(xs)

    for text, pos in lines:
        x1,y1,x2,y2 = pos
        x1 = int(x1)
        i = xs.index(x1)*4
        print(" "*i + text)


# Path to the PDF file
pdf_path = sys.argv[1]  # Replace with your PDF file path

# Call the function
extract_text_and_fonts(pdf_path)

