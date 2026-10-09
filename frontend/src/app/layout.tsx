import type { Metadata } from "next";
import "@fontsource-variable/outfit";
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
        <main className="mx-auto w-full max-w-7xl flex-1 p-4 sm:p-6">{children}</main>
      </body>
    </html>
  );
}
