import type { Metadata } from "next";
import { Geist, Geist_Mono, Roboto } from "next/font/google";
import "./styles/globals.css";

// Root layout for the application. 
// Defines global HTML structure, metadata, and fonts.

// Define fonts for the application.
// its recomended to describe the font in the layout file for better optimization.
const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const roboto = Roboto({
  variable: "--font-roboto",
  style: "normal",
  subsets: ["latin"],
  weight: "400",
});

// Metadata for the application.
// This is used by search engines and social media.
// Also shown title in the browser tab.
export const metadata: Metadata = {
  title: "Timeless",
  description: "A timeless application.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${roboto.variable} ${geistSans.variable} ${geistMono.variable}`}>
        {children}
      </body>
    </html>
  );
}
