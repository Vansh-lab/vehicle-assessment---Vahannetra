"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ShieldCheck, Smartphone } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { loginWithBackend } from "@/lib/api/services";

const schema = z.object({
  email: z.string().email("Enter a valid work email"),
  password: z.string().min(6, "Password must be at least 6 characters"),
  otp: z.string().optional(),
});

type LoginValues = z.infer<typeof schema>;

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginValues>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "", otp: "" },
  });

  const onSubmit = async (values: LoginValues) => {
    try {
      setSubmitting(true);
      setError("");
      await loginWithBackend(values);
      router.push("/dashboard");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Login failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto flex min-h-screen max-w-md items-center px-4 py-6">
      <Card className="w-full space-y-6 border-cyan-400/25">
        <div>
          <p className="text-2xl font-bold text-cyan-100">Vahannetra AI</p>
          <p className="text-sm text-slate-400">Secure sign in for inspection teams</p>
        </div>

        <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
          <div>
            <Label htmlFor="email">Work Email</Label>
            <Input id="email" type="email" placeholder="ops@insurer.com" {...register("email")} />
            {errors.email ? <p className="mt-1 text-xs text-rose-300">{errors.email.message}</p> : null}
          </div>
          <div>
            <Label htmlFor="password">Password</Label>
            <Input id="password" type="password" placeholder="Enter password" {...register("password")} />
            {errors.password ? <p className="mt-1 text-xs text-rose-300">{errors.password.message}</p> : null}
          </div>
          <div>
            <Label htmlFor="otp" className="flex items-center gap-1">
              <Smartphone size={14} /> OTP / 2FA (optional)
            </Label>
            <Input id="otp" placeholder="123456" {...register("otp")} />
          </div>

          {error ? <p className="text-xs text-rose-300">{error}</p> : null}

          <Button className="w-full" type="submit" disabled={submitting}>
            <ShieldCheck size={16} className="mr-2" /> {submitting ? "Signing in..." : "Login"}
          </Button>
        </form>

        <div className="flex items-center justify-between text-xs text-slate-400">
          <Link href="#" className="hover:text-cyan-100">
            Forgot password?
          </Link>
          <span>SSO ready</span>
        </div>
      </Card>
    </div>
  );
}
