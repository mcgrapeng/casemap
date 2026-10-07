import * as React from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Copy, Check, Eye, EyeOff, AlertTriangle } from 'lucide-react';
import { Shell } from '@/components/layout/Shell';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { useCreateProject } from '@/hooks/useProjects';
import { useAuth } from '@/components/providers/ApiProvider';
import { useToast } from '@/hooks/useToast';

const schema = z.object({
  name: z.string().min(1, 'Name is required').max(128),
  llm_provider: z.string().optional(),
  llm_model: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

export default function NewProjectPage() {
  const navigate = useNavigate();
  const { setToken } = useAuth();
  const create = useCreateProject();
  const { toast } = useToast();
  const [created, setCreated] = React.useState<{ id: string; key: string } | null>(null);
  const [copied, setCopied] = React.useState(false);
  const [reveal, setReveal] = React.useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { name: '', llm_provider: '', llm_model: '' },
  });

  const onSubmit = async (values: FormValues) => {
    try {
      const project = await create.mutateAsync({
        name: values.name,
        llm_provider: values.llm_provider || undefined,
        llm_model: values.llm_model || undefined,
      });
      setToken(project.project_api_key);
      setCreated({ id: project.id, key: project.project_api_key });
    } catch (e) {
      toast({
        title: 'Failed to create project',
        description: e instanceof Error ? e.message : 'Unknown error',
        variant: 'destructive',
      });
    }
  };

  const copyKey = async () => {
    if (!created) return;
    try {
      await navigator.clipboard.writeText(created.key);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      toast({ title: 'Copy failed', description: 'Select and copy manually', variant: 'destructive' });
    }
  };

  return (
    <Shell>
      <h1 className="mb-4 text-2xl font-semibold tracking-tight">New Project</h1>
      <Card className="max-w-xl">
        <CardHeader>
          <CardTitle>Project details</CardTitle>
          <CardDescription>You&apos;ll receive an API key after creation.</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                placeholder="acme-api"
                aria-invalid={!!errors.name}
                {...register('name')}
              />
              {errors.name && (
                <p className="text-xs text-destructive" role="alert">
                  {errors.name.message}
                </p>
              )}
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="llm_provider">LLM provider (optional)</Label>
                <Input
                  id="llm_provider"
                  placeholder="openai"
                  {...register('llm_provider')}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="llm_model">LLM model (optional)</Label>
                <Input id="llm_model" placeholder="gpt-4o-mini" {...register('llm_model')} />
              </div>
            </div>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Creating…' : 'Create project'}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Dialog open={!!created} onOpenChange={(open) => !open && setCreated(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-status-blocked" />
              Save your API key
            </DialogTitle>
            <DialogDescription>
              This key is shown <strong>only once</strong>. Copy it now and store it
              somewhere safe — you won&apos;t be able to see it again.
            </DialogDescription>
          </DialogHeader>
          <div className="flex items-center gap-2 rounded-md border bg-muted p-2 font-mono text-xs">
            <code className="flex-1 break-all" aria-label="Project API key">
              {reveal ? created?.key : '•'.repeat((created?.key ?? '').length || 32)}
            </code>
            <Button
              size="icon"
              variant="ghost"
              aria-label={reveal ? 'Hide key' : 'Reveal key'}
              onClick={() => setReveal((r) => !r)}
            >
              {reveal ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </Button>
            <Button size="sm" onClick={copyKey} aria-label="Copy key to clipboard">
              {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
              <span>{copied ? 'Copied' : 'Copy'}</span>
            </Button>
          </div>
          <DialogFooter>
            <Button
              onClick={() => {
                if (created) navigate(`/projects/${created.id}`);
              }}
            >
              Continue to project
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Shell>
  );
}
