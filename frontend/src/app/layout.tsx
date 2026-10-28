import type { Metadata } from "next";
import "./globals.css";
import "../styles/custom.scss";

export const metadata: Metadata = {
  title: "Yrys Kanban — Корпоративная система управления задачами",
  description: "Корпоративная веб-платформа с канбан-досками и автоматическим многоязычным переводом",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ru" className="h-full">
      <body className="min-h-full flex flex-col bg-slate-50 dark:bg-slate-950 text-black dark:text-white antialiased font-sans transition-colors duration-200">
        {children}
      </body>
    </html>
  );
}
