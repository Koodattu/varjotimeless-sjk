"use client";
import { useEffect, useState } from "react";
import MeetingMinutesComponent from "./meetingMinutes";
import RequirementsComponent from "./requirements";
import StateComponent from "./state";
import IframeSectionComponent from "./iframeSection";
import styles from "@/app/styles/dataProvider.module.css";
import { subscribeToSSE } from "./listeners/sse";
// import { pollData } from "./listeners/poller";
//import { subscribeToWebSocket } from "./listeners/webSocketComponen";

interface ProjectData {
  notebook_summary: string;
  requirements: string[];
  current_state: string;
  deployment_url: string;
  code_generation_running: boolean;
}

export default function ProjectDataWrapper() {
  const [data, setData] = useState<ProjectData | null>(null);

  //IF SSE
  useEffect(() => {
    //const unsubscribe = subscribeToSSE(setData);
    //const unsubscribe = subscribeToWebSocket(setData);
    const unsubscribe = subscribeToSSE(setData);
    return () => unsubscribe();
  }, []);
  if (!data) return <p>Loading project data...</p>;

  return (
    <div className={styles.wrapper}>
      <div className={styles.requirementsAndState}>
        <RequirementsComponent requirements={data.requirements} />
        <StateComponent state={data.current_state} />
      </div>
      <MeetingMinutesComponent meetingMinutes={data.notebook_summary} />
      {data.code_generation_running ? (
        <div className={styles.spinnerWrapper}>
          <div className={styles.spinner}></div>
          <p>Generating code... Please wait.</p>
        </div>
      ) : (
        <IframeSectionComponent url={data.deployment_url} />
      )}
    </div>
  );
}
