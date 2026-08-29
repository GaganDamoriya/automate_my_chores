import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Invisible Work Detector",
  description: "Discover repetitive invisible work and automate it.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
