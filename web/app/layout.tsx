import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Invisible Work Detector",
  description: "Find invisible work, automate it, and watch your automations run.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
