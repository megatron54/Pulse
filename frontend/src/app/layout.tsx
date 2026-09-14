import type { Metadata, Viewport } from "next";
import { Geist_Mono } from "next/font/google";
import { AppShell } from "@/components/AppShell";
import "./globals.css";

// Rediseño estilo Apple (a petición del usuario, skill `apple-design`
// de github.com/emilkowalski/skills): fuera Inter/Oswald de Google
// Fonts - "default to the platform's system font before a custom
// face; it already ships optical sizing, tracking tables, and
// legibility tuning" (§15). La pila `-apple-system` (globals.css)
// cubre texto y titulares por igual, así que solo queda la fuente
// monoespaciada (sin equivalente de sistema fiable multiplataforma).
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

// Resuelve el tema ANTES del primer paint. Sin esto, el html se pinta
// con el tema claro por defecto y salta a oscuro al hidratar React -
// el destello blanco clásico. Va como string para poder inyectarlo en
// un <script> sincrónico en <head>, que es el único punto que corre
// antes de pintar (Design System v3, "Tema claro/oscuro/sistema").
const SCRIPT_TEMA = `
(function(){try{
  var g=localStorage.getItem("pulse_theme");
  var t=(g==="light"||g==="dark"||g==="system")?g:"system";
  var o=t==="dark"||(t==="system"&&window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.dataset.theme=o?"dark":"light";
}catch(e){document.documentElement.dataset.theme="light";}})();
`;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es" className={`${geistMono.variable} h-full antialiased`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: SCRIPT_TEMA }} />
      </head>
      <body className="h-full flex flex-col">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
