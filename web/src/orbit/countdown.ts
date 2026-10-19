/** Seconds remaining until `to`, never negative. */
export function countdownSeconds(to: Date, now: Date): number {
  return Math.max(0, Math.floor((to.getTime() - now.getTime()) / 1000));
}

export function formatCountdown(totalSeconds: number): string {
  const seconds = Math.max(0, Math.floor(totalSeconds));
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  const two = (n: number) => String(n).padStart(2, "0");
  if (h > 0) {
    return `${h}:${two(m)}:${two(s)}`;
  }
  return `${two(m)}:${two(s)}`;
}
