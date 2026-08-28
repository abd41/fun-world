import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

/**
 * No stylesheet is imported, and that is the intended state for vertical 001.
 * `packages/tokens` is empty and §14 fails the build on a literal colour, so
 * there is nothing legitimate to style with until vertical 002 lands the
 * design system.
 */
export const metadata: Metadata = {
  title: "Fun World",
  description: "A private home streaming app.",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
