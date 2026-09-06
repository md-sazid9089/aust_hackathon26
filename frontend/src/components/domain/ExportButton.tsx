import { useState } from 'react';
import { Download, FileText } from 'lucide-react';
import { toast } from 'sonner';
import { useApi, ApiError } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/primitives';
import { downloadBlob } from '@/lib/format';

/** F-021: export accepted findings (default) or all. PDF falls back to Markdown when the backend reports 503. */
export function ExportButton({ runId, filename, acceptedCount }: { runId: string; filename: string; acceptedCount: number }) {
  const api = useApi();
  const [busy, setBusy] = useState(false);

  const run = async (format: 'md' | 'pdf', include: 'accepted' | 'all') => {
    setBusy(true);
    try {
      const blob = await api.exportRun(runId, format, include);
      downloadBlob(blob, `${filename}-${include}.${format}`);
      toast.success(`Exported ${include} findings as ${format.toUpperCase()}`);
    } catch (e) {
      if (format === 'pdf' && e instanceof ApiError && e.status === 503) {
        toast.message('PDF export is not available on this server — downloading Markdown instead.');
        await run('md', include);
        return;
      }
      toast.error(e instanceof Error ? e.message : 'Export failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" loading={busy}>
          <Download aria-hidden /> Export
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuLabel>Accepted findings ({acceptedCount})</DropdownMenuLabel>
        <DropdownMenuItem onSelect={() => void run('md', 'accepted')} disabled={acceptedCount === 0}>
          <FileText aria-hidden /> Markdown
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => void run('pdf', 'accepted')} disabled={acceptedCount === 0}>
          <FileText aria-hidden /> PDF
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuLabel>Everything</DropdownMenuLabel>
        <DropdownMenuItem onSelect={() => void run('md', 'all')}>
          <FileText aria-hidden /> Markdown (all)
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
