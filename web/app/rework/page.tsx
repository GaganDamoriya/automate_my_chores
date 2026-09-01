import { redirect } from "next/navigation";

// Rework intelligence is no longer a separate page — it's the "Rework Intelligence"
// automation. Anyone hitting /rework is sent to the Automations page.
export default function ReworkRedirect() {
  redirect("/automations");
}
