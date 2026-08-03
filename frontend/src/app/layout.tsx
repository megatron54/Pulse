import type { Metadata, Viewport } from "next";
import { Geist_Mono, Inter, Oswald } from "next/font/google";
import { AppShell } from "@/components/AppShell";
import "./globals.css";

// Sustitutas libres de Proxima Nova (texto) y DINPro (números) - las
// fuentes reales de la guía de marca de WHOOP son de pago. Ver
// globals.css para el razonamiento completo de la elección.
const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

const oswald = Oswald({
  variable: "--font-oswald",
  subsets: ["latin"],
  weight: ["500", "600", "700"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Pulse",
  description: "Entrenador personal con IA - recovery, strain y nutrición en un solo lugar.",
};

// viewportFit: "cover" habilita env(safe-area-inset-*) en CSS (code-review
// M1) - sin esto, la barra de pestañas móvil invadiría el área del
// home indicator en iPhones con notch.
export const viewport: Viewport = {
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="es"
      className={`${inter.variable} ${oswald.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="h-full flex flex-col">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
