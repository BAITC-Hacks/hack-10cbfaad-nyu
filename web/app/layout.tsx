import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "EKT AI — консультант по электротоварам",
  description: "AI-консультант EKT с поиском товаров и подтверждением добавления в корзину.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ru">
      <body>{children}</body>
    </html>
  );
}
