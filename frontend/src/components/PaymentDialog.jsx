import { useEffect, useRef, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Copy, Loader2, CheckCircle2, ExternalLink, Ticket } from "lucide-react";
import { toast } from "sonner";
import { api, brl } from "@/lib/api";

export default function PaymentDialog({ order, open, onOpenChange, onPaid }) {
  const [o, setO] = useState(order);
  const timer = useRef(null);

  useEffect(() => setO(order), [order]);

  useEffect(() => {
    clearInterval(timer.current);
    if (!open || !order?.id) return;
    timer.current = setInterval(async () => {
      try {
        const { data } = await api.get(`/orders/${order.id}`);
        setO(data);
        if (data.status !== "pending") {
          clearInterval(timer.current);
          if (data.status === "paid") {
            toast.success("Pagamento confirmado! Boa sorte!");
            onPaid?.(data);
          }
        }
      } catch {
        /* ignore */
      }
    }, 5000);
    return () => clearInterval(timer.current);
  }, [open, order?.id, onPaid]);

  const copy = () => {
    navigator.clipboard?.writeText(o?.pix_qr_code || "");
    toast.success("Código PIX copiado!");
  };

  if (!o) return null;
  const paid = o.status === "paid";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md border-[#2a303f] bg-[#131722] text-white sm:rounded-2xl" data-testid="payment-dialog">
        <DialogHeader>
          <DialogTitle className="font-head text-xl font-extrabold">
            {paid ? "Pagamento confirmado" : "Finalize seu pagamento"}
          </DialogTitle>
          <DialogDescription className="text-slate-400">
            {o.quantity} cupom(ns){o.fee > 0 && ` + taxa ${brl(o.fee)}`} • <span className="font-bold text-[#f59e0b]">{brl(o.total_charged ?? o.amount)}</span>
          </DialogDescription>
        </DialogHeader>

        {paid ? (
          <div className="winner-pop text-center" data-testid="payment-success">
            <CheckCircle2 className="mx-auto h-14 w-14 text-[#10b981]" />
            <p className="mt-3 text-sm text-slate-300">Seus números da sorte:</p>
            <div className="mt-3 flex max-h-48 flex-wrap justify-center gap-2 overflow-auto">
              {(o.coupons || []).map((c) => (
                <span key={c} className="flex items-center gap-1 rounded-lg border border-[#ff2e55]/40 bg-[#ff2e55]/10 px-2 py-1 font-mono text-sm">
                  <Ticket className="h-3 w-3 text-[#ff2e55]" />#{c}
                </span>
              ))}
            </div>
          </div>
        ) : o.gateway === "mercadopago" ? (
          <div className="space-y-4">
            {o.pix_qr_base64 && (
              <div className="mx-auto w-fit rounded-xl bg-white p-3">
                <img alt="QR Code PIX" src={`data:image/png;base64,${o.pix_qr_base64}`} className="h-52 w-52" data-testid="pix-qr-image" />
              </div>
            )}
            <div className="rounded-lg border border-[#2a303f] bg-[#0d1018] p-3">
              <p className="mb-1 text-[10px] font-bold uppercase tracking-widest text-slate-500">PIX copia e cola</p>
              <p className="break-all font-mono text-xs text-slate-300" data-testid="pix-copy-code">{o.pix_qr_code}</p>
            </div>
            <Button onClick={copy} data-testid="pix-copy-button" className="h-11 w-full bg-gradient-to-r from-[#e50914] to-[#ff2e55] font-bold text-white hover:opacity-95">
              <Copy className="h-4 w-4" /> Copiar código PIX
            </Button>
            <p className="flex items-center justify-center gap-2 text-xs text-slate-400">
              <Loader2 className="h-3 w-3 animate-spin" /> Aguardando confirmação do pagamento...
            </p>
          </div>
        ) : (
          <div className="space-y-4 text-center">
            <p className="text-sm text-slate-300">Você será levado ao checkout seguro da InfinitePay (PIX ou Cartão).</p>
            <Button asChild data-testid="infinitepay-checkout-button" className="h-11 w-full bg-gradient-to-r from-[#e50914] to-[#ff2e55] font-bold text-white hover:opacity-95">
              <a href={o.checkout_url} target="_self" rel="noreferrer">
                <ExternalLink className="h-4 w-4" /> Ir para o pagamento
              </a>
            </Button>
            <p className="flex items-center justify-center gap-2 text-xs text-slate-400">
              <Loader2 className="h-3 w-3 animate-spin" /> Aguardando confirmação...
            </p>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
