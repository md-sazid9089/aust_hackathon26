import { useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { ClipboardCheck, ArrowRight } from 'lucide-react';
import { useAuth, DEMO_USERS } from '@/auth/AuthProvider';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Field, Input } from '@/components/ui/input';

export function LoginPage() {
  const { status, profile, mode, authMode, lastError, signInMock, signInDev, signInWithPassword } = useAuth();
  const loc = useLocation() as { state?: { from?: string } };
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (status === 'authenticated' && profile) {
    const dest = loc.state?.from && loc.state.from !== '/login' ? loc.state.from : profile.role === 'admin' ? '/admin' : '/courses';
    return <Navigate to={dest} replace />;
  }

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setErr(await signInWithPassword(email, password));
    setBusy(false);
  };

  return (
    <div className="grid min-h-dvh bg-background lg:grid-cols-[1.1fr_1fr]">
      <a href="#login-main" className="skip-link">Skip to sign in</a>
      <section className="hidden flex-col justify-between border-r bg-card p-12 lg:flex">
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-md bg-primary text-primary-foreground">
            <ClipboardCheck className="h-5 w-5" aria-hidden />
          </div>
          <span className="font-semibold">Faculty Copilot</span>
        </div>
        <div className="max-w-xl">
          <h1 className="font-heading text-5xl font-semibold leading-[1.05] text-foreground">Evidence first. Then the AI explains.</h1>
          <p className="mt-6 text-lg text-muted-foreground">
            Audit a draft exam for CO coverage, compute CO/PO attainment, check syllabus overlap and calibrate grading — every finding shows its rationale and evidence before you decide.
          </p>
          <dl className="mt-10 grid grid-cols-3 gap-6 text-sm">
            <div>
              <dt className="text-muted-foreground">Analyses</dt>
              <dd className="mt-1 text-2xl font-semibold tabular">4 modules</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Numbers</dt>
              <dd className="mt-1 text-2xl font-semibold tabular">Deterministic</dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Decisions</dt>
              <dd className="mt-1 text-2xl font-semibold tabular">Yours</dd>
            </div>
          </dl>
        </div>
        <p className="text-sm text-muted-foreground">Ahsanullah University of Science and Technology · Dept. of CSE</p>
      </section>

      <main id="login-main" className="flex items-center justify-center p-6">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="font-heading text-2xl">Sign in</CardTitle>
            <CardDescription>
              {mode === 'mock'
                ? 'Demo mode — choose a role to explore with seeded data.'
                : authMode === 'dev'
                  ? 'Local development — the backend runs with a fixed faculty account.'
                  : 'Use your university account.'}
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {mode === 'live' && authMode === 'dev' ? (
              <>
                {lastError && (
                  <p role="alert" className="rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm text-destructive">
                    Could not reach the backend: {lastError}
                  </p>
                )}
                <Button type="button" onClick={() => void signInDev()} loading={status === 'loading'}>
                  Continue as local faculty
                </Button>
              </>
            ) : mode === 'mock' ? (
              DEMO_USERS.map((u) => (
                <button
                  key={u.id}
                  type="button"
                  onClick={() => signInMock(u.id)}
                  className="group flex w-full items-center justify-between rounded-lg border bg-card p-4 text-left transition-colors duration-fast hover:border-primary hover:bg-primary/5 cursor-pointer"
                >
                  <span>
                    <span className="block font-semibold">{u.label}</span>
                    <span className="block text-sm text-muted-foreground">{u.hint}</span>
                  </span>
                  <ArrowRight className="h-5 w-5 text-muted-foreground transition-transform duration-fast group-hover:translate-x-0.5" aria-hidden />
                </button>
              ))
            ) : (
              <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
                <Field id="email" label="Email">
                  <Input type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} required />
                </Field>
                <Field id="password" label="Password" error={err ?? undefined}>
                  <Input type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
                </Field>
                <Button type="submit" loading={busy} className="mt-2">
                  Sign in
                </Button>
              </form>
            )}
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
