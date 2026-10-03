import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { CheckCircle2, Loader2, Clock, Ticket } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

export default function PaymentReturn() {
  const [params] = useSearchParams();
  const nav = useNavigate();
  const [order, setOrder] = useState(null);
  const [tries, setTries] = useState(0);

  useEffect(() => {
    const order_nsu = params.get("order_nsu") || localStorage.getItem("sz_last_order");
    if (!order_nsu) return;
    let stop = false;
    const run = async () => {
      try {
        const { data } = await api.post("/orders/infinitepay/confirm", {
          order_nsu,
          transaction_nsu: params.get("transaction_nsu") || params.get("transaction_id"),
          slug: params.get("slug") || params.get("invoice_slug"),
        });
        if (stop) return;
        setOrder(data);
        if (data.status !== "paid") setTimeout(() => !stop && setTries((t) => t + 1), 4000);
      } catch {
        /* ignore */
      }
    };
    if (tries < 15) run();
    return () => { stop = true; };
  }, [params, tries]);

  const paid = order?.status === "paid";
  return (
    <div className="flex min-h-screen items-center justify-center bg-grid px-4">
      <div className="w-full max-w-md rounded-2xl border border-[#2a303f] bg-[#131722] p-8 text-center text-white shadow-2xl" data-testid="payment-return">
        {paid ? <CheckCircle2 className="mx-auto h-14 w-14 text-[#10b981]" /> : order ? <Clock className="mx-auto h-14 w-14 text-[#f59e0b]" /> : <Loader2 className="mx-auto h-10 w-10 animate-spin text-slate-400" />}
        <h1 className="mt-4 font-head text-2xl font-extrabold">{paid ? "Pagamento confirmado!" : "Confirmando pagamento..."}</h1>
        <p className="mt-1 text-sm text-slate-400">{paid ? "Seus números da sorte:" : "Isso pode levar alguns segundos."}</p>
        {paid && (
          <div className="mt-4 flex max-h-48 flex-wrap justify-center gap-2 overflow-auto">
            {order.coupons.map((c) => (
              <span key={c} className="flex items-center gap-1 rounded-lg border border-[#ff2e55]/40 bg-[#ff2e55]/10 px-2 py-1 font-mono text-sm"><Ticket className="h-3 w-3 text-[#ff2e55]" />#{c}</span>
            ))}
          </div>
        )}
        <Button onClick={() => nav("/")} data-testid="payment-return-home-button" className="mt-6 w-full bg-gradient-to-r from-[#e50914] to-[#ff2e55] font-bold text-white">Voltar ao sorteio</Button>
      </div>
    </div>
  );
}
