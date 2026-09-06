import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { BookOpen, Plus, Search, Sparkles, ArrowRight } from 'lucide-react';
import { toast } from 'sonner';
import { useCourses, useCreateCourse, usePrefetchCourse, useSeedDemo } from '@/lib/queries';
import { useAuth } from '@/auth/AuthProvider';
import { PageHeader, QueryBoundary, EmptyState } from '@/components/feedback/states';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input, Field } from '@/components/ui/input';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Card } from '@/components/ui/card';

function NewCourseDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (v: boolean) => void }) {
  const create = useCreateCourse();
  const nav = useNavigate();
  const [code, setCode] = useState('');
  const [title, setTitle] = useState('');
  const [term, setTerm] = useState('');
  const [err, setErr] = useState<string | null>(null);
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!/^[A-Z]{2,5}\s?\d{3,4}$/.test(code.trim())) return setErr('Use a course code like "CSE 3101".');
    if (title.trim().length < 3) return setErr('Title is too short.');
    setErr(null);
    create.mutate({ code: code.trim(), title: title.trim(), term: term.trim() || undefined }, {
      onSuccess: (c) => { toast.success('Course created'); onOpenChange(false); nav(`/courses/${c.id}`); },
      onError: (e) => setErr(e.message),
    });
  };
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New course</DialogTitle>
          <DialogDescription>You can add outcomes, topics and artefacts afterwards.</DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
          <Field id="c-code" label="Course code" error={err && err.includes('code') ? err : undefined}>
            <Input value={code} onChange={(e) => setCode(e.target.value)} placeholder="CSE 3101" />
          </Field>
          <Field id="c-title" label="Title" error={err && !err.includes('code') ? err : undefined}>
            <Input value={title} onChange={(e) => setTitle(e.target.value)} />
          </Field>
          <Field id="c-term" label="Term (optional)">
            <Input value={term} onChange={(e) => setTerm(e.target.value)} placeholder="Spring 2026" />
          </Field>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" loading={create.isPending}>Create</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function CoursesPage() {
  const { profile } = useAuth();
  const [q, setQ] = useState('');
  const courses = useCourses(q || undefined);
  const prefetch = usePrefetchCourse();
  const seed = useSeedDemo();
  const nav = useNavigate();
  const [open, setOpen] = useState(false);

  const seedDemo = () =>
    seed.mutate(undefined, {
      onSuccess: (r) => { toast.success(r.created ? 'Demo course created' : 'Demo course already exists'); nav(`/courses/${r.course_id}`); },
      onError: (e) => toast.error(e.message),
    });

  return (
    <>
      <PageHeader
        eyebrow={`Welcome back${profile?.full_name ? `, ${profile.full_name.split(' ').slice(-1)[0]}` : ''}`}
        title="My courses"
        description="Pick a course to audit an exam, compute attainment, check the syllabus or calibrate grading."
        actions={
          <>
            <Button variant="outline" onClick={seedDemo} loading={seed.isPending}>
              <Sparkles aria-hidden /> Load demo course
            </Button>
            <Button onClick={() => setOpen(true)}>
              <Plus aria-hidden /> New course
            </Button>
          </>
        }
      />
      <div className="mb-5 max-w-sm">
        <label htmlFor="course-search" className="sr-only">Search courses</label>
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
          <Input id="course-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by code or title" className="pl-9" />
        </div>
      </div>
      <QueryBoundary
        query={courses}
        isEmpty={(d) => d.items.length === 0}
        empty={
          <EmptyState
            icon={BookOpen}
            title={q ? 'No courses match' : 'No courses yet'}
            description={q ? 'Try a different code or title.' : 'Create your first course, or load the seeded demo to see every module with real-looking data.'}
            action={
              !q && (
                <div className="flex gap-2">
                  <Button variant="outline" onClick={seedDemo} loading={seed.isPending}><Sparkles aria-hidden /> Load demo course</Button>
                  <Button onClick={() => setOpen(true)}><Plus aria-hidden /> New course</Button>
                </div>
              )
            }
          />
        }
      >
        {(d) => (
          <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {d.items.map((c) => (
              <li key={c.id}>
                <Card className="group h-full transition-[border-color,box-shadow] duration-fast hover:border-primary/60 hover:shadow-md">
                  <Link to={`/courses/${c.id}`} onMouseEnter={() => prefetch(c.id)} onFocus={() => prefetch(c.id)} className="flex h-full flex-col p-5 focus-visible:outline-none">
                    <div className="flex items-start justify-between gap-2">
                      <p className="font-mono text-sm font-semibold text-primary">{c.code}</p>
                      {c.is_demo && <Badge variant="secondary">Demo</Badge>}
                    </div>
                    <h2 className="mt-1 text-lg font-semibold leading-snug">{c.title}</h2>
                    {c.term && <p className="text-sm text-muted-foreground">{c.term}</p>}
                    <dl className="mt-4 grid grid-cols-3 gap-2 text-sm">
                      <div><dt className="text-muted-foreground">Outcomes</dt><dd className="font-semibold tabular">{c.counts?.outcomes ?? 0}</dd></div>
                      <div><dt className="text-muted-foreground">Artefacts</dt><dd className="font-semibold tabular">{c.counts?.artefacts ?? 0}</dd></div>
                      <div><dt className="text-muted-foreground">Runs</dt><dd className="font-semibold tabular">{c.counts?.runs ?? 0}</dd></div>
                    </dl>
                    <span className="mt-auto flex items-center gap-1 pt-4 text-sm font-semibold text-primary">
                      Open <ArrowRight className="h-4 w-4 transition-transform duration-fast group-hover:translate-x-0.5" aria-hidden />
                    </span>
                  </Link>
                </Card>
              </li>
            ))}
          </ul>
        )}
      </QueryBoundary>
      <NewCourseDialog open={open} onOpenChange={setOpen} />
    </>
  );
}
