"use client";

interface Props {
  url?: string;
}

export default function IframeSectionComponent({ url }: Props) {
  if (!url) return null; // If url is undefined, return null

  return (
    <div style={{ width: "100%", height: "500px", border: "1px solid #ccc" }}>
      <iframe
        src={url}
        width="100%"
        height="100%"
        style={{ border: "none" }}
        allowFullScreen
      />
    </div>
  );
}
