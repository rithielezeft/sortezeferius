import { useState } from "react";
import { Dice5, RotateCcw, Trophy, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { toast } from "sonner";
import DrawModal from "@/components/DrawModal";
import { api, errMsg } from "@/lib/api";
import { useCountdown, fmtMs } from "@/components/Countdown";
import { box, inp } from "@/components/admin/RaffleTab";

export default function DrawTab({ ov, onChange }) {
  const [extra, setExtra] = useState(ov.manual_extra ?? 0);
  const [drawing, setDrawing] = useState(false);
  const [draw, setDraw] = useState(null);
  const [confirmNew, setConfirmNew] = useState(false);
  const left = useCountdown(ov);

  const applyExtra = async () => {
    try {
      await api.post("/admin/raffle/extra", { amount: Number(extra) || 0 });
      toast.success("Progresso ajustado");
      onChange();
    } catch (e) { toast.error(errMsg(e)); }
  };

  const doDraw = async () => {
    setDrawing(true);
    try {
      const { data } = await api.post("/admin/draw");
      const seen = JSON.parse(localStorage.getItem("sz_seen_draws") || "[]");
      localStorage.setItem("sz_seen_draws", JSON.stringify([...seen, data.id].slice(-50)));
      setDraw(data);
      onChange();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setDrawing(false);
    }
  };

  const doNew = async () => {
    try {
      await api.post("/admin/raffle/new");
      toast.success("Novo sorteio iniciado");
      setConfirmNew(false);
      onChange();
    } catch (e) { toast.error(errMsg(e)); }
  };

  return (
    <div className="space-y-4">
      <div className={box}>
        <h3 className="font-head text-base font-bold text-white">Ajuste manual de progresso</h3>
        <p className="mt-1 text-sm text-slate-400">Adicione um valor extra (R$) à barra de progresso, somado às vendas reais.</p>
        <div className="mt-3 flex gap-3">
          <Input data-testid="extra-input" type="number" value={extra} onChange={(e) => setExtra(e.target.value)} className={`${inp} mt-0`} />
          <Button onClick={applyExtra} data-testid="extra-apply-button" className="bg-[#f59e0b] font-bold text-[#0d1018] hover:bg-[#fbbf24]">Aplicar</Button>
        </div>
      </div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className={`${box} text-center`}>
          <Dice5 className="mx-auto h-9 w-9 text-[#ff2e55]" />
          <h3 className="mt-3 font-head text-base font-bold text-white">Realizar sorteio</h3>
          <p className="text-sm text-slate-400">Escolhe aleatoriamente um cupom pago e exibe a animação no site.</p>
          {left !== null && (
            <p className="mt-2 text-sm font-bold text-[#ff2e55]" data-testid="admin-countdown">Meta atingida! Sorteio automático em {fmtMs(left)}</p>
          )}
          {ov.status === "drawn" && ov.winner && (
            <p className="mt-2 text-sm text-[#f59e0b]">Ganhador: <b>{ov.winner.name}</b> • #{ov.winner.coupon}</p>
          )}
          <Button onClick={doDraw} disabled={drawing || ov.status !== "active"} data-testid="draw-now-button" className="mt-4 h-10 w-full bg-gradient-to-r from-[#e50914] to-[#ff2e55] font-bold text-white hover:opacity-95">
            {drawing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Trophy className="h-4 w-4" />} {ov.status === "active" ? "Sortear agora" : "Já sorteado"}
          </Button>
        </div>
        <div className={`${box} text-center`}>
          <RotateCcw className="mx-auto h-9 w-9 text-[#22d3ee]" />
          <h3 className="mt-3 font-head text-base font-bold text-white">Novo sorteio</h3>
          <p className="text-sm text-slate-400">Encerra o atual e inicia um novo sorteio zerado.</p>
          <Button variant="outline" onClick={() => setConfirmNew(true)} data-testid="new-raffle-button" className="mt-4 h-10 w-full border-[#2a303f] bg-transparent text-slate-200 hover:border-[#22d3ee] hover:bg-transparent hover:text-white">
            <RotateCcw className="h-4 w-4" /> Iniciar novo
          </Button>
        </div>
      </div>
      <DrawModal open={!!draw} onOpenChange={(o) => !o && setDraw(null)} draw={draw} live />
      <AlertDialog open={confirmNew} onOpenChange={setConfirmNew}>
        <AlertDialogContent className="border-[#2a303f] bg-[#131722] text-white">
          <AlertDialogHeader>
            <AlertDialogTitle>Iniciar novo sorteio?</AlertDialogTitle>
            <AlertDialogDescription className="text-slate-400">O sorteio atual será encerrado e um novo começará zerado (mesmas configurações).</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="border-[#2a303f] bg-transparent text-slate-200 hover:bg-[#0d1018] hover:text-white">Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={doNew} data-testid="confirm-new-raffle-button" className="bg-[#22d3ee] font-bold text-[#0d1018] hover:bg-[#67e8f9]">Iniciar</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
