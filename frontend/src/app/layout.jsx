import './globals.css'

export const metadata = {
  title: 'WallVision — FMCW Radar DSP Pipeline',
  description: 'Through-wall human detection and vital sign extraction via FMCW radar signal processing.',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}