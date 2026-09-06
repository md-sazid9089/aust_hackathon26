import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback } from 'react';
import { useApi } from '@/lib/api';
import type * as T from '@/lib/types/api';

export const qk = {
  courses: ['courses'] as const,
  course: (id: string) => ['course', id] as const,
  artefacts: (courseId: string, kind?: T.ArtefactKind) => ['artefacts', courseId, kind ?? 'all'] as const,
  artefactChildren: (artefactId: string, kind: string) => ['artefact-children', artefactId, kind] as const,
  runs: (courseId: string) => ['runs', courseId] as const,
  run: (runId: string) => ['run', runId] as const,
  findings: (runId: string) => ['findings', runId] as const,
  attainment: (runId: string) => ['attainment', runId] as const,
  prescores: (runId: string) => ['prescores', runId] as const,
  outcomes: (courseId: string) => ['outcomes', courseId] as const,
  copo: (courseId: string) => ['copo', courseId] as const,
  topics: (courseId: string) => ['topics', courseId] as const,
  pos: ['program-outcomes'] as const,
  dashboard: ['dashboard'] as const,
  admin: (...rest: (string | number | undefined)[]) => ['admin', ...rest] as const,
};

/* ---------- courses ---------- */
export const useCourses = (q?: string) => {
  const api = useApi();
  return useQuery({ queryKey: [...qk.courses, q ?? ''], queryFn: () => api.listCourses(q), placeholderData: keepPreviousData });
};
export const useCourse = (id: string) => {
  const api = useApi();
  return useQuery({ queryKey: qk.course(id), queryFn: () => api.getCourse(id) });
};
/** Warm the course page's queries on hover/focus so navigation paints with data already in cache. */
export const usePrefetchCourse = () => {
  const api = useApi();
  const qc = useQueryClient();
  return useCallback(
    (id: string) => {
      void qc.prefetchQuery({ queryKey: qk.course(id), queryFn: () => api.getCourse(id) });
      void qc.prefetchQuery({ queryKey: qk.artefacts(id), queryFn: () => api.listArtefacts(id) });
      void qc.prefetchQuery({ queryKey: [...qk.runs(id), 'all', 'all'], queryFn: () => api.listRuns(id) });
    },
    [api, qc],
  );
};
export const useCreateCourse = () => {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({ mutationFn: (b: T.CourseCreate) => api.createCourse(b), onSuccess: () => qc.invalidateQueries({ queryKey: qk.courses }) });
};
export const useSeedDemo = () => {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({ mutationFn: () => api.seedDemo(), onSuccess: () => qc.invalidateQueries() });
};
export const useRuns = (courseId: string, filter?: { module?: T.RunModule; status?: T.RunStatus }) => {
  const api = useApi();
  return useQuery({ queryKey: [...qk.runs(courseId), filter?.module ?? 'all', filter?.status ?? 'all'], queryFn: () => api.listRuns(courseId, filter), placeholderData: keepPreviousData });
};

/* ---------- outcomes ---------- */
export const useProgramOutcomes = () => {
  const api = useApi();
  return useQuery({ queryKey: qk.pos, queryFn: () => api.listProgramOutcomes(), staleTime: Infinity });
};
export const useOutcomes = (courseId: string) => {
  const api = useApi();
  return useQuery({ queryKey: qk.outcomes(courseId), queryFn: () => api.listOutcomes(courseId) });
};
export const usePutOutcomes = (courseId: string) => {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({ mutationFn: (rows: T.CourseOutcomeIn[]) => api.putOutcomes(courseId, rows), onSuccess: () => qc.invalidateQueries({ queryKey: qk.outcomes(courseId) }) });
};
export const useCoPoMap = (courseId: string) => {
  const api = useApi();
  return useQuery({ queryKey: qk.copo(courseId), queryFn: () => api.getCoPoMap(courseId) });
};
export const usePutCoPoMap = (courseId: string) => {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({ mutationFn: (cells: T.CoPoCell[]) => api.putCoPoMap(courseId, cells), onSuccess: () => qc.invalidateQueries({ queryKey: qk.copo(courseId) }) });
};
export const useTopics = (courseId: string) => {
  const api = useApi();
  return useQuery({ queryKey: qk.topics(courseId), queryFn: () => api.listTopics(courseId) });
};

