"use client";

export function pollData(setData: (data: any) => void) {
  const fetchData = async () => {
    try {
      const response = await fetch("http://localhost:8082/polling");
      if (!response.ok) throw new Error("Network response was not ok");
      const data = await response.json();
      setData(data);
    } catch (error) {
      console.error("Polling error:", error);
    }
  };

  const interval = setInterval(fetchData, 5000);
  fetchData();

  return () => clearInterval(interval);
}
