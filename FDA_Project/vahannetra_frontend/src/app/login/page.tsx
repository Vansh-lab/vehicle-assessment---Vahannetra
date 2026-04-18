"use client";

import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useNavigate } from "react-router-dom";
import { ShieldCheck, Smartphone } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { loginWithBackend, requestPasswordOtp, verifyPasswordOtp } from "@/lib/api/services";
import { isSessionActive, setSessionFromAuth } from "@/lib/auth/session";

const schema = z.object({
  email: z.string().email("Enter a valid work email"),
  password: z.string().min(6, "Password must be at least 6 characters"),
  otp: z.string().optional(),
});

type LoginValues = z.infer<typeof schema>;

export default function LoginPage() {
  const navigate = useNavigate();
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [forgotOpen, setForgotOpen] = useState(false);
  const [forgotEmail, setForgotEmail] = useState("");
  const [forgotOtp, setForgotOtp] = useState("");
  const [forgotMessage, setForgotMessage] = useState("");
  const [forgotLoading, setForgotLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginValues>({
    resolver: zodResolver(schema),
    defaultValues: { email: "", password: "", otp: "" },
  });

  useEffect(() => {
    if (isSessionActive()) {
      navigate("/dashboard", { replace: true });
    }
  }, [navigate]);

  const onSubmit = async (values: LoginValues) => {
    try {
      setSubmitting(true);
      setError("");
      const auth = await loginWithBackend(values);
      setSessionFromAuth(auth);
      navigate("/dashboard");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Login failed");
    } finally {
      setSubmitting(false);
    }
  };

  const sendForgotOtp = async () => {
    try {
      setForgotLoading(true);
      setForgotMessage("");
      const response = await requestPasswordOtp(forgotEmail);
      setForgotMessage(response.message);
    } catch (forgotError) {
      setForgotMessage(forgotError instanceof Error ? forgotError.message : "Failed to send OTP");
    } finally {
      setForgotLoading(false);
    }
  };

  const verifyForgotOtp = async () => {
    try {
      setForgotLoading(true);
      setForgotMessage("");
      await verifyPasswordOtp(forgotEmail, forgotOtp);
      setForgotMessage("OTP verified. You can now continue standard login.");
    } catch (forgotError) {
      setForgotMessage(forgotError instanceof Error ? forgotError.message : "OTP verification failed");
    } finally {
      setForgotLoading(false);
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
          <button type="button" onClick={() => setForgotOpen((prev) => !prev)} className="hover:text-cyan-100">
            {forgotOpen ? "Back to login" : "Forgot password?"}
          </button>
          <span>SSO ready</span>
        </div>

        {forgotOpen ? (
          <Card className="space-y-3 border-amber-300/20 p-4">
            <p className="text-sm font-semibold text-slate-100">Password recovery (OTP)</p>
            <div>
              <Label htmlFor="forgot-email">Work Email</Label>
              <Input
                id="forgot-email"
                type="email"
                placeholder="ops@insurer.com"
                value={forgotEmail}
                onChange={(event) => setForgotEmail(event.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="forgot-otp">OTP</Label>
              <Input
                id="forgot-otp"
                type="text"
                inputMode="numeric"
                maxLength={6}
                autoComplete="one-time-code"
                placeholder="123456"
                value={forgotOtp}
                onChange={(event) => setForgotOtp(event.target.value)}
              />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <Button
                type="button"
                variant="secondary"
                onClick={() => void sendForgotOtp()}
                disabled={!forgotEmail || forgotLoading}
              >
                Send OTP
              </Button>
              <Button
                type="button"
                onClick={() => void verifyForgotOtp()}
                disabled={!forgotEmail || !forgotOtp || forgotLoading}
              >
                Verify OTP
              </Button>
            </div>
            {forgotMessage ? <p className="text-xs text-slate-300">{forgotMessage}</p> : null}
          </Card>
        ) : null}
      </Card>
    </div>
  );
}
