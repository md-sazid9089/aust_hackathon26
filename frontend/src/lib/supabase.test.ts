import { describe, it, expect } from 'vitest';
import { supabase } from './supabase';
import { supabase as supabaseFromUtils } from '../utils/supabase';
import { api } from './api-client';

describe('Supabase Client & Auth Configuration', () => {
  it('should initialize Supabase client successfully', () => {
    expect(supabase).toBeDefined();
    expect(supabase.auth).toBeDefined();
    expect(typeof supabase.auth.getSession).toBe('function');
    expect(typeof supabase.auth.signInWithPassword).toBe('function');
    expect(typeof supabase.auth.signOut).toBe('function');
  });

  it('should re-export supabase client from utils/supabase without divergence', () => {
    expect(supabaseFromUtils).toBe(supabase);
  });

  it('should integrate with api-client', () => {
    expect(api).toBeDefined();
    expect(typeof api.me).toBe('function');
    expect(typeof api.listCourses).toBe('function');
  });
});
