from fpdf import FPDF
from io import BytesIO
from datetime import datetime

def generate_pdp_pdf(pdp_doc, player_name):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Metadata
    created = datetime.fromisoformat(pdp_doc["created"]).strftime("%Y-%m-%d")
    created_by = pdp_doc.get("created_by", "Unknown")

    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, f"PDP Report for {player_name}", ln=True, align="C")
    
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 10, f"Created: {created} by {created_by}", ln=True, align="C")
    pdf.ln(5)

    for category, subcats in pdp_doc["data"].items():
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 8, category, ln=True)
        pdf.ln(2)

        for subcat, topics in subcats.items():
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 8, f"  {subcat}", ln=True)

            # Add table header
            pdf.set_font("Arial", "B", 10)
            pdf.cell(80, 8, "Topic", border=1)
            pdf.cell(30, 8, "Score", border=1, align="C")
            pdf.cell(30, 8, "Priority", border=1, align="C")
            pdf.ln()

            # Add topic rows
            pdf.set_font("Arial", "", 10)
            for topic, details in topics.items():
                score = details["score"]
                priority = "Yes" if details["priority"] else "No"
                
                pdf.cell(80, 8, topic, border=1)
                pdf.cell(30, 8, str(score), border=1, align="C")
                pdf.cell(30, 8, priority, border=1, align="C")
                pdf.ln()

                # Optional: add comment in a separate row
                comment = details.get("comment", "").strip()
                if comment:
                    pdf.set_font("Arial", "I", 10)
                    pdf.multi_cell(140, 6, f"  Comment: {comment}", border='LRB')  # align under full width
                    pdf.set_font("Arial", "", 10)

            pdf.ln(2)

    # Output as bytes
    buffer = BytesIO()
    pdf_bytes = pdf.output(dest='S').encode('latin-1')  # 'S' returns PDF as a string
    buffer.write(pdf_bytes)
    buffer.seek(0)
    return buffer