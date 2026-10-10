import type { Metadata } from "next";
import "@fontsource-variable/inter";
import "@fontsource-variable/jetbrains-mono";
import "./globals.css";
import NavBar from "@/components/layout/NavBar";
import { AuthGate, AuthProvider } from "@/lib/auth";

export const metadata: Metadata = {
  title: "SRPPS: Smart Road Pothole Prioritization",
  description: "Turn road images into a repair-priority map and a repair plan.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col">
        <AuthProvider>
          <NavBar />
          <main className="mx-auto w-full max-w-7xl flex-1 px-4 py-6 sm:px-6 lg:px-8">
            <AuthGate>{children}</AuthGate>
          </main>
        </AuthProvider>
      </body>
    </html>
  );
}
