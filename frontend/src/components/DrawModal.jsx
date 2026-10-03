import { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Loader2 } from "lucide-react";
import DrawReel from "@/components/DrawReel";
import { api } from "@/lib/api";

export default function DrawModal({ open, onOpenChange, draw, drawId, live = false }) {
  const [full, setFull] = useState(null);

  useEffect(() => {
    if (!open) {
      setFull(null);
      return;
    }
    if (draw?.sequence) {
      setFull(draw);
      return;
    }
    const id = drawId || draw?.id;
    if (id) api.get(`/draws/${id}`).then((r) => setFull(r.data)).catch(() => setFull(null));
  }, [open, draw, drawId]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="w-[calc(100vw-2rem)] max-w-3xl overflow-hidden border-[#2a303f] bg-[#131722] p-6 text-white sm:rounded-2xl [&>*]:min-w-0" data-testid="draw-modal">
        <DialogHeader>
          <DialogTitle className="font-head text-xl font-extrabold">
            {live ? "Sorteio ao vivo" : "Replay"} — {full?.title || draw?.title || ""}
          </DialogTitle>
          <DialogDescription className="text-slate-400">
            A seta fixa indica o cupom sorteado. O nome abaixo acompanha a roleta em tempo real.
          </DialogDescription>
        </DialogHeader>
        {full ? (
          <DrawReel key={`${full.id}-${open}`} draw={full} />
        ) : (
          <div className="flex h-48 items-center justify-center text-slate-400">
            <Loader2 className="h-6 w-6 animate-spin" />
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
