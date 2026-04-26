import Link from "next/link";
import { Shield, Search, GitBranch, FileText, ArrowRight } from "lucide-react";

const features = [
  {
    icon: <Search className="w-6 h-6 text-blue-600" />,
    title: "PII Detection",
    description:
      "Detects Aadhaar, PAN, Driving License, email, phone, and names in PDFs, DOCX, and scanned images using Microsoft Presidio.",
  },
  {
    icon: <Shield className="w-6 h-6 text-green-600" />,
    title: "Three-Level Redaction",
    description:
      "Light (mask middle), Full ([REDACTED]), or Synthetic (format-matching fake values). DPDP Act compliant.",
  },
  {
    icon: <GitBranch className="w-6 h-6 text-purple-600" />,
    title: "OpenMetadata Lineage",
    description:
      "Creates Container entities with classification tags, risk scores, and lineage edges between original and redacted versions.",
  },
  {
    icon: <FileText className="w-6 h-6 text-orange-600" />,
    title: "Risk Scoring",
    description:
      "Weighted risk formula per PII type. Automatic DPDP Act policy enforcement for HIGH and CRITICAL risk documents.",
  },
];

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-gray-50 to-white">
      {/* Hero */}
      <section className="max-w-4xl mx-auto px-6 pt-20 pb-16 text-center">
        <div className="inline-flex items-center gap-2 bg-blue-50 text-blue-700 text-xs font-medium px-3 py-1 rounded-full mb-6">
          <span>T-06 Governance &amp; Classification</span>
          <span className="text-blue-400">·</span>
          <span>T-01 MCP/AI Agents</span>
        </div>

        <h1 className="text-5xl font-bold text-gray-900 mb-4 leading-tight">
          Document PII Governance
          <br />
          <span className="text-blue-600">for OpenMetadata</span>
        </h1>

        <p className="text-xl text-gray-600 mb-8 max-w-2xl mx-auto">
          OpenMetadata governs structured data. Enterprises have thousands of PDFs full of
          Aadhaar and PAN numbers. Morolo bridges the gap.
        </p>

        <Link
          href="/dashboard"
          className="inline-flex items-center gap-2 bg-blue-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors text-lg"
        >
          Start Analyzing
          <ArrowRight className="w-5 h-5" />
        </Link>
      </section>

      {/* Features */}
      <section className="max-w-4xl mx-auto px-6 pb-20">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {features.map((feature) => (
            <div
              key={feature.title}
              className="bg-white rounded-xl border p-6 hover:shadow-md transition-shadow"
            >
              <div className="mb-3">{feature.icon}</div>
              <h3 className="font-semibold text-gray-900 mb-2">{feature.title}</h3>
              <p className="text-sm text-gray-600">{feature.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t py-6 text-center text-sm text-gray-400">
        Morolo · Code Coalescence 2025 (CC10) · OpenMetadata Hackathon
      </footer>
    </main>
  );
}
