import { useState } from "react";

export default function DownloadButton({ src, filename = "speech.mp3" }) {
  const [downloading, setDownloading] = useState(false);

  if (!src) return null;

  async function handleDownload() {
    setDownloading(true);
    try {
      // Fetch as a blob so the file downloads correctly even though it's
      // served from a different origin (the Flask backend) than the page.
      const res = await fetch(src);
      if (!res.ok) throw new Error("Failed to fetch audio for download.");
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      // Fall back to opening the file directly if the blob download fails.
      window.open(src, "_blank", "noopener,noreferrer");
    } finally {
      setDownloading(false);
    }
  }

  return (
    <button
      type="button"
      onClick={handleDownload}
      disabled={downloading}
      className="inline-flex items-center justify-center rounded-lg border border-indigo-300 bg-white px-4 py-2 text-sm font-medium text-indigo-700 shadow-sm transition hover:bg-indigo-50 disabled:opacity-50"
    >
      {downloading ? "Downloading..." : "Download Audio"}
    </button>
  );
}
