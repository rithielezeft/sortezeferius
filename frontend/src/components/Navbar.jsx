import { useNavigate } from "react-router-dom";
import { Dice5, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function Navbar({ onMyCoupons }) {
  const nav = useNavigate();
  const goHistory = () => document.getElementById("historico")?.scrollIntoView({ behavior: "smooth" });
  return (
    <header className="sticky top-0 z-40 border-b border-[#2a303f] bg-[#090b10]/80 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
        <button data-testid="navbar-brand-logo" onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })} className="flex items-center gap-2">
          <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-[#e50914] to-[#ff2e55] btn-glow">
            <Dice5 className="h-5 w-5 text-white" />
          </span>
          <span className="font-head text-lg font-extrabold tracking-tight text-white">
            Sorte<span className="text-[#ff2e55]">Zeferius</span>
          </span>
        </button>
        <div className="flex items-center gap-1 sm:gap-2">
          <Button variant="ghost" onClick={onMyCoupons} data-testid="navbar-my-coupons-button" className="hidden text-slate-300 hover:bg-[#131722] hover:text-white sm:inline-flex">
            Meus cupons
          </Button>
          <Button variant="ghost" onClick={goHistory} data-testid="navbar-history-button" className="text-slate-300 hover:bg-[#131722] hover:text-white">
            Histórico
          </Button>
          <Button variant="outline" onClick={() => nav("/admin")} data-testid="navbar-admin-button" className="border-[#2a303f] bg-transparent text-slate-200 hover:border-[#ff2e55] hover:bg-transparent hover:text-white">
            <Shield className="h-4 w-4" /> Painel
          </Button>
        </div>
      </div>
    </header>
  );
}
