"use client";

interface Props {
  state?: string;
}

const STATES = [
  "Conceptualization",
  "Requirement Analysis",
  "Design (tech & UIUX)",
  "Implementation",
  "Testing",
  "Deployment, and Maintenance",
];

export default function StateComponent({ state }: Props) {
  if (!state) return null;
  return (
    <div>
      <h3 style={{ marginBottom: "10px" }}>Project State:</h3>
      <div style={{ position: "relative", fontSize: "1.2rem" }}>
        {STATES.map((option, index) => (
          <p
            key={index}
            style={{
              left: 0,
              top: `${index * 1.5}rem`,
              opacity: state === option ? 1 : 0.4,
              fontWeight: state === option ? "bold" : "normal",
              transition: "opacity 0.3s ease-in-out",
            }}
          >
            {option}
          </p>
        ))}
      </div>
    </div>
  );
}
