"use client";

import ReactMarkdown from "react-markdown";
import rehypeRaw from "rehype-raw";

interface Props {
  meetingMinutes: string;
}

export default function MeetingMinutesComponent({ meetingMinutes }: Props) {
  return (
    <div
      style={{
        padding: "1rem",
        borderRadius: "8px",
        height: "250px",
        overflowY: "auto",
        marginBottom:"20px",
        backgroundColor: "rgba(255, 255, 255, 0.1)"
      }}
    >
      <h2>Meeting Minutes</h2>
      <div style={{ whiteSpace: "pre-wrap", fontSize: "1.4rem" }}>
        <ReactMarkdown rehypePlugins={[rehypeRaw]}>
          {meetingMinutes}
        </ReactMarkdown>
      </div>
    </div>
  );
}
