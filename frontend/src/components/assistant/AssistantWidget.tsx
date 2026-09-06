import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { ArrowRight, Bot, CheckCircle2, Loader2, MessageSquare, Paperclip, Send, Trash2, X, XCircle } from 'lucide-react';
import { useApi } from '@/lib/api';
import { ApiError } from '@/lib/api/types';
import type { AssistantAction, ChatMessage } from '@/lib/types/api';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/input';
import { cn } from '@/lib/format';
import { Markdown } from './Markdown';

interface Turn extends ChatMessage {
  id: string;
  actions?: AssistantAction[];
  navigate?: string | null;
  fileName?: string;
  error?: boolean;
}

const SUGGESTIONS = ['What can you do?', 'List my courses', 'Seed the demo course', 'Show findings of the latest run'];
const ACCEPT = '.pdf,.docx,.txt,.md';

export function AssistantWidget() {
  const api = useApi();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { id: courseId } = useParams();
  const [open, setOpen] = useState(false);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [turns, busy, open]);

  async function send(text: string) {
    const message = text.trim();
    if (!message || busy) return;
    const history: ChatMessage[] = turns.filter((t) => !t.error).map(({ role, content }) => ({ role, content })).slice(-12);
    const attached = file;
    setTurns((t) => [...t, { id: crypto.randomUUID(), role: 'user', content: message, fileName: attached?.name }]);
    setInput('');
    setFile(null);
    setBusy(true);
    try {
      const res = await api.assistantChat({ message, history, course_id: courseId, file: attached ?? undefined });
      setTurns((t) => [...t, { id: crypto.randomUUID(), role: 'assistant', content: res.reply, actions: res.actions, navigate: res.navigate }]);
      if (res.actions.some((a) => a.status === 'ok')) void qc.invalidateQueries();
    } catch (e) {
      const msg = e instanceof ApiError ? `${e.code}: ${e.message}` : 'The assistant is unavailable right now.';
      setTurns((t) => [...t, { id: crypto.randomUUID(), role: 'assistant', content: msg, error: true }]);
    } finally {
      setBusy(false);
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    void send(input || (file ? 'Analyze this file' : ''));
  }
  function onKey(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void send(input || (file ? 'Analyze this file' : ''));
    }
  }

  if (!open) {
    return (
      <Button
        onClick={() => setOpen(true)}
        className="fixed bottom-5 right-5 z-40 h-12 rounded-full px-5 shadow-xl hover:shadow-2xl transition-all duration-fast hover:scale-105 active:scale-95 bg-gradient-to-r from-primary to-primary/90 text-primary-foreground font-semibold flex items-center gap-2 group"
        aria-label="Open assistant"
      >
        <MessageSquare className="h-5 w-5 transition-transform duration-fast group-hover:rotate-6" aria-hidden />
        <span>Assistant</span>
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary-foreground opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-primary-foreground"></span>
        </span>
      </Button>
    );
  }

  return (
    <section
      role="dialog"
      aria-label="Faculty Copilot assistant"
      className="fixed bottom-5 right-5 z-40 flex h-[min(640px,calc(100dvh-2.5rem))] w-[min(420px,calc(100vw-2.5rem))] flex-col overflow-hidden rounded-2xl border border-border/80 bg-card/95 backdrop-blur-xl shadow-2xl ring-1 ring-black/5 dark:ring-white/10 animate-fade-in"
    >
      <header className="flex items-center gap-2 border-b border-border/70 px-4 py-3 bg-muted/30">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-xs">
          <Bot className="h-4 w-4" aria-hidden />
        </div>
        <div className="min-w-0 flex-1 leading-tight">
          <p className="text-sm font-semibold">Assistant</p>
          <p className="truncate text-xs text-muted-foreground">{courseId ? 'Acting on the current course' : 'Ask or attach a paper to analyse'}</p>
        </div>
        {turns.length > 0 && (
          <Button variant="ghost" size="icon-sm" onClick={() => setTurns([])} aria-label="Clear conversation">
            <Trash2 aria-hidden />
          </Button>
        )}
        <Button variant="ghost" size="icon-sm" onClick={() => setOpen(false)} aria-label="Close assistant">
          <X aria-hidden />
        </Button>
      </header>

      <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto px-4 py-3" aria-live="polite">
        {turns.length === 0 && (
          <div className="space-y-3 text-sm text-muted-foreground">
            <p>I can do anything you can do here: create courses, upload and analyse papers, run exam audits, accept or dismiss findings, export reports.</p>
            <div className="flex flex-wrap gap-2">
              {SUGGESTIONS.map((s) => (
                <button key={s} type="button" onClick={() => void send(s)} className="rounded-full border border-border/70 px-3 py-1 text-xs hover:bg-muted transition-all active:scale-95">
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {turns.map((t) => (
          <div key={t.id} className={cn('flex', t.role === 'user' ? 'justify-end' : 'justify-start')}>
            <div className={cn('max-w-[88%] rounded-lg px-3 py-2', t.role === 'user' ? 'bg-primary text-primary-foreground' : t.error ? 'border border-destructive/40 bg-destructive/10' : 'bg-muted')}>
              {t.role === 'user' ? (
                <div className="text-sm">
                  <p className="whitespace-pre-wrap">{t.content}</p>
                  {t.fileName && (
                    <p className="mt-1 flex items-center gap-1 text-xs opacity-80">
                      <Paperclip className="h-3 w-3" aria-hidden /> {t.fileName}
                    </p>
                  )}
                </div>
              ) : (
                <>
                  {t.actions && t.actions.length > 0 && (
                    <ul className="mb-2 space-y-1 border-b pb-2 text-xs">
                      {t.actions.map((a, i) => (
                        <li key={i} className="flex items-start gap-1.5">
                          {a.status === 'ok' ? <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-success" aria-hidden /> : <XCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-destructive" aria-hidden />}
                          <span>
                            <span className="font-mono text-[11px] text-muted-foreground">{a.tool}</span> · {a.summary}
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                  <Markdown text={t.content} />
                  {t.navigate && (
                    <Button variant="link" size="sm" className="mt-1 h-auto px-0" onClick={() => navigate(t.navigate!)}>
                      Open page <ArrowRight aria-hidden />
                    </Button>
                  )}
                </>
              )}
            </div>
          </div>
        ))}
        {busy && (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden /> Working… uploads and audits can take a moment
          </div>
        )}
      </div>

      <form onSubmit={onSubmit} className="border-t p-3">
        {file && (
          <div className="mb-2 flex items-center gap-2 rounded-md border bg-muted/50 px-2 py-1 text-xs">
            <Paperclip className="h-3.5 w-3.5" aria-hidden />
            <span className="min-w-0 flex-1 truncate">{file.name}</span>
            <button type="button" onClick={() => setFile(null)} aria-label="Remove attachment" className="rounded p-0.5 hover:bg-muted">
              <X className="h-3.5 w-3.5" aria-hidden />
            </button>
          </div>
        )}
        <div className="flex items-end gap-2">
          <input ref={fileRef} type="file" accept={ACCEPT} className="hidden" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
          <Button type="button" variant="outline" size="icon" onClick={() => fileRef.current?.click()} aria-label="Attach a file" disabled={busy}>
            <Paperclip aria-hidden />
          </Button>
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKey}
            rows={1}
            placeholder={file ? 'Tell me what to do with this file…' : 'Ask or give an instruction…'}
            className="max-h-32 min-h-10 flex-1 resize-none"
            aria-label="Message"
            disabled={busy}
          />
          <Button type="submit" size="icon" aria-label="Send" disabled={busy || (!input.trim() && !file)}>
            <Send aria-hidden />
          </Button>
        </div>
      </form>
    </section>
  );
}
