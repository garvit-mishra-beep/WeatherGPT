import type { Metadata } from "next";
import "@/styles/globals.css";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";
import { ShowcaseBar } from "@/components/showcase/ShowcaseBar";

export const metadata: Metadata = {
  title: "VAYUBODHAK — Evidence-First Disaster Intelligence",
  description:
    "Deterministic multi-criteria disaster intelligence, Nirnay decision support, and operational resilience platform.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <Header />
        <ShowcaseBar />
        <div className="vayu-layout-grid">
          <Sidebar />
          <main style={{ padding: "1.5rem", maxWidth: "1200px", width: "100%" }}>
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
