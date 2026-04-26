"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Upload, FileText, AlertCircle } from "lucide-react";
import { useUploadMutation } from "@/lib/queries";
import { cn } from "@/lib/utils";

const ALLOWED_EXTENSIONS = [".pdf", ".png", ".jpg", ".jpeg", ".docx"];
const MAX_SIZES: Record<string, number> = {
  pdf: 10 * 1024 * 1024,
  docx: 10 * 1024 * 1024,
  png: 5 * 1024 * 1024,
  jpg: 5 * 1024 * 1024,
  jpeg: 5 * 1024 * 1024,
};

// Magic bytes for client-side validation
const MAGIC_BYTES: Record<string, number[]> = {
  pdf: [0x25, 0x50, 0x44, 0x46], // %PDF
  png: [0x89, 0x50, 0x4e, 0x47], // PNG
  jpg: [0xff, 0xd8, 0xff],
  jpeg: [0xff, 0xd8, 0xff],
  docx: [0x50, 0x4b, 0x03, 0x04], // PK (ZIP)
};

async function validateFile(file: File): Promise<string | null> {
  const ext = file.name.split(".").pop()?.toLowerCase() ?? "";

  if (!ALLOWED_EXTENSIONS.includes(`.${ext}`)) {
    return `Unsupported file type. Allowed: ${ALLOWED_EXTENSIONS.join(", ")}`;
  }

  const maxSize = MAX_SIZES[ext];
  if (file.size > maxSize) {
    return `File too large. Max size for ${ext}: ${maxSize / 1024 / 1024}MB`;
  }

  // Check magic bytes
  const buffer = await file.slice(0, 8).arrayBuffer();
  const bytes = new Uint8Array(buffer);
  const expected = MAGIC_BYTES[ext];
  if (expected && !expected.every((b, i) => bytes[i] === b)) {
    return `File content doesn't match extension. Expected a valid ${ext} file.`;
  }

  return null;
}

export function UploadDropzone() {
  const router = useRouter();
  const [isDragging, setIsDragging] = useState(false);
  const uploadMutation = useUploadMutation();

  const handleFile = useCallback(
    async (file: File) => {
      const error = await validateFile(file);
      if (error) {
        toast.error(error);
        return;
      }

      try {
        const result = await uploadMutation.mutateAsync(file);
        toast.success(`"${file.name}" uploaded successfully`);
        router.push(`/dashboard/${result.doc_id}`);
      } catch (err: any) {
        const message =
          err?.response?.data?.detail ?? "Upload failed. Please try again.";
        toast.error(message);
      }
    },
    [uploadMutation, router]
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  const onInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) handleFile(file);
    },
    [handleFile]
  );

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={onDrop}
      className={cn(
        "relative flex flex-col items-center justify-center w-full h-64 border-2 border-dashed rounded-xl cursor-pointer transition-colors",
        isDragging
          ? "border-blue-500 bg-blue-50"
          : "border-gray-300 bg-gray-50 hover:bg-gray-100",
        uploadMutation.isPending && "opacity-60 pointer-events-none"
      )}
    >
      <input
        type="file"
        accept={ALLOWED_EXTENSIONS.join(",")}
        onChange={onInputChange}
        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
        disabled={uploadMutation.isPending}
      />

      <div className="flex flex-col items-center gap-3 pointer-events-none">
        {uploadMutation.isPending ? (
          <>
            <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-sm text-gray-600">Uploading…</p>
          </>
        ) : (
          <>
            <Upload className="w-10 h-10 text-gray-400" />
            <div className="text-center">
              <p className="text-sm font-medium text-gray-700">
                Drop a file here, or click to browse
              </p>
              <p className="text-xs text-gray-500 mt-1">
                PDF, DOCX, PNG, JPG — up to 10 MB
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
