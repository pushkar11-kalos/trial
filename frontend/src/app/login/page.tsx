"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { ShieldCheck } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Alert } from "@/components/ui/alert";

const DEMO_ACCOUNTS = [
  { role: "Inspector", email: "inspector@metracheck.demo" },
  { role: "Supervisor", email: "supervisor@metracheck.demo" },
  { role: "Administrator", email: "admin@metracheck.demo" },
];
const DEMO_PASSWORD = "Demo@1234";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Login failed. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  function fillDemo(demoEmail: string) {
    setEmail(demoEmail);
    setPassword(DEMO_PASSWORD);
    setError(null);
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-navy-900 p-4">
      <div className="grid w-full max-w-4xl overflow-hidden rounded-xl border border-white/10 bg-white shadow-2xl md:grid-cols-2">
        <div className="hidden flex-col justify-between bg-navy-900 p-8 text-white md:flex">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-6 w-6 text-accent" />
            <span className="font-heading text-lg font-bold">MetraCheck</span>
          </div>
          <div>
            <h2 className="font-heading text-2xl font-bold leading-tight">
              AI-assisted compliance screening for Legal Metrology inspections.
            </h2>
            <p className="mt-3 text-sm text-white/60">
              OCR extracts evidence. A deterministic, versioned rule engine decides
              pass, review, or non-compliant. An officer makes the final call —
              every finding stays explainable and evidence-linked.
            </p>
          </div>
          <p className="text-[11px] text-white/30">
            Prototype rule pack — verify against active official legal instruments
            before operational enforcement.
          </p>
        </div>

        <div className="p-8">
          <CardHeader className="p-0">
            <CardTitle className="text-xl">Officer sign in</CardTitle>
            <CardDescription>Sign in to start or continue an inspection.</CardDescription>
          </CardHeader>

          <form onSubmit={handleSubmit} className="mt-6 space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@metracheck.demo"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
              />
            </div>
            {error && <Alert variant="destructive">{error}</Alert>}
            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? "Signing in..." : "Sign in"}
            </Button>
          </form>

          <div className="mt-6 border-t border-line pt-4">
            <p className="text-xs font-medium text-ink-500">
              DEMO ACCOUNTS (password: {DEMO_PASSWORD})
            </p>
            <div className="mt-2 space-y-1.5">
              {DEMO_ACCOUNTS.map((acc) => (
                <button
                  key={acc.email}
                  type="button"
                  onClick={() => fillDemo(acc.email)}
                  className="flex w-full items-center justify-between rounded-md border border-line px-3 py-2 text-left text-xs hover:bg-canvas"
                >
                  <span className="font-medium text-ink-900">{acc.role}</span>
                  <span className="font-mono text-ink-500">{acc.email}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
