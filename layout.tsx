import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AI Tabanlı Araç Fiyat Değerleme ve Karar Destek Asistanı",
  description: "Yapay zeka destekli ikinci el araç piyasası analiz asistanı.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="tr">
      <body className={`${inter.className} bg-slate-50`}>
        {children}
      </body>
    </html>
  );
}