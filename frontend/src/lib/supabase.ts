import { createClient } from "@supabase/supabase-js";

// Set these in frontend/.env: VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY
// (Supabase dashboard > Project Settings > API). The anon key is safe to ship.
const url = import.meta.env.VITE_SUPABASE_URL as string;
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY as string;

export const supabase = createClient(url, anonKey);
