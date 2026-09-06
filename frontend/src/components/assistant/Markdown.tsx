import { Fragment, type ReactNode } from 'react';

/** Tiny Markdown subset renderer (headings, bullets, bold, code, fences). Never injects HTML (SEC-004). */
function inline(text: string, key: number): ReactNode {
  const parts: ReactNode[] = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`|_[^_]+_)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let i = 0;
  while ((m = re.exec(text))) {
    if (m.index > last) parts.push(text.slice(last, m.index));
    const tok = m[0];
    if (tok.startsWith('**')) parts.push(<strong key={i++}>{tok.slice(2, -2)}</strong>);
    else if (tok.startsWith('`')) parts.push(<code key={i++} className="rounded bg-muted px-1 py-0.5 text-[0.85em]">{tok.slice(1, -1)}</code>);
    else parts.push(<em key={i++}>{tok.slice(1, -1)}</em>);
    last = m.index + tok.length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return <Fragment key={key}>{parts}</Fragment>;
}

export function Markdown({ text }: { text: string }) {
  const lines = text.replace(/\r\n/g, '\n').split('\n');
  const out: ReactNode[] = [];
  let i = 0;
  let k = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (line.startsWith('```')) {
      const buf: string[] = [];
      i++;
      while (i < lines.length && !lines[i].startsWith('```')) buf.push(lines[i++]);
      i++;
      out.push(
        <pre key={k++} className="my-2 max-h-60 overflow-auto rounded-md bg-muted p-2 text-xs">
          <code>{buf.join('\n')}</code>
        </pre>,
      );
      continue;
    }
    if (/^\s*[-*] /.test(line)) {
      const items: string[] = [];
      while (i < lines.length && /^\s*[-*] /.test(lines[i])) items.push(lines[i++].replace(/^\s*[-*] /, ''));
      out.push(
        <ul key={k++} className="my-1 list-disc space-y-0.5 pl-5">
          {items.map((it, j) => <li key={j}>{inline(it, j)}</li>)}
        </ul>,
      );
      continue;
    }
    const h = /^(#{1,3}) (.*)$/.exec(line);
    if (h) {
      out.push(<p key={k++} className="mt-2 font-semibold">{inline(h[2], 0)}</p>);
      i++;
      continue;
    }
    if (line.trim() === '') {
      i++;
      continue;
    }
    out.push(<p key={k++} className="my-1">{inline(line, 0)}</p>);
    i++;
  }
  return <div className="text-sm leading-relaxed">{out}</div>;
}
