import { useState } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import { Users, Activity, Coins, Building2, DatabaseZap, ArrowRight } from 'lucide-react';
import type { RunModule, RunStatus } from '@/lib/types/api';
import { useAdminDemoReset, useAdminPatchUser, useAdminRuns, useAdminUsage, useAdminUsers, useDeptAttainment, useDeptAudits } from '@/lib/queries';
import { PageHeader, QueryBoundary, EmptyState } from '@/components/feedback/states';
import { Stat, ComputedLabel } from '@/components/domain/trust';
import { StatusBadge } from '@/components/domain/RunProgress';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Field, Input } from '@/components/ui/input';
import { Switch, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/primitives';
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from '@/components/ui/dialog';
import { MODULE_LABEL, MODULE_PATH, STATUS_LABEL, formatDate, relTime } from '@/lib/format';

const MODULES: RunModule[] = ['exam_audit', 'attainment', 'syllabus_check', 'calibration'];
const STATUSES: RunStatus[] = ['queued', 'analyzing', 'completed', 'partial', 'failed'];

/* ------------------------------------------------------------------ users */
export function AdminUsersPage() {
  const [page, setPage] = useState(1);
  const q = useAdminUsers(page);
  const patch = useAdminPatchUser();
  return (
    <>
      <PageHeader title="Users" description="Faculty and admin accounts. Deactivated users keep their data but cannot sign in." />
      <QueryBoundary query={q} isEmpty={(d) => d.items.length === 0} empty={<EmptyState icon={Users} title="No users" />}>
        {(d) => (
          <div className="rounded-lg border bg-card">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead className="text-right">Courses</TableHead>
                  <TableHead className="text-right">Runs</TableHead>
                  <TableHead>Active</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {d.items.map((u) => (
                  <TableRow key={u.id}>
                    <TableCell className="font-medium">{u.full_name ?? '—'}</TableCell>
                    <TableCell className="text-muted-foreground">{u.email}</TableCell>
                    <TableCell>
                      <Select value={u.role} onValueChange={(role) => patch.mutate({ id: u.id, body: { role: role as 'faculty' | 'admin' } }, { onError: (e) => toast.error(e.message) })}>
                        <SelectTrigger aria-label={`Role for ${u.email}`} className="h-8 w-32"><SelectValue /></SelectTrigger>
                        <SelectContent><SelectItem value="faculty">Faculty</SelectItem><SelectItem value="admin">Admin</SelectItem></SelectContent>
                      </Select>
                    </TableCell>
                    <TableCell className="text-right tabular">{u.courses}</TableCell>
                    <TableCell className="text-right tabular">{u.runs}</TableCell>
                    <TableCell>
                      <Switch aria-label={`Active for ${u.email}`} checked={u.is_active} onCheckedChange={(is_active) => patch.mutate({ id: u.id, body: { is_active } }, { onError: (e) => toast.error(e.message) })} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <Pager page={d.page} pageSize={d.page_size} total={d.total} onPage={setPage} />
          </div>
        )}
      </QueryBoundary>
    </>
  );
}

function Pager({ page, pageSize, total, onPage }: { page: number; pageSize: number; total: number; onPage: (p: number) => void }) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  if (pages <= 1) return null;
  return (
    <nav aria-label="Pagination" className="flex items-center justify-between border-t px-4 py-2 text-sm">
      <span className="tabular text-muted-foreground">Page {page} of {pages} · {total} total</span>
      <div className="flex gap-2">
        <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => onPage(page - 1)}>Previous</Button>
        <Button size="sm" variant="outline" disabled={page >= pages} onClick={() => onPage(page + 1)}>Next</Button>
      </div>
    </nav>
  );
}

/* ------------------------------------------------------------------- runs */
export function AdminRunsPage() {
  const [page, setPage] = useState(1);
  const [module, setModule] = useState<RunModule | 'all'>('all');
  const [status, setStatus] = useState<RunStatus | 'all'>('all');
  const q = useAdminRuns({ page, module: module === 'all' ? undefined : module, status: status === 'all' ? undefined : status });
  return (
    <>
      <PageHeader
        title="All runs"
        description="Every analysis across the department. Open a run to read its findings (read-only)."
        actions={
          <div className="flex gap-2">
            <Select value={module} onValueChange={(v) => { setModule(v as RunModule | 'all'); setPage(1); }}>
              <SelectTrigger aria-label="Filter by module" className="w-44"><SelectValue /></SelectTrigger>
              <SelectContent><SelectItem value="all">All modules</SelectItem>{MODULES.map((m) => <SelectItem key={m} value={m}>{MODULE_LABEL[m]}</SelectItem>)}</SelectContent>
            </Select>
            <Select value={status} onValueChange={(v) => { setStatus(v as RunStatus | 'all'); setPage(1); }}>
              <SelectTrigger aria-label="Filter by status" className="w-40"><SelectValue /></SelectTrigger>
              <SelectContent><SelectItem value="all">All statuses</SelectItem>{STATUSES.map((s) => <SelectItem key={s} value={s}>{STATUS_LABEL[s]}</SelectItem>)}</SelectContent>
            </Select>
          </div>
        }
      />
      <QueryBoundary query={q} isEmpty={(d) => d.items.length === 0} empty={<EmptyState icon={Activity} title="No runs match" description="Try clearing the filters." />}>
        {(d) => (
          <div className="rounded-lg border bg-card">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>When</TableHead>
                  <TableHead>Owner</TableHead>
                  <TableHead>Module</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Progress</TableHead>
                  <TableHead><span className="sr-only">Open</span></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {d.items.map((r) => (
                  <TableRow key={r.id}>
                    <TableCell><time dateTime={r.created_at} title={formatDate(r.created_at)}>{relTime(r.created_at)}</time></TableCell>
                    <TableCell className="text-muted-foreground">{r.owner_email}</TableCell>
                    <TableCell>{MODULE_LABEL[r.module]}</TableCell>
                    <TableCell><StatusBadge status={r.status} /></TableCell>
                    <TableCell className="text-right tabular">{r.progress_pct}%</TableCell>
                    <TableCell className="text-right">
                      <Button asChild variant="ghost" size="sm"><Link to={`/courses/${r.course_id}/${MODULE_PATH[r.module]}/${r.id}`}>Open <ArrowRight aria-hidden /></Link></Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            <Pager page={d.page} pageSize={d.page_size} total={d.total} onPage={setPage} />
          </div>
        )}
      </QueryBoundary>
    </>
  );
}

/* ------------------------------------------------------------------ usage */
export function AdminUsagePage() {
  const [group, setGroup] = useState<'user' | 'day'>('user');
  const q = useAdminUsage(group);
  return (
    <>
      <PageHeader title="LLM usage" description="Calls, tokens and estimated cost recorded per request by the backend." actions={<ComputedLabel />} />
      <Tabs value={group} onValueChange={(v) => setGroup(v as 'user' | 'day')}>
        <TabsList><TabsTrigger value="user">By user</TabsTrigger><TabsTrigger value="day">By day</TabsTrigger></TabsList>
        <TabsContent value={group}>
          <QueryBoundary query={q} isEmpty={(d) => d.length === 0} empty={<EmptyState icon={Coins} title="No usage recorded" description="Usage appears after the first LLM-backed run." />}>
            {(rows) => {
              const tot = rows.reduce((a, r) => ({ calls: a.calls + r.calls, tin: a.tin + r.tokens_in, tout: a.tout + r.tokens_out, cost: a.cost + r.cost_usd, fail: a.fail + r.failures }), { calls: 0, tin: 0, tout: 0, cost: 0, fail: 0 });
              return (
                <div className="flex flex-col gap-4">
                  <section aria-label="Totals" className="grid gap-3 sm:grid-cols-4">
                    <Stat label="Calls" value={tot.calls.toLocaleString()} />
                    <Stat label="Tokens in / out" value={`${(tot.tin / 1000).toFixed(1)}k / ${(tot.tout / 1000).toFixed(1)}k`} />
                    <Stat label="Estimated cost" value={`$${tot.cost.toFixed(2)}`} hint="Provider list price" />
                    <Stat label="Failures" value={tot.fail} hint={tot.calls ? `${((100 * tot.fail) / tot.calls).toFixed(1)}% of calls` : undefined} />
                  </section>
                  <div className="rounded-lg border bg-card">
                    <Table dense>
                      <TableHeader>
                        <TableRow>
                          <TableHead>{group === 'user' ? 'User' : 'Day'}</TableHead>
                          <TableHead className="text-right">Calls</TableHead>
                          <TableHead className="text-right">Tokens in</TableHead>
                          <TableHead className="text-right">Tokens out</TableHead>
                          <TableHead className="text-right">Cost (USD)</TableHead>
                          <TableHead className="text-right">Failures</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {rows.map((r) => (
                          <TableRow key={r.key}>
                            <TableCell className="font-medium">{r.key}</TableCell>
                            <TableCell className="text-right tabular">{r.calls}</TableCell>
                            <TableCell className="text-right tabular">{r.tokens_in.toLocaleString()}</TableCell>
                            <TableCell className="text-right tabular">{r.tokens_out.toLocaleString()}</TableCell>
                            <TableCell className="text-right tabular">{r.cost_usd.toFixed(3)}</TableCell>
                            <TableCell className="text-right tabular">{r.failures > 0 ? <Badge variant="high">{r.failures}</Badge> : 0}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                </div>
              );
            }}
          </QueryBoundary>
        </TabsContent>
      </Tabs>
    </>
  );
}

/* ------------------------------------------------------------- seed reset */
export function AdminSeedPage() {
  const reset = useAdminDemoReset();
  const [confirm, setConfirm] = useState('');
  return (
    <>
      <PageHeader title="Demo data" description="Restore the CSE 2201 demo course, artefacts and runs to their seeded state. Everything created since is deleted." />
      <div className="max-w-xl rounded-lg border border-destructive/40 bg-card p-6">
        <div className="flex items-start gap-3">
          <DatabaseZap className="mt-0.5 h-5 w-5 text-destructive" aria-hidden />
          <div className="flex flex-col gap-3">
            <p className="font-semibold">Reset demo dataset</p>
            <p className="text-sm text-muted-foreground">Removes all courses, artefacts, runs and findings for every user, then re-inserts the seed. Accounts are kept. This cannot be undone.</p>
            <AlertDialog onOpenChange={() => setConfirm('')}>
              <AlertDialogTrigger asChild><Button variant="destructive" className="self-start">Reset demo data…</Button></AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Reset all demo data?</AlertDialogTitle>
                  <AlertDialogDescription>Type <span className="font-mono font-semibold">RESET</span> to confirm. Every run and finding will be lost.</AlertDialogDescription>
                </AlertDialogHeader>
                <Field id="confirm" label="Confirmation">
                  <Input id="confirm" value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="off" spellCheck={false} />
                </Field>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction
                    disabled={confirm !== 'RESET' || reset.isPending}
                    className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                    onClick={() => reset.mutate(undefined, { onSuccess: () => toast.success('Demo data reset'), onError: (e) => toast.error(e.message) })}
                  >
                    Reset
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        </div>
      </div>
    </>
  );
}

/* ------------------------------------------------------------- department */
export function AdminDepartmentPage() {
  const att = useDeptAttainment();
  const aud = useDeptAudits();
  return (
    <>
      <PageHeader title="Department view" description="Latest completed result per course, across all faculty. Read-only." actions={<ComputedLabel />} />
      <Tabs defaultValue="attainment">
        <TabsList><TabsTrigger value="attainment">CO attainment</TabsTrigger><TabsTrigger value="audits">Exam audits</TabsTrigger></TabsList>
        <TabsContent value="attainment">
          <QueryBoundary query={att} isEmpty={(d) => d.length === 0} empty={<EmptyState icon={Building2} title="No attainment runs yet" />}>
            {(rows) => (
              <div className="rounded-lg border bg-card">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Course</TableHead>
                      <TableHead>Owner</TableHead>
                      <TableHead>Finished</TableHead>
                      <TableHead className="text-right">COs met</TableHead>
                      <TableHead>Weakest CO</TableHead>
                      <TableHead><span className="sr-only">Open</span></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {rows.map((r) => (
                      <TableRow key={r.run_id}>
                        <TableCell className="font-mono font-semibold">{r.course_code}</TableCell>
                        <TableCell className="text-muted-foreground">{r.owner_email}</TableCell>
                        <TableCell>{formatDate(r.finished_at)}</TableCell>
                        <TableCell className="text-right tabular"><Badge variant={r.cos_met === r.cos_total ? 'success' : 'medium'}>{r.cos_met}/{r.cos_total}</Badge></TableCell>
                        <TableCell>{r.weakest_co ?? '—'}</TableCell>
                        <TableCell className="text-right"><Button asChild variant="ghost" size="sm"><Link to={`/admin/runs`}>Runs <ArrowRight aria-hidden /></Link></Button></TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </QueryBoundary>
        </TabsContent>
        <TabsContent value="audits">
          <QueryBoundary query={aud} isEmpty={(d) => d.length === 0} empty={<EmptyState icon={Building2} title="No exam audits yet" />}>
            {(rows) => (
              <div className="rounded-lg border bg-card">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Course</TableHead>
                      <TableHead>Owner</TableHead>
                      <TableHead>Finished</TableHead>
                      <TableHead className="text-right">Coverage</TableHead>
                      <TableHead className="text-right">Duplicates</TableHead>
                      <TableHead className="text-right">Open findings</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {rows.map((r) => (
                      <TableRow key={r.run_id}>
                        <TableCell className="font-mono font-semibold">{r.course_code}</TableCell>
                        <TableCell className="text-muted-foreground">{r.owner_email}</TableCell>
                        <TableCell>{formatDate(r.finished_at)}</TableCell>
                        <TableCell className="text-right tabular">{Math.round(r.coverage_pct)}%</TableCell>
                        <TableCell className="text-right tabular">{r.duplicates}</TableCell>
                        <TableCell className="text-right tabular">{r.open_findings}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </QueryBoundary>
        </TabsContent>
      </Tabs>
    </>
  );
}
