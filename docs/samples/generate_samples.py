"""
Generate sample PDF documents for Morolo demo.

Requires: fpdf2
Install: pip install fpdf2

Usage:
    python docs/samples/generate_samples.py
"""

from fpdf import FPDF


def create_aadhaar_sample():
    """Create a text PDF with Aadhaar and PAN numbers (HIGH risk)."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)

    content = [
        "EMPLOYEE VERIFICATION FORM",
        "",
        "Employee ID: EMP-2024-001",
        "Name: Rajesh Kumar",
        "Department: Engineering",
        "Date of Joining: 15-March-2022",
        "",
        "IDENTITY DOCUMENTS",
        "",
        "Aadhaar Number: 2345 6789 0123",
        "PAN Card: ABCDE1234F",
        "Driving License: MH02 AB 2019 1234567",
        "",
        "CONTACT INFORMATION",
        "",
        "Email: rajesh.kumar@example.com",
        "Phone: +91 98765 43210",
        "",
        "This document contains sensitive personal information.",
        "Handle with care as per DPDP Act 2023.",
    ]

    for line in content:
        pdf.cell(0, 10, line, ln=True)

    pdf.output("docs/samples/aadhaar_sample.pdf")
    print("Created: docs/samples/aadhaar_sample.pdf (HIGH risk - Aadhaar + PAN + DL)")


def create_pan_mixed():
    """Create a PDF with PAN and email (MEDIUM risk)."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)

    content = [
        "VENDOR ONBOARDING FORM",
        "",
        "Vendor Name: Priya Sharma Consulting",
        "GST Number: 27AABCU9603R1ZX",
        "",
        "PROPRIETOR DETAILS",
        "",
        "Name: Priya Sharma",
        "PAN: FGHIJ5678K",
        "Email: priya.sharma@consulting.in",
        "",
        "Bank Account: HDFC Bank",
        "Account Number: XXXX XXXX 4521",
        "IFSC: HDFC0001234",
        "",
        "Registered Address: 42, MG Road, Bangalore - 560001",
    ]

    for line in content:
        pdf.cell(0, 10, line, ln=True)

    pdf.output("docs/samples/pan_mixed.pdf")
    print("Created: docs/samples/pan_mixed.pdf (MEDIUM risk - PAN + email)")


def create_clean_doc():
    """Create a PDF with no PII (LOW risk)."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)

    content = [
        "QUARTERLY PERFORMANCE REPORT",
        "Q1 2026",
        "",
        "EXECUTIVE SUMMARY",
        "",
        "The engineering team delivered 12 features in Q1 2026.",
        "System uptime was 99.97% across all production services.",
        "Customer satisfaction score improved from 4.2 to 4.6.",
        "",
        "KEY METRICS",
        "",
        "- Deployments: 47",
        "- Incidents: 3 (all P2, resolved within SLA)",
        "- Code coverage: 84%",
        "- Technical debt reduction: 15%",
        "",
        "NEXT QUARTER GOALS",
        "",
        "1. Launch document governance module",
        "2. Achieve 90% code coverage",
        "3. Reduce P1 incident response time to < 15 minutes",
    ]

    for line in content:
        pdf.cell(0, 10, line, ln=True)

    pdf.output("docs/samples/clean_doc.pdf")
    print("Created: docs/samples/clean_doc.pdf (LOW risk - no PII)")


if __name__ == "__main__":
    import os
    os.makedirs("docs/samples", exist_ok=True)

    create_aadhaar_sample()
    create_pan_mixed()
    create_clean_doc()

    print("\nAll sample documents created.")
    print("Upload these to Morolo for the demo:")
    print("  1. aadhaar_sample.pdf → HIGH risk (Aadhaar + PAN + DL)")
    print("  2. pan_mixed.pdf      → MEDIUM risk (PAN + email)")
    print("  3. clean_doc.pdf      → LOW risk (no PII)")