/* ---------- artefacts ---------- */
export const useArtefacts = (courseId: string, kind?: T.ArtefactKind) => {
  const api = useApi();
  return useQuery({
    queryKey: qk.artefacts(courseId, kind),
    queryFn: () => api.listArtefacts(courseId, kind ? { kind } : undefined),
    refetchInterval: (q) => (q.state.data?.some((a) => a.status === 'pending' || a.status === 'extracting') ? 1500 : false),
  });
};
export const useUploadArtefact = (courseId: string) => {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({ mutationFn: (b: T.ArtefactUpload) => api.uploadArtefact(courseId, b), onSuccess: () => qc.invalidateQueries({ queryKey: ['artefacts', courseId] }) });
};
export const useDeleteArtefact = (courseId: string) => {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({ mutationFn: (id: string) => api.deleteArtefact(id), onSuccess: () => qc.invalidateQueries({ queryKey: ['artefacts', courseId] }) });
};
export const useReextract = (courseId: string) => {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({ mutationFn: (id: string) => api.reextract(id), onSuccess: () => qc.invalidateQueries({ queryKey: ['artefacts', courseId] }) });
};
export const useQuestions = (artefactId: string | undefined) => {
  const api = useApi();
  return useQuery({ queryKey: qk.artefactChildren(artefactId ?? '', 'questions'), queryFn: () => api.getQuestions(artefactId!), enabled: !!artefactId });
};
export const usePutQuestions = (artefactId: string) => {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ rows, coMap }: { rows: T.QuestionIn[]; coMap?: T.QuestionCoMapIn[] }) => {
      const saved = await api.putQuestions(artefactId, rows);
      if (coMap) await api.putQuestionCoMap(artefactId, coMap);
      return saved;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['artefact-children', artefactId] }),
  });
};
export const useMarks = (artefactId: string | undefined) => {
  const api = useApi();
  return useQuery({ queryKey: qk.artefactChildren(artefactId ?? '', 'marks'), queryFn: () => api.getMarks(artefactId!), enabled: !!artefactId });
};
export const useRubric = (artefactId: string | undefined) => {
  const api = useApi();
  return useQuery({ queryKey: qk.artefactChildren(artefactId ?? '', 'rubric'), queryFn: () => api.getRubric(artefactId!), enabled: !!artefactId });
};
export const usePutRubric = (artefactId: string) => {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({ mutationFn: (rows: T.RubricCriterion[]) => api.putRubric(artefactId, rows), onSuccess: () => qc.invalidateQueries({ queryKey: ['artefact-children', artefactId] }) });
};
export const useAnswers = (artefactId: string | undefined) => {
  const api = useApi();
  return useQuery({ queryKey: qk.artefactChildren(artefactId ?? '', 'answers'), queryFn: () => api.getAnswers(artefactId!), enabled: !!artefactId });
};
export const usePutAnswers = (artefactId: string) => {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({ mutationFn: (rows: T.Answer[]) => api.putAnswers(artefactId, rows), onSuccess: () => qc.invalidateQueries({ queryKey: ['artefact-children', artefactId] }) });
};

/* ---------- runs ---------- */
export const useCreateRun = (courseId: string) => {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({ mutationFn: (b: T.RunCreate) => api.createRun(courseId, b), onSuccess: () => qc.invalidateQueries({ queryKey: qk.runs(courseId) }) });
};
export const useRun = (runId: string) => {
  const api = useApi();
  return useQuery({ queryKey: qk.run(runId), queryFn: () => api.getRun(runId) });
};
export const useFindings = (runId: string, enabled = true) => {
  const api = useApi();
  return useQuery({ queryKey: qk.findings(runId), queryFn: () => api.listFindings(runId), enabled });
};
export const usePatchFinding = (runId: string) => {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: T.FindingStatus }) => api.patchFinding(id, status),
    onMutate: async ({ id, status }) => {
      await qc.cancelQueries({ queryKey: qk.findings(runId) });
      const prev = qc.getQueryData<T.Finding[]>(qk.findings(runId));
      qc.setQueryData<T.Finding[]>(qk.findings(runId), (old) => old?.map((f) => (f.id === id ? { ...f, status, decided_at: new Date().toISOString() } : f)));
      return { prev };
    },
    onError: (_e, _v, ctx) => ctx?.prev && qc.setQueryData(qk.findings(runId), ctx.prev),
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: qk.findings(runId) });
      void qc.invalidateQueries({ queryKey: qk.dashboard });
    },
  });
};
export const useAttainment = (runId: string, enabled = true) => {
  const api = useApi();
  return useQuery({ queryKey: qk.attainment(runId), queryFn: () => api.getAttainment(runId), enabled });
};
export const usePrescores = (runId: string, enabled = true) => {
  const api = useApi();
  return useQuery({ queryKey: qk.prescores(runId), queryFn: () => api.getPrescores(runId), enabled });
};
export const useCompare = (a: string | null, b: string | null) => {
  const api = useApi();
  return useQuery({ queryKey: ['compare', a, b], queryFn: () => api.compareRuns(a!, b!), enabled: !!a && !!b && a !== b });
};
export const useSuggest = (runId: string) => {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({ mutationFn: (coIds?: string[]) => api.suggestQuestions(runId, coIds), onSuccess: () => qc.invalidateQueries({ queryKey: qk.findings(runId) }) });
};

/* ---------- dashboard / admin ---------- */
export const useDashboard = () => {
  const api = useApi();
  return useQuery({ queryKey: qk.dashboard, queryFn: () => api.dashboardSummary() });
};
export const useAdminUsers = (page = 1) => {
  const api = useApi();
  return useQuery({ queryKey: qk.admin('users', page), queryFn: () => api.adminUsers(page) });
};
export const useAdminCreateUser = () => {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: T.AdminUserCreate) => api.adminCreateUser(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.admin('users') }),
  });
};
export const useAdminPatchUser = () => {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: T.AdminUserPatch }) => api.adminPatchUser(id, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.admin('users') }),
  });
};
export const useChangePassword = () => {
  const api = useApi();
  return useMutation({
    mutationFn: (body: T.ChangePasswordInput) => api.changePassword(body),
  });
};
export const useAdminRuns = (params: { page?: number; module?: T.RunModule; status?: T.RunStatus }) => {
  const api = useApi();
  return useQuery({ queryKey: qk.admin('runs', params.page, params.module, params.status), queryFn: () => api.adminRuns(params) });
};
export const useAdminUsage = (group: 'user' | 'day') => {
  const api = useApi();
  return useQuery({ queryKey: qk.admin('usage', group), queryFn: () => api.adminUsage({ group }) });
};
export const useAdminDemoReset = () => {
  const api = useApi();
  const qc = useQueryClient();
  return useMutation({ mutationFn: () => api.adminDemoReset(), onSuccess: () => qc.invalidateQueries() });
};
export const useDeptAttainment = () => {
  const api = useApi();
  return useQuery({ queryKey: qk.admin('dept', 'attainment'), queryFn: () => api.adminDeptAttainment() });
};
export const useDeptAudits = () => {
  const api = useApi();
  return useQuery({ queryKey: qk.admin('dept', 'audits'), queryFn: () => api.adminDeptExamAudits() });
};
