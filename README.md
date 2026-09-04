# Devin + Power Apps: KYC Review Queue prototype

This repo is my Cognition take-home. The question: can a fintech team use Devin to build the internal tools they currently make in Microsoft Power Apps?

To test that, I had Devin build one of their real apps, a KYC review queue, directly inside Power Apps. Devin writes the app's source files, checks them, and pushes them into Power Apps Studio through Microsoft's own authoring tool.

## Demo

https://github.com/user-attachments/assets/6fcde944-62c8-4954-8730-af42a3042691

Download: [Cognition_TH_Prototype_demo.mp4](./Cognition_TH_Prototype_demo.mp4)

## What the app does

A compliance reviewer opens the app and sees:

- **Dashboard.** Counts of pending, approved-today, and rejected-today requests. A list of pending requests with a colour-coded risk score. Search by name and filter by risk level.
- **Review screen.** All details of one request, a notes box, and Approve / Reject buttons. High-risk approvals need a supervisor email. Rejections need notes. Every decision writes an audit log entry.
- **History.** Every reviewed request with who reviewed it and when. Filter by status.

Data is seeded in memory when the app starts, since this environment has no database.

## What is in this repo

| Path | What it is |
|---|---|
| `kyc-example/PROMPT.md` | The task given to Devin: the app spec plus connection IDs. |
| `kyc-example/generated/` | The Power Apps source files Devin wrote (`.pa.yaml`, one per screen). |
| `skills/power-apps-canvas-authoring/` | The playbook Devin follows: how to connect, write valid YAML, and fix compile errors. Includes a small checker script. |
| `setup.sh` | Checks you have the tools installed. |
| `connect.sh` | Installs Microsoft's Power Apps plugin into Devin and confirms it boots. |
| `.devin/mcp_config.json` | Tells Devin how to start Microsoft's Canvas Authoring server. |

## How to run it

You need: .NET 10 SDK, the Devin CLI (logged in), and a Microsoft work or school account with Power Apps.

1. **Check prerequisites.**
   ```bash
   ./setup.sh
   ```
   It tells you what is missing and how to install it.

2. **Install the Power Apps plugin into Devin.**
   ```bash
   ./connect.sh
   ```

3. **Create an empty app in Power Apps.** In the browser, go to https://make.powerapps.com.
   Create a blank canvas app (tablet) and save it. In Settings, turn on "Coauthoring". Keep the tab open.

4. **Copy the IDs.** The address bar looks like
   `https://make.powerapps.com/e/<ENVIRONMENT_ID>/canvas/?action=edit&app-id=<APP_ID>`.
   Paste both IDs into `kyc-example/PROMPT.md` under "Connection values".

5. **Hand it to Devin.**
   ```bash
   devin --prompt-file kyc-example/PROMPT.md
   ```
   Devin signs in to Microsoft (a browser window opens), writes the four source files, compiles them until there are no errors, and syncs the app into your open Studio tab.

6. **Try it.** Press Play in Power Apps Studio.

## Notes

- Devin never touches the Power Apps UI. It only writes source files and calls Microsoft's authoring server, so every change is reviewable text.
- The `skills` folder is the important part. It captures the rules that made the build succeed on the first compile pass, so the next app is cheaper than the first.
