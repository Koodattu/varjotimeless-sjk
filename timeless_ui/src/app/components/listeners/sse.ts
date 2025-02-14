"use client";

export function subscribeToSSE(setData: (data: any) => void) {
  const eventSource = new EventSource("http://localhost:8082/api/v0/sse");

  eventSource.onmessage = (event) => {
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
