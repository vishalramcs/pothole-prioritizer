import type { Metadata } from "next";
import "./globals.css";
import NavBar from "@/components/layout/NavBar";

export const metadata: Metadata = {
  title: "SRPPS: Smart Road Pothole Prioritization",
  description: "Turn road images into a repair-priority map and a repair plan.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">
        <NavBar />
        <main className="flex-1 p-6">{children}</main>
      </body>
    </html>
  );
}
