import { useEffect, useState } from "react";
import { Plus, Users, Check, Trash2, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { toast } from "sonner";
import { api, brl, errMsg, maskPhone } from "@/lib/api";
import { box, inp } from "@/components/admin/RaffleTab";

const ST = {
  paid: { t: "Pago", c: "border-[#10b981]/40 bg-[#10b981]/15 text-[#10b981]" },
  pending: { t: "Pendente", c: "border-[#f59e0b]/40 bg-[#f59e0b]/15 text-[#f59e0b]" },
  cancelled: { t: "Cancelado", c: "border-slate-600 bg-slate-700/30 text-slate-400" },
};

export default function ParticipantsTab({ onChange }) {
  const [list, setList] = useState([]);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [qty, setQty] = useState(1);
  const [adding, setAdding] = useState(false);
  const [del, setDel] = useState(null);
  const [showAll, setShowAll] = useState(false);
  const paidList = list.filter((o) => o.status === "paid");
  const shown = showAll ? list : paidList;
  const pendingCount = list.length - paidList.length;

  const load = async () => {
    const { data } = await api.get("/admin/participants");
    setList(data);
  };
  useEffect(() => { load().catch(() => {}); }, []);

  const add = async () => {
    if (!name.trim()) return toast.error("Informe o nome");
    setAdding(true);
    try {
      const { data } = await api.post("/admin/participants", { name, whatsapp: phone, quantity: Number(qty) || 1 });
      toast.success(`${data.name} adicionado com ${data.coupons.length} cupom(ns)`);
      setName(""); setPhone(""); setQty(1);
      load(); onChange();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setAdding(false);
    }
  };

  const approve = async (id) => {
    try {
      await api.post(`/admin/participants/${id}/approve`);
      toast.success("Pagamento aprovado");
      load(); onChange();
    } catch (e) { toast.error(errMsg(e)); }
  };

  const remove = async () => {
    try {
      await api.delete(`/admin/participants/${del.id}`);
      toast.success("Removido");
      setDel(null); load(); onChange();
    } catch (e) { toast.error(errMsg(e)); }
  };

  return (
    <div className="space-y-4">
      <div className={box}>
        <h3 className="mb-4 flex items-center gap-2 font-head text-base font-bold text-white"><Plus className="h-4 w-4" /> Adicionar participante manual</h3>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-4">
          <Input data-testid="manual-name-input" placeholder="Nome" value={name} onChange={(e) => setName(e.target.value)} className={inp} />
          <Input data-testid="manual-whatsapp-input" placeholder="WhatsApp" value={phone} onChange={(e) => setPhone(maskPhone(e.target.value))} className={inp} />
          <Input data-testid="manual-qty-input" type="number" min="1" value={qty} onChange={(e) => setQty(e.target.value)} className={inp} />
          <Button onClick={add} disabled={adding} data-testid="manual-add-button" className="mt-1 h-9 bg-gradient-to-r from-[#e50914] to-[#ff2e55] font-bold text-white hover:opacity-95">
            {adding && <Loader2 className="h-4 w-4 animate-spin" />} Adicionar
          </Button>
        </div>
      </div>
      <div className={box}>
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <h3 className="flex items-center gap-2 font-head text-base font-bold text-white" data-testid="participants-count"><Users className="h-4 w-4" /> Participantes concorrendo ({paidList.length})</h3>
          <div className="flex rounded-lg border border-[#2a303f] bg-[#0d1018] p-1 text-xs">
            <button onClick={() => setShowAll(false)} data-testid="filter-paid" className={`rounded-md px-3 py-1 transition-colors ${!showAll ? "bg-[#131722] text-white" : "text-slate-400 hover:text-white"}`}>Concorrendo</button>
            <button onClick={() => setShowAll(true)} data-testid="filter-all" className={`rounded-md px-3 py-1 transition-colors ${showAll ? "bg-[#131722] text-white" : "text-slate-400 hover:text-white"}`}>Todos ({list.length}){pendingCount > 0 && ` • ${pendingCount} pendente(s)`}</button>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm" data-testid="participants-table">
            <thead>
              <tr className="text-left text-xs uppercase tracking-widest text-slate-500">
                <th className="py-2 pr-3 font-semibold">Nome</th>
                <th className="py-2 pr-3 font-semibold">WhatsApp</th>
                <th className="py-2 pr-3 font-semibold">Cupons</th>
                <th className="py-2 pr-3 font-semibold">Valor</th>
                <th className="py-2 pr-3 font-semibold">Status</th>
                <th className="py-2 font-semibold"></th>
              </tr>
            </thead>
            <tbody>
              {shown.length === 0 ? (
                <tr><td colSpan={6} className="py-8 text-center text-slate-500">Nenhum participante ainda</td></tr>
              ) : shown.map((o) => (
                <tr key={o.id} className="border-t border-[#2a303f] text-slate-200">
                  <td className="py-3 pr-3 font-semibold text-white">{o.name}<span className="block text-[10px] font-normal uppercase text-slate-500">{o.gateway}</span></td>
                  <td className="py-3 pr-3 text-slate-400">{o.whatsapp || "—"}</td>
                  <td className="py-3 pr-3">
                    <span className="font-bold">{o.quantity}</span>
                    {o.coupons?.length > 0 && (
                      <span className="block max-w-[220px] truncate font-mono text-[11px] text-slate-500" title={o.coupons.join(", ")}>#{o.coupons.join(" #")}</span>
                    )}
                  </td>
                  <td className="py-3 pr-3">{brl(o.amount)}</td>
                  <td className="py-3 pr-3"><Badge variant="outline" className={ST[o.status]?.c}>{ST[o.status]?.t || o.status}</Badge></td>
                  <td className="py-3 text-right">
                    <div className="flex justify-end gap-1">
                      {o.status === "pending" && (
                        <Button size="icon" variant="ghost" title="Aprovar pagamento" onClick={() => approve(o.id)} data-testid={`approve-${o.id}`} className="h-8 w-8 text-[#10b981] hover:bg-[#10b981]/15 hover:text-[#10b981]"><Check className="h-4 w-4" /></Button>
                      )}
                      <Button size="icon" variant="ghost" title="Remover" onClick={() => setDel(o)} data-testid={`delete-${o.id}`} className="h-8 w-8 text-slate-400 hover:bg-[#ff2e55]/15 hover:text-[#ff2e55]"><Trash2 className="h-4 w-4" /></Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <AlertDialog open={!!del} onOpenChange={(o) => !o && setDel(null)}>
        <AlertDialogContent className="border-[#2a303f] bg-[#131722] text-white">
          <AlertDialogHeader>
            <AlertDialogTitle>Remover participante?</AlertDialogTitle>
            <AlertDialogDescription className="text-slate-400">{del?.name} e seus cupons serão removidos deste sorteio.</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="border-[#2a303f] bg-transparent text-slate-200 hover:bg-[#0d1018] hover:text-white">Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={remove} data-testid="confirm-delete-button" className="bg-[#ff2e55] text-white hover:bg-[#e50914]">Remover</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
