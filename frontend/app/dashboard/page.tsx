import { UploadDropzone } from "@/components/upload/UploadDropzone";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export default function DashboardPage() {
  return (
    <main className="min-h-screen bg-gray-50">
      <div className="max-w-2xl mx-auto px-6 py-12">
        {/* Back link */}
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 mb-8"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to home
        </Link>

        <h1 className="text-2xl font-bold text-gray-900 mb-2">Upload Document</h1>
        <p className="text-gray-600 mb-8">
          Upload a PDF, DOCX, or image to detect PII and create an OpenMetadata Container entity.
        </p>

        <UploadDropzone />

        <p className="mt-4 text-xs text-gray-400 text-center">
          Supported: PDF (≤10MB), DOCX (≤10MB), PNG/JPG (≤5MB)
        </p>
      </div>
    </main>
  );
}
