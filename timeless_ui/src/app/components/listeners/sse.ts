"use client";

export function subscribeToSSE(setData: (data: any) => void) {
  const eventSource = new EventSource("http://localhost:3001/sse");

  eventSource.onmessage = (event) => {
    console.log("Received SSE:", event.data);
    const newData = JSON.parse(event.data);
    setData(newData);
  };

  eventSource.onerror = (error) => {
    console.error("SSE error:", error);
    eventSource.close();
  };

  return () => {
    eventSource.close();
  };
}
