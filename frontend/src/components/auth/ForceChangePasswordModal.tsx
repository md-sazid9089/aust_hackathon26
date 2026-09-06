import { useState } from 'react';
import { KeyRound, ShieldAlert, LogOut } from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '@/auth/AuthProvider';
import { useChangePassword } from '@/lib/queries';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Field, Input } from '@/components/ui/input';

export function ForceChangePasswordModal() {
  const { profile, signOut, refreshProfile } = useAuth();
  const changePassword = useChangePassword();

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);

  if (!profile?.must_change_password) {
    return null;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!currentPassword) {
      setError('Please enter your current temporary password.');
      return;
    }
    if (newPassword.length < 8) {
      setError('New password must be at least 8 characters long.');
      return;
    }
    if (newPassword === currentPassword) {
      setError('New password must be different from your temporary password.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('New password and confirmation do not match.');
      return;
    }

    try {
      await changePassword.mutateAsync({
        current_password: currentPassword,
        new_password: newPassword,
      });
      await refreshProfile();
      toast.success('Password updated successfully. Welcome to Faculty Copilot!');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to update password. Please check your credentials.';
      setError(msg);
    }
  };

  return (
    <Dialog open={true}>
      <DialogContent
        hideClose
        onPointerDownOutside={(e) => e.preventDefault()}
        onEscapeKeyDown={(e) => e.preventDefault()}
        className="sm:max-w-md"
      >
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <KeyRound className="h-5 w-5" aria-hidden />
            </div>
            <div>
              <DialogTitle>Set New Password</DialogTitle>
              <div className="mt-1 flex items-center gap-1.5 text-xs text-amber-600 dark:text-amber-400 font-medium">
                <ShieldAlert className="h-3.5 w-3.5" aria-hidden />
                <span>First sign-in password change required</span>
              </div>
            </div>
          </div>
          <DialogDescription className="mt-2 text-left text-sm">
            Your account was created with a temporary password. For your security, please create a new password before accessing your faculty workspace.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="flex flex-col gap-3.5 py-1">
          {error && (
            <div role="alert" className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
              {error}
            </div>
          )}

          <Field id="current-password" label="Temporary / Current Password">
            <Input
              type="password"
              autoComplete="current-password"
              placeholder="Enter the password provided by admin"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              required
            />
          </Field>

          <Field id="new-password" label="New Password (min. 8 characters)">
            <Input
              type="password"
              autoComplete="new-password"
              placeholder="Choose a strong password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
            />
          </Field>

          <Field id="confirm-password" label="Confirm New Password">
            <Input
              type="password"
              autoComplete="new-password"
              placeholder="Re-enter your new password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />
          </Field>

          <DialogFooter className="mt-3 flex-col sm:flex-row gap-2">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => void signOut()}
              className="text-muted-foreground hover:text-foreground"
            >
              <LogOut className="h-4 w-4 mr-1.5" aria-hidden />
              Sign out
            </Button>
            <Button type="submit" loading={changePassword.isPending}>
              Update Password & Continue
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
