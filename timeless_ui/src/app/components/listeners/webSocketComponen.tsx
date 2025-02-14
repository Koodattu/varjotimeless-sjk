"use client";

import io from "socket.io-client";

interface ProjectData {
  meeting_minutes: string;
  requirements: string[];
  state: string;
}

export function subscribeToWebSocket(setData: (data: ProjectData) => void) {
  const socket = io("http://localhost:8082", { path: "/socket/" });

  socket.on("backend-update", (data: ProjectData) => {
    console.log("Received WebSocket data:", data);
    setData(data);
  });

  return () => {
    socket.disconnect();
  };
}
