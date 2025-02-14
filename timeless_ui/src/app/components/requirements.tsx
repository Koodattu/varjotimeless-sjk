"use client";

interface Props {
  requirements?: string[];
}

export default function RequirementsComponent({ requirements }: Props) {
  if (!requirements) return null;
  return (
    <div>
      <h3 style={{marginBottom:"10px"}}>Requirements:</h3>
      <ul style={{ listStylePosition: "inside" }}>
        {requirements.map((req, index) => (
          <li key={index}>{req}</li>
        ))}
      </ul>
    </div>
  );
}
