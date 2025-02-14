# Next.js Project

## Overview

This Next.js project displays real-time project updates using **Server-Sent Events (SSE)**. The **`ProjectDataProvider`** component manages data fetching and updates the relevant UI components accordingly.

## **ProjectDataProvider: SSE-Based Data Fetching**

The `ProjectDataProvider` component establishes a **persistent SSE connection** with the backend and updates the following components:


- **`RequirementsComponent`** - Displays **project requirements**.
- **`StateComponent`** - Highlights **the current project phase**.
- **`MeetingMinutesComponent`** - Renders **meeting minutes in markdown format**.
- **`IframeSectionComponent`** - Displays an **iframe with a provided URL**.

## **Important Notice**
Ensure that you update the correct API URL in the **SSE component** and other related files before deploying. The default URL may point to `http://localhost:3001`, but it should be changed to the correct backend endpoint for the production environment.


### **How It Works**
1. The component initializes an **SSE connection** to the backend.
2. When a new update is received, the application state is updated.
3. The updated data is passed as props to `RequirementsComponent`, `StateComponent`, `MeetingMinutesComponent`, and `IframeSectionComponent`.

---

## **Backend API Requirements**
The backend must provide an SSE endpoint (`/sse`) that continuously streams JSON updates in the following format:

### **Example JSON Response**
```json
{
    "state": "Implementation",
    "requirements": [
        "The system must support user authentication and authorization.",
        "The application must be accessible on both mobile and desktop devices.",
        "All data must be encrypted before storage.",
        "Users should be able to reset their passwords via email verification."
    ],
    "meeting_minutes": "# Project Meeting Minutes\n\n**Date:** 2024-02-12  \n**Attendees:** John Doe, Jane Smith, Alice Johnson, Bob Williams  \n\n## Agenda:\n- Review of previous action items\n- Discussion on **Implementation** phase\n- Identifying key requirements and priorities\n\n## Action Items:\n1. John Doe will finalize the requirement document by **next Friday**.\n2. Jane Smith will schedule a follow-up meeting with the **UI/UX team**.\n3. Alice Johnson will conduct a feasibility study on potential **technical challenges**.",
    "url": "https://example.com"
}

## **Deployment and Setup**
### Install Dependencies**
npm install
npm run dev
navigate to -> http://localhost:3000/
