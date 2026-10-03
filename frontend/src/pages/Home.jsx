import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Flame, Sparkles, Target, Users, Ticket, Trophy, Search, Loader2 } from "lucide-react";
import Navbar from "@/components/Navbar";
import PurchasePanel from "@/components/PurchasePanel";
import HistorySection from "@/components/HistorySection";
import DrawModal from "@/components/DrawModal";
import PaymentDialog from "@/components/PaymentDialog";
import CountdownBanner, { DrawPendingPanel, useCountdown } from "@/components/Countdown";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { api, brl, errMsg, maskPhone } from "@/lib/api";
import { toast } from "sonner";

const StatusBadge = ({ status, pending }) => {
  const s = pending
    ? { label: "SORTEANDO", cls: "bg-[#ff2e55]/15 text-[#ff2e55] border-[#ff2e55]/40" }
    : status === "active"
    ? { label: "EM ANDAMENTO", cls: "bg-[#10b981]/15 text-[#10b981] border-[#10b981]/40" }
    : { label: "SORTEADO", cls: "bg-[#f59e0b]/15 text-[#f59e0b] border-[#f59e0b]/40" };
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-3 py-1 text-xs font-bold tracking-widest ${s.cls}`}>
      <Flame className="h-3 w-3" /> {s.label}
    </span>
  );
};

const Stat = ({ icon: Icon, value, label, testid }) => (
  <div className="rounded-xl border border-[#2a303f] bg-[#0d1018] p-3 text-center" data-testid={testid}>
    <Icon className="mx-auto mb-1 h-4 w-4 text-[#ff2e55]" />
    <p className="font-head text-lg font-extrabold text-white">{value}</p>
    <p className="text-[10px] uppercase tracking-widest text-slate-500">{label}</p>
  </div>
);

export default function Home() {
  const [raffle, setRaffle] = useState(null);
  const [history, setHistory] = useState([]);
  const [replay, setReplay] = useState(null);
  const [live, setLive] = useState(null);
  const [order, setOrder] = useState(null);
  const [mine, setMine] = useState(false);
  const [lookupPhone, setLookupPhone] = useState("");
  const [lookupRes, setLookupRes] = useState(null);
  const [looking, setLooking] = useState(false);

  const load = useCallback(async () => {
    try {
      const [r, h] = await Promise.all([api.get("/raffle"), api.get("/history")]);
      setRaffle(r.data);
      setHistory(h.data);
    } catch {
      /* ignore */
    }
  }, []);

  // initial + periodic refresh, detect live draws
  useEffect(() => {
    load();
    const checkLive = async () => {
      try {
        const { data } = await api.get("/draws/latest");
        if (!data?.id) return;
        const age = Date.now() - new Date(data.created_at).getTime();
        const seen = JSON.parse(localStorage.getItem("sz_seen_draws") || "[]");
        if (age < 3 * 60 * 1000 && !seen.includes(data.id)) {
          localStorage.setItem("sz_seen_draws", JSON.stringify([...seen, data.id].slice(-50)));
          setLive(data);
          load();
        }
      } catch {
        /* ignore */
      }
    };
    checkLive();
    const t1 = setInterval(load, 5000);
    const t2 = setInterval(checkLive, 4000);
    return () => {
      clearInterval(t1);
      clearInterval(t2);
    };
  }, [load]);

  const doLookup = async () => {
    setLooking(true);
    try {
      const { data } = await api.get("/coupons/lookup", { params: { whatsapp: lookupPhone } });
      setLookupRes(data);
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setLooking(false);
    }
  };

  const pct = raffle?.percent || 0;
  const left = useCountdown(raffle);
  const pending = left !== null;

  // near/after zero: poll fast so everyone sees the live draw right away
  useEffect(() => {
    if (!pending || left > 8000) return;
    const t = setInterval(async () => {
      try {
        const { data } = await api.get("/draws/latest");
        const seen = JSON.parse(localStorage.getItem("sz_seen_draws") || "[]");
        if (data?.id && data.raffle_id === raffle?.id && !seen.includes(data.id)) {
          localStorage.setItem("sz_seen_draws", JSON.stringify([...seen, data.id].slice(-50)));
          setLive(data);
          load();
        }
      } catch {
        /* ignore */
      }
    }, 1500);
    return () => clearInterval(t);
  }, [pending, left !== null && left <= 8000, raffle?.id, load]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="min-h-screen bg-grid">
      <Navbar onMyCoupons={() => setMine(true)} />
      <main className="mx-auto max-w-7xl space-y-14 px-4 py-8 sm:px-6 lg:px-8">
        {pending && <CountdownBanner left={left} />}
        {!raffle ? (
          <div className="flex h-[60vh] items-center justify-center text-slate-400"><Loader2 className="h-8 w-8 animate-spin" /></div>
        ) : (
          <section className="grid grid-cols-1 items-stretch gap-6 lg:grid-cols-12">
            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }} className="relative overflow-hidden rounded-2xl border border-[#2a303f] bg-gradient-to-br from-[#131722] to-[#0d1018] p-6 shadow-2xl lg:col-span-7">
              <div className="mb-4 flex items-center justify-between">
                <StatusBadge status={raffle.status} pending={pending} />
                <span className="flex items-center gap-1 text-xs font-bold uppercase tracking-widest text-[#f59e0b]">
                  <Sparkles className="h-3 w-3" /> Sorteio Premiado
                </span>
              </div>
              <div className="overflow-hidden rounded-xl">
                {raffle.image_url && (
                  <img alt={raffle.title} src={raffle.image_url} className="h-56 w-full object-cover transition-transform duration-700 hover:scale-105 sm:h-72" />
                )}
              </div>
              <h1 className="mt-5 font-head text-3xl font-extrabold tracking-tight text-white sm:text-4xl lg:text-5xl" data-testid="raffle-title">{raffle.title}</h1>
              <p className="mt-2 max-w-xl text-sm text-slate-400 sm:text-base">{raffle.description}</p>

              {raffle.status === "drawn" && raffle.winner && (
                <div className="mt-5 rounded-xl border border-[#f59e0b]/30 bg-[#f59e0b]/10 p-4" data-testid="current-winner-box">
                  <p className="flex items-center gap-1 text-xs font-bold uppercase tracking-widest text-[#f59e0b]"><Trophy className="h-3 w-3" /> Ganhador</p>
                  <p className="font-head text-2xl font-extrabold text-white">{raffle.winner.name}</p>
                  <p className="font-mono text-xs text-slate-400">Cupom #{raffle.winner.coupon}</p>
                </div>
              )}

              <div className="mt-6">
                <div className="mb-2 flex items-end justify-between">
                  <span className="flex items-center gap-1 text-xs font-bold uppercase tracking-widest text-slate-400">
                    <Target className="h-3 w-3" /> Meta: {brl(raffle.goal)}
                  </span>
                  <span data-testid="raffle-goal-percentage" className="font-head text-2xl font-extrabold text-shine">{pct}%</span>
                </div>
                <div data-testid="raffle-goal-progress-bar" className="h-5 w-full overflow-hidden rounded-full border border-[#2a303f] bg-[#0d1018]">
                  <motion.div initial={{ width: 0 }} animate={{ width: `${pct}%` }} transition={{ duration: 1.2, ease: "easeOut" }} className="h-full rounded-full bg-gradient-to-r from-[#e50914] via-[#ff2e55] to-[#f59e0b]" />
                </div>
                <p className="mt-2 text-xs text-slate-500">{brl(raffle.progress_total)} arrecadados de {brl(raffle.goal)}</p>
              </div>
              <div className="mt-6 grid grid-cols-3 gap-3">
                <Stat icon={Users} value={raffle.participants} label="Participantes" testid="stat-participants" />
                <Stat icon={Ticket} value={raffle.coupons} label="Cupons" testid="stat-coupons" />
                <Stat icon={Trophy} value={brl(raffle.price)} label="Cupom" testid="stat-price" />
              </div>
            </motion.div>
            <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.1 }} className="lg:col-span-5">
              {pending ? <DrawPendingPanel left={left} /> : <PurchasePanel raffle={raffle} onOrder={setOrder} />}
            </motion.div>
          </section>
        )}
        <HistorySection history={history} onReplay={setReplay} />
      </main>
      <footer className="border-t border-[#2a303f] py-6 text-center text-xs text-slate-600">
        SorteZeferius • sorte.zeferius.com.br • Jogue com responsabilidade
      </footer>

      <DrawModal open={!!replay} onOpenChange={(o) => !o && setReplay(null)} draw={replay} />
      <DrawModal open={!!live} onOpenChange={(o) => !o && setLive(null)} draw={live} live />
      <PaymentDialog order={order} open={!!order} onOpenChange={(o) => !o && setOrder(null)} onPaid={load} />

      <Dialog open={mine} onOpenChange={(o) => { setMine(o); if (!o) setLookupRes(null); }}>
        <DialogContent className="max-w-md border-[#2a303f] bg-[#131722] text-white sm:rounded-2xl">
          <DialogHeader>
            <DialogTitle className="font-head text-xl font-extrabold">Meus cupons</DialogTitle>
            <DialogDescription className="text-slate-400">Consulte seus números pelo WhatsApp usado na compra.</DialogDescription>
          </DialogHeader>
          <div className="flex gap-2">
            <Input data-testid="lookup-whatsapp-input" value={lookupPhone} onChange={(e) => setLookupPhone(maskPhone(e.target.value))} placeholder="(11) 99999-9999" className="border-[#2a303f] bg-[#0d1018] text-white placeholder:text-slate-600" />
            <Button onClick={doLookup} disabled={looking} data-testid="lookup-submit-button" className="bg-gradient-to-r from-[#e50914] to-[#ff2e55] text-white">
              {looking ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
            </Button>
          </div>
          {lookupRes && (
            <div data-testid="lookup-result">
              {lookupRes.coupons.length === 0 ? (
                <p className="text-center text-sm text-slate-500">Nenhum cupom pago encontrado.</p>
              ) : (
                <>
                  <p className="mb-2 text-sm text-slate-300">{lookupRes.name} • {lookupRes.coupons.length} cupom(ns)</p>
                  <div className="flex max-h-56 flex-wrap gap-2 overflow-auto">
                    {lookupRes.coupons.map((c) => (
                      <span key={c} className="rounded-lg border border-[#ff2e55]/40 bg-[#ff2e55]/10 px-2 py-1 font-mono text-sm">#{c}</span>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
