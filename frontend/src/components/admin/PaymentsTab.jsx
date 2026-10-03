import { useEffect, useState } from "react";
import { KeyRound, Save, Loader2, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { api, errMsg } from "@/lib/api";
import { box, inp, lbl } from "@/components/admin/RaffleTab";

export default function PaymentsTab() {
  const [info, setInfo] = useState(null);
  const [mp, setMp] = useState("");
  const [ip, setIp] = useState("");
  const [saving, setSaving] = useState(false);

  const load = async () => {
    const { data } = await api.get("/admin/keys");
    setInfo(data);
    setIp(data.infinitepay_handle || "");
  };
  useEffect(() => { load().catch(() => {}); }, []);

  const save = async () => {
    setSaving(true);
    try {
      await api.put("/admin/keys", { mp_access_token: mp, infinitepay_handle: ip });
      setMp("");
      toast.success("Chaves salvas");
      load();
    } catch (e) {
      toast.error(errMsg(e));
    } finally {
      setSaving(false);
    }
  };

  const ok = (v) => v && <span className="ml-2 inline-flex items-center gap-1 text-[10px] font-bold text-[#10b981]"><CheckCircle2 className="h-3 w-3" /> CONFIGURADO</span>;

  return (
    <div className={`${box} space-y-4`}>
      <p className="flex items-center gap-2 text-sm text-slate-300">
        <KeyRound className="h-4 w-4 text-[#f59e0b]" /> As chaves ficam salvas no servidor e nunca aparecem no site.
      </p>
      <div>
        <Label className={lbl}>Mercado Pago — Access Token {ok(info?.mp_configured)}</Label>
        <Input data-testid="admin-mp-token-input" type="password" value={mp} onChange={(e) => setMp(e.target.value)} placeholder={info?.mp_access_token_masked || "APP_USR-..."} className={inp} />
      </div>
      <div>
        <Label className={lbl}>InfinitePay — Handle {ok(info?.infinitepay_configured)}</Label>
        <Input data-testid="admin-ip-handle-input" value={ip} onChange={(e) => setIp(e.target.value)} placeholder="sua-loja" className={inp} />
      </div>
      <Button onClick={save} disabled={saving} data-testid="admin-save-keys-button" className="h-10 w-full bg-gradient-to-r from-[#22d3ee] to-[#10b981] font-bold text-[#0d1018] hover:opacity-95">
        {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />} Salvar chaves
      </Button>
    </div>
  );
}
