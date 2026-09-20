import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Cortex AI",
  description: "Interactive AI training: role-based tracks, daily micro-learning, and a live prompt sandbox.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
