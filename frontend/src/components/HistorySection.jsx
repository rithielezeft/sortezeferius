import { Trophy, Calendar, Users, Ticket, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { brl, fmtDate } from "@/lib/api";

export default function HistorySection({ history, onReplay }) {
  return (
    <section id="historico" className="scroll-mt-20">
      <div className="mb-6 flex items-center gap-3">
        <Trophy className="h-6 w-6 text-[#f59e0b]" />
        <h2 className="font-head text-2xl font-bold text-white sm:text-3xl">Histórico de Sorteios</h2>
      </div>
      {history.length === 0 ? (
        <div className="rounded-2xl border border-dashed border-[#2a303f] bg-[#131722]/60 p-10 text-center text-sm text-slate-500" data-testid="raffle-history-empty">
          Nenhum sorteio realizado ainda.
        </div>
      ) : (
        <div data-testid="raffle-history-list" className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {history.map((r, idx) => (
            <div key={r.id} className="group rounded-2xl border border-[#2a303f] bg-[#131722] p-5 transition-colors hover:border-[#ff2e55]/60">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-xs font-bold uppercase tracking-widest text-slate-500">Prêmio</p>
                  <h3 className="font-head text-lg font-bold text-white">{r.title}</h3>
                </div>
                <span className="flex items-center gap-1 text-xs text-slate-500">
                  <Calendar className="h-3 w-3" /> {fmtDate(r.created_at)}
                </span>
              </div>
              <div className="mt-4 rounded-xl border border-[#f59e0b]/30 bg-[#f59e0b]/10 p-3">
                <p className="text-xs uppercase tracking-widest text-[#f59e0b]">Ganhador</p>
                <p className="font-head text-lg font-extrabold text-white">{r.winner?.name}</p>
                <p className="font-mono text-xs text-slate-400">Cupom #{r.winner?.coupon}</p>
              </div>
              <div className="mt-4 flex items-center justify-between text-xs text-slate-400">
                <span className="flex items-center gap-1"><Users className="h-3 w-3" /> {r.participants}</span>
                <span className="flex items-center gap-1"><Ticket className="h-3 w-3" /> {r.total_coupons} cupons</span>
                <span>{brl(r.amount)}</span>
              </div>
              <Button variant="outline" onClick={() => onReplay(r)} data-testid={`replay-draw-button-${idx + 1}`} className="mt-4 w-full border-[#2a303f] bg-transparent text-slate-200 hover:border-[#ff2e55] hover:bg-transparent hover:text-white">
                <Play className="mr-2 h-4 w-4" /> Ver replay do sorteio
              </Button>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
