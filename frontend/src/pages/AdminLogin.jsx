import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Shield, Loader2, LogIn } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { api, errMsg } from "@/lib/api";

export default function AdminLogin() {
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const { data } = await api.post("/auth/login", { email, password });
      localStorage.setItem("sz_token", data.token);
      nav("/admin");
    } catch (err) {
      toast.error(errMsg(err, "Falha no login"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-grid px-4">
      <form onSubmit={submit} className="w-full max-w-sm rounded-2xl border border-[#2a303f] bg-[#131722] p-8 shadow-2xl" data-testid="admin-login-form">
        <div className="mb-6 flex items-center gap-2">
          <Shield className="h-5 w-5 text-[#ff2e55]" />
          <h1 className="font-head text-xl font-extrabold text-white">Painel SorteZeferius</h1>
        </div>
        <div className="space-y-4">
          <div>
            <Label className="text-xs font-bold uppercase tracking-widest text-slate-400">Email</Label>
            <Input data-testid="admin-email-input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} className="mt-1 border-[#2a303f] bg-[#0d1018] text-white" required />
          </div>
          <div>
            <Label className="text-xs font-bold uppercase tracking-widest text-slate-400">Senha</Label>
            <Input data-testid="admin-password-input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} className="mt-1 border-[#2a303f] bg-[#0d1018] text-white" required />
          </div>
          <Button type="submit" disabled={loading} data-testid="admin-login-submit" className="btn-glow h-11 w-full bg-gradient-to-r from-[#e50914] to-[#ff2e55] font-bold text-white hover:opacity-95">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <LogIn className="h-4 w-4" />} Entrar
          </Button>
          <button type="button" onClick={() => nav("/")} className="w-full text-center text-xs text-slate-500 hover:text-slate-300">Voltar ao site</button>
        </div>
      </form>
    </div>
  );
}
