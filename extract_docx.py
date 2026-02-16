
import zipfile
import xml.etree.ElementTree as ET
import os

def extract_text_from_docx(docx_path):
    try:
        with zipfile.ZipFile(docx_path) as z:
            xml_content = z.read('word/document.xml')
            tree = ET.fromstring(xml_content)
            
            # Simple text extraction. 
            # Word stores text in <w:t> tags within <w:r> within <w:p>.
            # We will try to group by paragraphs.
            
            namespaces = {
                'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
            }
            
            structure = []
            
            for p in tree.iterfind('.//w:p', namespaces):
                para_text = ""
                for t in p.iterfind('.//w:t', namespaces):
                    if t.text:
                        para_text += t.text
                
                if para_text.strip():
                    structure.append(para_text.strip())
                    
            return structure
            
    except Exception as e:
        return [f"Error reading docx: {str(e)}"]

if __name__ == "__main__":
    path = r"c:\Users\armas\OneDrive\Escritorio\LECTOR\PreDatos.docx"
    output_path = r"c:\Users\armas\OneDrive\Escritorio\LECTOR\docx_content.txt"
    
    if os.path.exists(path):
        lines = extract_text_from_docx(path)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("--- CONTENT START ---\n")
            for line in lines:
                f.write(line + "\n")
            f.write("--- CONTENT END ---\n")
        print(f"Content extracted to {output_path}")
    else:
        print(f"File not found: {path}")
