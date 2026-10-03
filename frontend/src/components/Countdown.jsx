import { useEffect, useState } from "react";
import { Clock, Loader2 } from "lucide-react";

// returns ms remaining until draw_at using server clock offset
export function useCountdown(raffle) {
  const [left, setLeft] = useState(null);
  useEffect(() => {
    if (!raffle?.draw_at || raffle.status !== "active") {
      setLeft(null);
      return;
    }
    const offset = new Date(raffle.server_now).getTime() - Date.now();
    const target = new Date(raffle.draw_at).getTime();
    const tick = () => setLeft(Math.max(0, target - (Date.now() + offset)));
    tick();
    const t = setInterval(tick, 250);
    return () => clearInterval(t);
  }, [raffle?.draw_at, raffle?.server_now, raffle?.status]);
  return left;
}

export const fmtMs = (ms) => {
  const s = Math.ceil(ms / 1000);
  return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;
};

export default function CountdownBanner({ left }) {
  if (left === null) return null;
  const zero = left <= 0;
  return (
    <div data-testid="draw-countdown-banner" className="relative overflow-hidden rounded-2xl border border-[#ff2e55]/40 bg-gradient-to-r from-[#e50914]/20 via-[#131722] to-[#ff2e55]/10 px-6 py-6 shadow-[0_0_60px_-20px_rgba(255,46,85,0.7)]">
      <div className="flex flex-col items-center justify-center gap-2 sm:flex-row sm:gap-5">
        <span className="flex items-center gap-2 text-sm font-bold uppercase tracking-widest text-[#ff2e55]">
          {zero ? <Loader2 className="h-5 w-5 animate-spin" /> : <Clock className="h-5 w-5" />}
          {zero ? "Sorteio começando agora!" : "Meta atingida! Sorteio em"}
        </span>
        {!zero && (
          <span data-testid="draw-countdown-time" className="font-head text-5xl font-extrabold tabular-nums text-white drop-shadow-[0_0_18px_rgba(255,46,85,0.6)] sm:text-6xl">
            {fmtMs(left)}
          </span>
        )}
      </div>
    </div>
  );
}

export function DrawPendingPanel({ left }) {
  return (
    <div data-testid="draw-pending-panel" className="flex h-full min-h-[360px] flex-col items-center justify-center rounded-2xl border border-[#ff2e55]/30 bg-[#131722] p-8 text-center shadow-2xl">
      <Clock className="h-12 w-12 animate-pulse text-[#ff2e55]" />
      <h3 className="mt-4 font-head text-xl font-extrabold text-white">Sorteio em andamento</h3>
      <p className="mt-2 max-w-sm text-sm text-slate-400">
        A meta foi atingida! As vendas estão encerradas e o sorteio será realizado ao vivo quando a contagem chegar a zero. Fique na página!
      </p>
      {left > 0 && <p className="mt-4 font-head text-3xl font-extrabold tabular-nums text-[#f59e0b]">{fmtMs(left)}</p>}
    </div>
  );
}
