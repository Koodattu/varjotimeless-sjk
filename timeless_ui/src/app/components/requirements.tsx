"use client";

interface Props {
  requirements?: string[] | string;
}

export default function RequirementsComponent({ requirements }: Props) {
  if (!requirements) return null;

  // Muutetaan string tarvittaessa taulukoksi
  const requirementsArray: string[] =
    typeof requirements === "string"
      ? (requirements.includes("\n")
          ? requirements.split("\n").filter((line) => line.trim() !== "")
          : [requirements])
      : requirements;

  return (
    <div>
      <h3 style={{ marginBottom: "10px" }}>Requirements:</h3>
      <ul style={{ listStylePosition: "inside" }}>
        {requirementsArray.map((req, index) => (
          <li key={index}>{req}</li>
        ))}
      </ul>
    </div>
  );
}
