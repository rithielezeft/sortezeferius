import { useEffect, useState } from "react";
import { Minus, Plus, Ticket, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { api, brl, errMsg, maskPhone } from "@/lib/api";

const QUICK_PACKS = [1, 5, 10, 20, 50, 100];

export default function PurchasePanel({ raffle, onOrder }) {
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [qty, setQty] = useState(5);
  const [gateway, setGateway] = useState(raffle?.default_gateway || "mercadopago");
  const [loading, setLoading] = useState(false);
  const price = Number(raffle?.price || 0);
  const closed = raffle?.status !== "active";
  const subtotal = Math.round(qty * price * 100) / 100;
  const feePct = Number(raffle?.mp_fee_percent ?? 0.99);
  const fee = gateway === "mercadopago" ? Math.round((Math.round(subtotal * 100) * Math.round(feePct * 100)) / 10000) / 100 : 0;

  useEffect(() => {
    if (raffle?.default_gateway) setGateway(raffle.default_gateway);
  }, [raffle?.default_gateway]);

  const submit = async () => {
    if (name.trim().length < 2) return toast.error("Informe seu nome completo");
    if (phone.replace(/\D/g, "").length < 10) return toast.error("Informe um WhatsApp válido");
    setLoading(true);
    try {
      const { data } = await api.post("/orders", { name, whatsapp: phone, quantity: qty, gateway });
      localStorage.setItem("sz_last_order", data.id);
      onOrder(data);
    } catch (e) {
      toast.error(errMsg(e, "Não foi possível gerar o pagamento"));
    } finally {
      setLoading(false);
    }
  };

  const gwBtn = (id, label, sub, color) => {
    const on = gateway === id;
    return (
      <button
        data-testid={`payment-gateway-${id}-option`}
        onClick={() => setGateway(id)}
        className={`rounded-lg border px-3 py-3 text-sm font-semibold transition-colors ${
          on ? color : "border-[#2a303f] bg-[#0d1018] text-slate-300 hover:border-slate-500"
        }`}
      >
        {label}
        <span className="block text-[10px] font-normal text-slate-400">{sub}</span>
      </button>
    );
  };

  return (
    <div data-testid="purchase-panel" className="flex flex-col gap-5 rounded-2xl border border-[#2a303f] bg-[#131722] p-6 shadow-2xl">
      <div>
        <h3 className="font-head text-xl font-bold text-white">Garanta seus cupons</h3>
        <p className="text-sm text-slate-400">{brl(price)} por cupom • quanto mais, mais chances</p>
      </div>
      <div className="space-y-3">
        <div>
          <Label className="text-xs font-bold uppercase tracking-widest text-slate-400">Nome completo</Label>
          <Input data-testid="participant-name-input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Seu nome" className="mt-1 border-[#2a303f] bg-[#0d1018] text-white placeholder:text-slate-600" />
        </div>
        <div>
          <Label className="text-xs font-bold uppercase tracking-widest text-slate-400">WhatsApp</Label>
          <Input data-testid="participant-whatsapp-input" inputMode="numeric" value={phone} onChange={(e) => setPhone(maskPhone(e.target.value))} placeholder="(11) 99999-9999" className="mt-1 border-[#2a303f] bg-[#0d1018] text-white placeholder:text-slate-600" />
        </div>
      </div>
      <div>
        <Label className="text-xs font-bold uppercase tracking-widest text-slate-400">Quantidade de cupons</Label>
        <div className="mt-2 flex items-center gap-3" data-testid="coupon-quantity-selector">
          <button data-testid="coupon-qty-minus" onClick={() => setQty((q) => Math.max(1, q - 1))} className="flex h-10 w-10 items-center justify-center rounded-lg border border-[#2a303f] bg-[#0d1018] text-white transition-colors hover:border-[#ff2e55]">
            <Minus className="h-4 w-4" />
          </button>
          <div className="flex h-10 flex-1 items-center justify-center rounded-lg border border-[#2a303f] bg-[#0d1018] text-lg font-bold text-white" data-testid="coupon-qty-value">{qty}</div>
          <button data-testid="coupon-qty-plus" onClick={() => setQty((q) => Math.min(10000, q + 1))} className="flex h-10 w-10 items-center justify-center rounded-lg border border-[#2a303f] bg-[#0d1018] text-white transition-colors hover:border-[#ff2e55]">
            <Plus className="h-4 w-4" />
          </button>
        </div>
        <div className="mt-3 grid grid-cols-3 gap-2">
          {QUICK_PACKS.map((p) => (
            <button
              key={p}
              data-testid={`coupon-quick-pack-${p}`}
              onClick={() => setQty(p)}
              className={`rounded-lg border py-2 text-sm font-bold transition-colors ${
                qty === p ? "border-[#ff2e55] bg-[#ff2e55]/15 text-white" : "border-[#2a303f] bg-[#0d1018] text-slate-300 hover:border-[#ff2e55]/60"
              }`}
            >
              +{p}
            </button>
          ))}
        </div>
      </div>
      <div>
        <Label className="text-xs font-bold uppercase tracking-widest text-slate-400">Forma de pagamento</Label>
        <div className="mt-2 grid grid-cols-2 gap-2">
          {gwBtn("mercadopago", "Mercado Pago", "PIX instantâneo", "border-[#00b1ea] bg-[#00b1ea]/15 text-white")}
          {gwBtn("infinitepay", "InfinitePay", "PIX / Cartão", "border-[#10b981] bg-[#10b981]/15 text-white")}
        </div>
      </div>
      <div className="rounded-xl border border-[#2a303f] bg-[#0d1018] px-4 py-3" data-testid="purchase-summary">
        {fee > 0 && (
          <div className="mb-2 space-y-1 border-b border-[#2a303f] pb-2 text-xs text-slate-400">
            <div className="flex justify-between"><span>{qty} cupom(ns)</span><span data-testid="purchase-subtotal">{brl(subtotal)}</span></div>
            <div className="flex justify-between"><span>Taxa Mercado Pago ({feePct.toLocaleString("pt-BR")}%)</span><span data-testid="purchase-fee">+ {brl(fee)}</span></div>
          </div>
        )}
        <div className="flex items-center justify-between">
          <span className="text-sm text-slate-400">Total</span>
          <span className="font-head text-2xl font-extrabold text-[#f59e0b]" data-testid="purchase-total">{brl(subtotal + fee)}</span>
        </div>
      </div>
      <Button onClick={submit} disabled={loading || closed} data-testid="buy-coupons-submit-button" className="btn-glow h-12 w-full bg-gradient-to-r from-[#e50914] to-[#ff2e55] text-base font-extrabold text-white hover:opacity-95">
        {loading ? <Loader2 className="mr-2 h-5 w-5 animate-spin" /> : <Ticket className="mr-2 h-5 w-5" />}
        {closed ? "Sorteio encerrado" : "Comprar e concorrer"}
      </Button>
    </div>
  );
}
