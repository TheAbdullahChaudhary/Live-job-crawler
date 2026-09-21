import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "OpsBoard — Live DevOps & SRE Jobs",
  description: "A focused live feed of DevOps, SRE, platform and cloud engineering roles.",
  icons: { icon: "/favicon.svg", shortcut: "/favicon.svg" },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
