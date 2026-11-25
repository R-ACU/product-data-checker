import { CircleAlert, FileQuestion, LayoutDashboard, ListChecks, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { FIRMS, currentFirm } from "@/lib/theme";
import { EmptyState } from "./EmptyState";

export function NotFound() {
  const first = FIRMS[currentFirm()].firstRoute;
  return (
    <Card className="not-found mx-auto max-w-2xl">
      <EmptyState
        icon={FileQuestion}
        title="Diese Ansicht gibt es nicht"
        text="Der Link führt zu keiner Ansicht des Produktdaten-Prüfers. Vielleicht wurde er gekürzt oder falsch abgetippt."
        action={
          <>
            <Button variant="primary" asChild>
              <a href={`#/${first}`}>
                <LayoutDashboard />
                Zur Startansicht
              </a>
            </Button>
            <Button asChild>
              <a href="#/pruefen">
                <ListChecks />
                Zur Prüfliste
              </a>
            </Button>
          </>
        }
      />
    </Card>
  );
}

export function LoadError({ message }: { message: string }) {
  return (
    <Card className="error-box mx-auto max-w-2xl">
      <EmptyState
        icon={CircleAlert}
        title="Daten konnten nicht geladen werden"
        text={
          <>
            data.json fehlt oder ist beschädigt ({message}). Zuerst <code className="rounded bg-muted px-1">uv run pdc build</code> ausführen, dann{" "}
            <code className="rounded bg-muted px-1">uv run pdc serve</code>.
          </>
        }
        action={
          <Button onClick={() => window.location.reload()}>
            <RotateCcw />
            Neu laden
          </Button>
        }
      />
    </Card>
  );
}

export function LoadingView() {
  return (
    <div className="space-y-6" aria-label="Lädt" role="status">
      <div className="space-y-2">
        <Skeleton className="h-8 w-[420px] max-w-full" />
        <Skeleton className="h-4 w-[560px] max-w-full" />
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-[134px] rounded-[16px]" />
        ))}
      </div>
      <div className="grid gap-4 xl:grid-cols-12">
        <Skeleton className="h-[420px] rounded-[16px] xl:col-span-8" />
        <Skeleton className="h-[420px] rounded-[16px] xl:col-span-4" />
      </div>
    </div>
  );
}
