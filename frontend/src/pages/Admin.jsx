import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Shield, Home as HomeIcon, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { api, brl } from "@/lib/api";
import RaffleTab from "@/components/admin/RaffleTab";
import PaymentsTab from "@/components/admin/PaymentsTab";
import ParticipantsTab from "@/components/admin/ParticipantsTab";
import DrawTab from "@/components/admin/DrawTab";

const STATUS = { active: "Active", drawn: "Drawn", drawing: "Drawing", finished: "Finished" };

const Card = ({ label, value, cls = "text-white", testid }) => (
  <div className="rounded-xl border border-[#2a303f] bg-[#131722]/80 px-4 py-4" data-testid={testid}>
    <p className="text-xs uppercase tracking-widest text-slate-500">{label}</p>
    <p className={`font-head text-2xl font-extrabold ${cls}`}>{value}</p>
  </div>
);

export default function Admin() {
  const nav = useNavigate();
  const [ov, setOv] = useState(null);

  const load = useCallback(async () => {
    try {
      const { data } = await api.get("/admin/overview");
      setOv(data);
    } catch (e) {
      if (e?.response?.status === 401) {
        localStorage.removeItem("sz_token");
        nav("/admin/login");
      }
    }
  }, [nav]);

  useEffect(() => {
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, [load]);

  const logout = () => {
    localStorage.removeItem("sz_token");
    nav("/admin/login");
  };

  const trig = "rounded-md px-3 py-1.5 text-sm text-slate-400 data-[state=active]:bg-[#090b10] data-[state=active]:text-white data-[state=active]:shadow";

  return (
    <div className="min-h-screen bg-grid">
      <header className="sticky top-0 z-40 border-b border-[#2a303f] bg-[#090b10]/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-[#ff2e55]" />
            <span className="font-head text-base font-extrabold text-white">Painel SorteZeferius</span>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" onClick={() => nav("/")} data-testid="admin-site-button" className="text-slate-300 hover:bg-[#131722] hover:text-white">
              <HomeIcon className="h-4 w-4" /> Site
            </Button>
            <Button variant="outline" onClick={logout} data-testid="admin-logout-button" className="border-[#2a303f] bg-transparent text-slate-200 hover:border-[#ff2e55] hover:bg-transparent hover:text-white">
              <LogOut className="h-4 w-4" /> Sair
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-6">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Card label="Progresso" value={`${ov?.percent ?? 0}%`} cls="text-shine" testid="admin-stat-progress" />
          <Card label="Arrecadado" value={brl(ov?.raised)} testid="admin-stat-raised" />
          <Card label="Cupons" value={ov?.coupons ?? 0} testid="admin-stat-coupons" />
          <Card label="Status" value={STATUS[ov?.status] || "—"} testid="admin-stat-status" />
        </div>
        <Tabs defaultValue="sorteio" className="mt-6">
          <TabsList className="h-auto rounded-lg border border-[#2a303f]/40 bg-[#131722] p-1">
            <TabsTrigger value="sorteio" className={trig} data-testid="admin-tab-sorteio">Sorteio</TabsTrigger>
            <TabsTrigger value="pagamentos" className={trig} data-testid="admin-tab-pagamentos">Pagamentos</TabsTrigger>
            <TabsTrigger value="participantes" className={trig} data-testid="admin-tab-participantes">Participantes</TabsTrigger>
            <TabsTrigger value="sortear" className={trig} data-testid="admin-tab-sortear">Sortear</TabsTrigger>
          </TabsList>
          <TabsContent value="sorteio" className="mt-4">{ov && <RaffleTab ov={ov} onSaved={load} />}</TabsContent>
          <TabsContent value="pagamentos" className="mt-4"><PaymentsTab /></TabsContent>
          <TabsContent value="participantes" className="mt-4"><ParticipantsTab onChange={load} /></TabsContent>
          <TabsContent value="sortear" className="mt-4">{ov && <DrawTab ov={ov} onChange={load} />}</TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
