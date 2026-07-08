import { useEffect, useState } from "react";
import { Routes, Route, Navigate } from "react-router-dom";
import type { Session } from "@supabase/supabase-js";
import Landing from "@/pages/Landing";
import Dashboard from "@/pages/Dashboard";
import Review from "@/pages/Review";
import Login from "@/pages/Login";
import { supabase } from "@/lib/supabase";

function useSession() {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setLoading(false);
    });
    const { data: sub } = supabase.auth.onAuthStateChange((_e, s) => setSession(s));
    return () => sub.subscription.unsubscribe();
  }, []);

  return { session, loading };
}

function RequireAuth({ children }: { children: JSX.Element }) {
  const { session, loading } = useSession();
  if (loading) return null; // ponytail: blank while the session resolves; add a spinner if it ever feels slow
  return session ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route
        path="/app"
        element={
          <RequireAuth>
            <Dashboard />
          </RequireAuth>
        }
      />
      <Route
        path="/review"
        element={
          <RequireAuth>
            <Review />
          </RequireAuth>
        }
      />
    </Routes>
  );
}
