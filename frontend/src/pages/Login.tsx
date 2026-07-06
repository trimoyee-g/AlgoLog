import { Github } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { supabase } from "@/lib/supabase";

function signIn(provider: "google" | "github") {
  supabase.auth.signInWithOAuth({
    provider,
    // After the provider redirects back, Supabase parses the session and we land on /app.
    options: { redirectTo: `${window.location.origin}/app` },
  });
}

export default function Login() {
  return (
    <div className="flex min-h-screen items-center justify-center px-6">
      <Card className="w-full max-w-sm p-8 text-center">
        <h1 className="text-xl font-medium">Sign in to AlgoLog</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Your practice log is private to your account.
        </p>
        <div className="mt-6 flex flex-col gap-3">
          <Button size="lg" onClick={() => signIn("google")}>
            Continue with Google
          </Button>
          <Button size="lg" variant="outline" onClick={() => signIn("github")}>
            <Github className="mr-2 h-4 w-4" />
            Continue with GitHub
          </Button>
        </div>
      </Card>
    </div>
  );
}
