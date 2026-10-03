import { useState } from "react";
import { Save, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { api, errMsg } from "@/lib/api";

export const box = "rounded-2xl border border-[#2a303f] bg-[#131722]/80 p-6";
export const inp = "mt-1 border-[#2a303f] bg-[#0d1018] text-white placeholder:text-slate-600";
export const lbl = "text-xs font-medium uppercase tracking-widest text-slate-400";

export default function RaffleTab({ ov, onSaved }) {
  const [f, setF] = useState({
    title: ov.title || "", description: ov.description || "", image_url: ov.image_url || "",
    goal: ov.goal ?? 0, price: ov.price ?? 0, default_gateway: ov.default_gateway || "mercadopago",
  });
  const [saving, setSaving] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const save = async () => {
    setSaving(true);
    try {
      await api.put("/admin/raffle", { ...f, goal: Number(f.goal), price: Number(f.price) });
      toast.success("Configurações salvas");
      onSaved();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setSaving(false);
    }
  };

  const gw = (id, label) => (
    <button
      onClick={() => setF({ ...f, default_gateway: id })}
      data-testid={`admin-gateway-${id}`}
      className={`h-10 rounded-lg border text-sm font-semibold transition-colors ${
        f.default_gateway === id ? "border-[#ff2e55] bg-[#ff2e55]/15 text-white" : "border-[#2a303f] bg-[#0d1018] text-slate-300 hover:border-slate-500"
      }`}
    >
      {label}
    </button>
  );

  return (
    <div className={`${box} space-y-4`}>
      <div>
        <Label className={lbl}>Título do prêmio</Label>
        <Input data-testid="admin-title-input" value={f.title} onChange={set("title")} className={inp} />
      </div>
      <div>
        <Label className={lbl}>Descrição</Label>
        <Textarea data-testid="admin-description-input" value={f.description} onChange={set("description")} className={inp} />
      </div>
      <div>
        <Label className={lbl}>URL da imagem</Label>
        <Input data-testid="admin-image-input" value={f.image_url} onChange={set("image_url")} className={inp} />
      </div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <Label className={lbl}>Meta (R$)</Label>
          <Input data-testid="admin-goal-input" type="number" min="0" value={f.goal} onChange={set("goal")} className={inp} />
        </div>
        <div>
          <Label className={lbl}>Preço por cupom (R$)</Label>
          <Input data-testid="admin-price-input" type="number" min="0" step="0.01" value={f.price} onChange={set("price")} className={inp} />
        </div>
      </div>
      <div>
        <Label className={lbl}>Gateway padrão</Label>
        <div className="mt-2 grid grid-cols-2 gap-2">
          {gw("mercadopago", "Mercado Pago")}
          {gw("infinitepay", "InfinitePay")}
        </div>
      </div>
      <Button onClick={save} disabled={saving} data-testid="admin-save-raffle-button" className="h-10 w-full bg-gradient-to-r from-[#e50914] to-[#ff2e55] font-bold text-white hover:opacity-95">
        {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} Salvar configurações
      </Button>
    </div>
  );
}
