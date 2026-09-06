import { useState } from 'react';
import { Link } from 'react-router-dom';
import { toast } from 'sonner';
import { Users, Activity, Coins, Building2, DatabaseZap, ArrowRight, UserPlus, Copy, Check, KeyRound, ShieldAlert } from 'lucide-react';
import type { RunModule, RunStatus } from '@/lib/types/api';
import { useAdminCreateUser, useAdminDemoReset, useAdminPatchUser, useAdminRuns, useAdminUsage, useAdminUsers, useDeptAttainment, useDeptAudits } from '@/lib/queries';
import { PageHeader, QueryBoundary, EmptyState } from '@/components/feedback/states';
import { Stat, ComputedLabel } from '@/components/domain/trust';
import { StatusBadge } from '@/components/domain/RunProgress';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Field, Input } from '@/components/ui/input';
import { Switch, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/primitives';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger } from '@/components/ui/dialog';
import { MODULE_LABEL, MODULE_PATH, STATUS_LABEL, formatDate, relTime } from '@/lib/format';

const MODULES: RunModule[] = ['exam_audit', 'attainment', 'syllabus_check', 'calibration'];
const STATUSES: RunStatus[] = ['queued', 'analyzing', 'completed', 'partial', 'failed'];

/* ------------------------------------------------------------------ users */
function AddUserModal({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  const createUser = useAdminCreateUser();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<'faculty' | 'admin'>('faculty');
  const [mustChangePassword, setMustChangePassword] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [createdResult, setCreatedResult] = useState<{ email: string; password: string; name: string } | null>(null);

  const generatePassword = () => {
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%';
    let res = 'AUST#';
    for (let i = 0; i < 6; i++) {
      res += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    setPassword(res);
  };

  const handleOpenChange = (nextOpen: boolean) => {
    if (!nextOpen) {
      setFullName('');
      setEmail('');
      setPassword('');
      setRole('faculty');
      setMustChangePassword(true);
      setError(null);
      setCopied(false);
      setCreatedResult(null);
    }
    onOpenChange(nextOpen);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!email.trim() || !password) {
      setError('Email and password are required.');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }

    try {
      await createUser.mutateAsync({
        email: email.trim(),
        password,
        full_name: fullName.trim() || undefined,
        role,
        must_change_password: mustChangePassword,
      });
      setCreatedResult({
        email: email.trim(),
        password,
        name: fullName.trim() || email.trim(),
      });
      toast.success('User account created.');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create user');
    }
  };

  const copyCreds = async () => {
    if (!createdResult) return;
    const text = `Faculty Copilot Login Credentials\nName: ${createdResult.name}\nEmail: ${createdResult.email}\nTemporary Password: ${createdResult.password}\n\nNote: You will be asked to choose a new password on your first sign in.`;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      toast.success('Credentials copied to clipboard');
      setTimeout(() => setCopied(false), 2500);
    } catch {
      toast.error('Could not copy to clipboard');
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{createdResult ? 'User Created Successfully' : 'Add New User'}</DialogTitle>
          <DialogDescription>
            {createdResult
              ? 'Share these temporary credentials with the teacher. They will be prompted to change their password on first login.'
              : 'Create a new faculty or admin account. Provide an initial password to give to the teacher.'}
          </DialogDescription>
        </DialogHeader>

        {createdResult ? (
          <div className="flex flex-col gap-4 py-2">
            <div className="rounded-lg border bg-muted/40 p-4 font-mono text-sm space-y-1.5 select-all">
              <div>
                <span className="text-muted-foreground select-none font-sans text-xs">Email: </span>
                <span className="font-semibold text-foreground">{createdResult.email}</span>
              </div>
              <div>
                <span className="text-muted-foreground select-none font-sans text-xs">Temporary Password: </span>
                <span className="font-semibold text-primary">{createdResult.password}</span>
              </div>
            </div>

            <div className="flex items-center gap-2 text-xs text-amber-600 dark:text-amber-400">
              <ShieldAlert className="h-4 w-4 shrink-0" aria-hidden />
              <span>The user will be required to change this password on their first login.</span>
            </div>

            <DialogFooter className="mt-2 flex-col sm:flex-row gap-2">
              <Button type="button" variant="outline" onClick={copyCreds}>
                {copied ? <Check className="h-4 w-4 mr-1.5 text-emerald-600" /> : <Copy className="h-4 w-4 mr-1.5" />}
                {copied ? 'Copied' : 'Copy Credentials'}
              </Button>
              <Button type="button" onClick={() => handleOpenChange(false)}>
                Done
              </Button>
            </DialogFooter>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col gap-3 py-1">
            {error && (
              <div role="alert" className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
                {error}
              </div>
            )}

            <Field id="user-name" label="Full Name (optional)">
              <Input
                type="text"
                placeholder="e.g. Dr. Sadia Sultana"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
              />
            </Field>

            <Field id="user-email" label="Email Address">
              <Input
                type="email"
                placeholder="teacher@aust.edu"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </Field>

            <Field id="user-role" label="Role">
              <Select value={role} onValueChange={(v) => setRole(v as 'faculty' | 'admin')}>
                <SelectTrigger id="user-role"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="faculty">Faculty (Teacher)</SelectItem>
                  <SelectItem value="admin">Administrator</SelectItem>
                </SelectContent>
              </Select>
            </Field>

            <div className="flex flex-col gap-1.5">
              <div className="flex items-center justify-between">
                <label htmlFor="user-password" className="text-sm font-medium leading-none">
                  Temporary Password
                </label>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-6 px-1.5 text-xs text-primary"
                  onClick={generatePassword}
                >
                  Generate
                </Button>
              </div>
              <Input
                id="user-password"
                type="text"
                placeholder="Enter or generate temporary password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            <div className="flex items-center gap-2 pt-1">
              <Switch
                id="must-change"
                checked={mustChangePassword}
                onCheckedChange={setMustChangePassword}
              />
              <label htmlFor="must-change" className="text-xs text-muted-foreground cursor-pointer select-none">
                Require password change on first sign-in
              </label>
            </div>

            <DialogFooter className="mt-3">
              <Button type="button" variant="outline" onClick={() => handleOpenChange(false)}>
                Cancel
              </Button>
              <Button type="submit" loading={createUser.isPending}>
                Create User
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}

function ResetPasswordModal({
  user,
  open,
  onOpenChange,
}: {
  user: { id: string; email: string; full_name: string | null } | null;
  open: boolean;
  onOpenChange: (v: boolean) => void;
}) {
  const patchUser = useAdminPatchUser();
  const [newPassword, setNewPassword] = useState('');
  const [mustChangePassword, setMustChangePassword] = useState(true);
  const [copied, setCopied] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generatePassword = () => {
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%';
    let res = 'AUST#';
    for (let i = 0; i < 6; i++) {
      res += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    setNewPassword(res);
  };

  const handleOpenChange = (v: boolean) => {
    if (!v) {
      setNewPassword('');
      setMustChangePassword(true);
      setCopied(false);
      setDone(false);
      setError(null);
    }
    onOpenChange(v);
  };

  const handleReset = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!user) return;
    setError(null);
    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }
    try {
      await patchUser.mutateAsync({
        id: user.id,
        body: {
          password: newPassword,
          must_change_password: mustChangePassword,
        },
      });
      setDone(true);
      toast.success('Password reset successfully.');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to reset password');
    }
  };

  const copyCreds = async () => {
    if (!user) return;
    const text = `Faculty Copilot Login Credentials\nName: ${user.full_name ?? user.email}\nEmail: ${user.email}\nTemporary Password: ${newPassword}\n\nNote: You will be asked to choose a new password on your next sign in.`;
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      toast.success('Credentials copied to clipboard');
      setTimeout(() => setCopied(false), 2500);
    } catch {
      toast.error('Could not copy to clipboard');
    }
  };

  if (!user) return null;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{done ? 'Password Reset' : 'Reset User Password'}</DialogTitle>
          <DialogDescription>
            {done
              ? `Password for ${user.email} has been updated. Provide these credentials to the user.`
              : `Set a new temporary password for ${user.full_name ? `${user.full_name} (${user.email})` : user.email}.`}
          </DialogDescription>
        </DialogHeader>

        {done ? (
          <div className="flex flex-col gap-4 py-2">
            <div className="rounded-lg border bg-muted/40 p-4 font-mono text-sm space-y-1.5 select-all">
              <div>
                <span className="text-muted-foreground select-none font-sans text-xs">Email: </span>
                <span className="font-semibold text-foreground">{user.email}</span>
              </div>
              <div>
                <span className="text-muted-foreground select-none font-sans text-xs">New Temporary Password: </span>
                <span className="font-semibold text-primary">{newPassword}</span>
              </div>
            </div>

            <DialogFooter className="mt-2 flex-col sm:flex-row gap-2">
              <Button type="button" variant="outline" onClick={copyCreds}>
                {copied ? <Check className="h-4 w-4 mr-1.5 text-emerald-600" /> : <Copy className="h-4 w-4 mr-1.5" />}
                {copied ? 'Copied' : 'Copy Credentials'}
              </Button>
              <Button type="button" onClick={() => handleOpenChange(false)}>
                Done
              </Button>
            </DialogFooter>
          </div>
        ) : (
          <form onSubmit={handleReset} className="flex flex-col gap-3 py-1">
            {error && (
              <div role="alert" className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
                {error}
              </div>
            )}

            <div className="flex flex-col gap-1.5">
              <div className="flex items-center justify-between">
                <label htmlFor="reset-password" className="text-sm font-medium leading-none">
                  New Temporary Password
                </label>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-6 px-1.5 text-xs text-primary"
                  onClick={generatePassword}
                >
                  Generate
                </Button>
              </div>
              <Input
                id="reset-password"
                type="text"
                placeholder="Enter or generate temporary password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
              />
            </div>

            <div className="flex items-center gap-2 pt-1">
              <Switch
                id="reset-must-change"
                checked={mustChangePassword}
                onCheckedChange={setMustChangePassword}
              />
              <label htmlFor="reset-must-change" className="text-xs text-muted-foreground cursor-pointer select-none">
                Require password change on next sign-in
              </label>
            </div>

            <DialogFooter className="mt-3">
              <Button type="button" variant="outline" onClick={() => handleOpenChange(false)}>
                Cancel
              </Button>
              <Button type="submit" loading={patchUser.isPending}>
                Reset Password
              </Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}

export function AdminUsersPage() {
  const [page, setPage] = useState(1);
  const [addOpen, setAddOpen] = useState(false);
  const [resetTarget, setResetTarget] = useState<{ id: string; email: string; full_name: string | null } | null>(null);
  const q = useAdminUsers(page);
  const patch = useAdminPatchUser();
  return (
    <>
      <PageHeader
        title="Users"
        description="Faculty and admin accounts. Deactivated users keep their data but cannot sign in."
        actions={
          <Button size="sm" onClick={() => setAddOpen(true)}>
            <UserPlus className="h-4 w-4 mr-1.5" aria-hidden /> Add User
          </Button>
        }
      />
      <AddUserModal open={addOpen} onOpenChange={setAddOpen} />
      <ResetPasswordModal user={resetTarget} open={!!resetTarget} onOpenChange={(v) => !v && setResetTarget(null)} />
      <QueryBoundary query={q} isEmpty={(d) => d.items.length === 0} empty={<EmptyState icon={Users} title="No users" />}>
        {(d) => (
          <div className="rounded-lg border bg-card">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Courses</TableHead>
                  <TableHead className="text-right">Runs</TableHead>
                  <TableHead>Active</TableHead>
                  <TableHead><span className="sr-only">Actions</span></TableHead>
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
                    <TableCell>
                      {u.must_change_password ? (
                        <Badge variant="outline" className="border-amber-400/60 bg-amber-50/50 text-amber-700 dark:bg-amber-950/20 dark:text-amber-400 text-xs">
                          Pending PW change
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="border-border text-muted-foreground text-xs">
                          Active
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-right tabular">{u.courses}</TableCell>
                    <TableCell className="text-right tabular">{u.runs}</TableCell>
                    <TableCell>
                      <Switch aria-label={`Active for ${u.email}`} checked={u.is_active} onCheckedChange={(is_active) => patch.mutate({ id: u.id, body: { is_active } }, { onError: (e) => toast.error(e.message) })} />
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-8 px-2 text-xs text-muted-foreground hover:text-foreground"
                        onClick={() => setResetTarget(u)}
                        title={`Reset password for ${u.email}`}
                      >
                        <KeyRound className="h-3.5 w-3.5 mr-1" aria-hidden /> Reset PW
                      </Button>
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
      <PageHeader title="Demo data" description="Restore the CSE 3103 demo course, artefacts and runs to their seeded state. Everything created in it since is deleted." />
      <div className="max-w-xl rounded-lg border border-destructive/40 bg-card p-6">
        <div className="flex items-start gap-3">
          <DatabaseZap className="mt-0.5 h-5 w-5 text-destructive" aria-hidden />
          <div className="flex flex-col gap-3">
            <p className="font-semibold">Reset demo dataset</p>
            <p className="text-sm text-muted-foreground">Deletes the demo courses owned by this admin account (artefacts, runs and findings included) and re-inserts the seed dataset. Faculty workspaces are untouched. This cannot be undone.</p>
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
