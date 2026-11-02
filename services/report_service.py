import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas as pdf_canvas

class ReportService:
    def generate_monthly_pdf(self, month_data, day_records):
        buffer = io.BytesIO()
        c = pdf_canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        y = height - 2*cm
        c.setFont("Helvetica-Bold", 16)
        c.drawString(2*cm, y, f"Monatsbericht {month_data['monat']} {month_data['jahr']}")
        y -= 1*cm

        c.setFont("Helvetica", 11)
        lines = [
            f"Soll-Stunden gesamt: {month_data['soll_stunden_gesamt']:.2f}",
            f"Ist Arbeitszeit: {month_data['ist_arbeitszeit_laufend']:.2f}",
            f"Ist Remote: {month_data['ist_remote_stunden_laufend']:.2f}",
            f"Individuelle Quote: {month_data['individuelle_quote']:.0f}%",
            f"Max Remote: {month_data['max_remote_stunden']:.2f}",
        ]
        for line in lines:
            c.drawString(2*cm, y, line)
            y -= 0.7*cm

        if day_records:
            y -= 0.5*cm
            c.setFont("Helvetica-Bold", 12)
            c.drawString(2*cm, y, "Tägliche Einträge:")
            y -= 0.6*cm
            c.setFont("Helvetica", 9)
            for r in day_records:
                line = f"{r['datum']}: {r['startTime']}-{r['endTime']} Pause {r['pauseMinutes']}min | Remote {r['remoteStundenHeute']:.2f}h | Gesamt {r['totalStundenHeute']:.2f}h"
                c.drawString(2*cm, y, line[:120])
                y -= 0.5*cm
                if y < 2*cm:
                    c.showPage()
                    y = height - 2*cm

        c.showPage()
        c.save()
        pdf = buffer.getvalue()
        buffer.close()
        return pdf
