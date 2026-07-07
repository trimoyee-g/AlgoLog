import { Link } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Lock,
  Download,
  Github,
  Star,
  Search,
  Mail,
  ArrowRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Reveal } from "@/components/motion/Reveal";
import { GlowOrb } from "@/components/motion/ParallaxLayer";
import { TiltCard, TiltLayer } from "@/components/motion/TiltCard";
import { HoverLift, ButtonMotion } from "@/components/motion/HoverLift";

const FEATURES = [
  {
    icon: Star,
    title: "Rate yourself honestly",
    body: "1-5 difficulty plus a blunt “did I actually solve it myself” flag, logged every time.",
  },
  {
    icon: Search,
    title: "Pattern recall",
    body: "Embedding similarity search surfaces problems you've struggled with before you repeat the mistake.",
  },
  {
    icon: Mail,
    title: "Weekly digest",
    body: "A Sunday email recap of what you practiced, what you avoided, and what to revisit.",
  },
];

const STEPS = [
  {
    title: "Solve as usual",
    body: "Keep grinding on LeetCode, Codeforces, or wherever you already practice.",
  },
  {
    title: "Rate the problem",
    body: "Open the extension popup for a quick 1-5 and a yes/no.",
  },
  {
    title: "Watch the pattern",
    body: "Your dashboard fills in with what's actually sticking and what isn't.",
  },
];

export default function Landing() {
  return (
    <div className="min-h-screen overflow-x-hidden">
      <motion.nav
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: "easeOut" }}
        className="sticky top-0 z-20 border-b border-border bg-background/80 backdrop-blur-md"
      >
        <div className="mx-auto flex max-w-[1180px] items-center justify-between px-6 py-4">
          <div className="flex items-center gap-2 text-[15px] font-medium">
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-sm font-semibold text-primary-foreground">
              A
            </div>
            AlgoLog
          </div>
          <div className="hidden items-center gap-7 text-[13.5px] text-muted-foreground sm:flex">
            <a href="#features" className="hover:text-foreground">
              Features
            </a>
            <a href="#how-it-works" className="hover:text-foreground">
              How it works
            </a>
          </div>
          <ButtonMotion>
            <Button asChild size="sm">
              <Link to="/app">Get started</Link>
            </Button>
          </ButtonMotion>
        </div>
      </motion.nav>

      <header className="relative overflow-hidden px-6 py-24 text-center">
        <GlowOrb
          speed={0.25}
          className="pointer-events-none absolute -left-32 -top-24 z-0 h-[380px] w-[380px] bg-primary/25"
        />
        <GlowOrb
          speed={-0.3}
          className="pointer-events-none absolute -right-40 top-10 z-0 h-[420px] w-[420px] bg-[hsl(280_70%_60%/0.18)]"
        />
        <GlowOrb
          speed={0.15}
          className="pointer-events-none absolute bottom-[-160px] left-1/2 z-0 h-[460px] w-[720px] -translate-x-1/2 bg-primary/10"
        />

        <div className="relative z-10 mx-auto max-w-[1180px]">
          <Reveal>
            <div className="mb-6 inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1.5 text-xs text-primary">
              <Lock className="h-3.5 w-3.5" />
              Runs locally · free · no API keys
            </div>
          </Reveal>

          <Reveal delay={0.08}>
            <h1 className="mx-auto max-w-[720px] text-[44px] font-medium leading-[1.2] tracking-tight">
              Track what you actually solve,{" "}
              <span className="text-primary">not just what you finish.</span>
            </h1>
          </Reveal>

          <Reveal delay={0.16}>
            <p className="mx-auto mt-5 max-w-[560px] text-base leading-relaxed text-muted-foreground">
              Rate questions on a difficulty scale of 1-5, answer if you really solved it
              yourself, and AlgoLog will quietly build a map of the patterns you keep tripping
              over.
            </p>
          </Reveal>

          <Reveal delay={0.24}>
            <div className="mt-8 flex items-center justify-center gap-3">
              <ButtonMotion>
                <Button asChild size="lg">
                  <Link to="/app">
                    Ready to start logging?
                  </Link>
                </Button>
              </ButtonMotion>
              <ButtonMotion>
                <Button asChild variant="outline" size="lg">
                  <a href="#features">
                    See how it works
                  </a>
                </Button>
              </ButtonMotion>
            </div>
          </Reveal>

          <Reveal delay={0.3}>
            <div className="mt-4 text-xs text-muted-foreground/70">
              Works with LeetCode, Codeforces, CodeChef, AtCoder, and GFG
            </div>
          </Reveal>

          <Reveal delay={0.38} y={40}>
            <TiltCard className="mx-auto mt-14 max-w-[900px]" maxTilt={6} lift={16}>
              <Card className="overflow-hidden p-0 text-left shadow-2xl shadow-black/20 [transform-style:preserve-3d]">
                <div className="flex gap-1.5 border-b border-border px-4 py-3">
                  <div className="h-2.5 w-2.5 rounded-full bg-border" />
                  <div className="h-2.5 w-2.5 rounded-full bg-border" />
                  <div className="h-2.5 w-2.5 rounded-full bg-border" />
                </div>
                <div className="p-6 [transform-style:preserve-3d]">
                  <TiltLayer depth={36} className="mb-4 grid grid-cols-4 gap-2.5">
                    {[
                      ["142", "Problems logged"],
                      ["187", "Total attempts"],
                      ["96", "Solved unaided"],
                      ["23", "Rated 4-5"],
                    ].map(([val, label]) => (
                      <div
                        key={label}
                        className="rounded-lg border border-border bg-secondary/40 p-3"
                      >
                        <div className="text-xl font-medium">{val}</div>
                        <div className="mt-0.5 text-[11px] text-muted-foreground">
                          {label}
                        </div>
                      </div>
                    ))}
                  </TiltLayer>
                  <TiltLayer depth={14} className="overflow-hidden rounded-lg border border-border">
                    <div className="grid grid-cols-4 gap-2 px-3.5 py-2 text-[11px] uppercase tracking-wide text-muted-foreground">
                      <div>Problem</div>
                      <div>Tags</div>
                      <div>Difficulty Rating</div>
                      <div>Solved it yourself?</div>
                    </div>
                    {[
                      ["Course schedule II", "graph", "3/5", "Yes"],
                      ["Word break", "dp", "4/5", "No"],
                    ].map((row) => (
                      <div
                        key={row[0]}
                        className="grid grid-cols-4 items-center gap-2 border-t border-border px-3.5 py-2.5 text-[12.5px]"
                      >
                        <div className="text-primary">{row[0]}</div>
                        <div>
                          <Badge variant="accent">{row[1]}</Badge>
                        </div>
                        <div>
                          <Badge variant="warning">{row[2]}</Badge>
                        </div>
                        <div className="text-muted-foreground">{row[3]}</div>
                      </div>
                    ))}
                  </TiltLayer>
                </div>
              </Card>
            </TiltCard>
          </Reveal>
        </div>
      </header>

      <section id="features" className="mx-auto max-w-[1180px] px-6 py-20">
        <Reveal className="mx-auto mb-12 max-w-[560px] text-center">
          <h2 className="text-[28px] font-medium tracking-tight">
            Built for honest practice
          </h2>
          <p className="mt-3 text-[15px] leading-relaxed text-muted-foreground">
            Not another problem list. AlgoLog tracks whether you're actually
            getting better.
          </p>
        </Reveal>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f, i) => (
            <Reveal key={f.title} delay={i * 0.08}>
              <HoverLift>
                <Card className="h-full p-5 transition-shadow hover:shadow-lg hover:shadow-primary/5">
                  <div className="mb-4 flex h-9 w-9 items-center justify-center rounded-lg bg-primary/15 text-primary">
                    <f.icon className="h-[17px] w-[17px]" />
                  </div>
                  <h3 className="mb-1.5 text-[15px] font-medium">{f.title}</h3>
                  <p className="text-[13px] leading-relaxed text-muted-foreground">
                    {f.body}
                  </p>
                </Card>
              </HoverLift>
            </Reveal>
          ))}
        </div>
      </section>

      <section id="how-it-works" className="mx-auto max-w-[1180px] px-6 pb-24">
        <Reveal className="mx-auto mb-12 max-w-[560px] text-center">
          <h2 className="text-[28px] font-medium tracking-tight">How it works</h2>
          <p className="mt-3 text-[15px] leading-relaxed text-muted-foreground">
            Three steps, done in seconds.
          </p>
        </Reveal>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          {STEPS.map((s, i) => (
            <Reveal key={s.title} delay={i * 0.1}>
              <HoverLift>
                <Card className="h-full p-6 transition-shadow hover:shadow-lg hover:shadow-primary/5">
                  <div className="mb-3.5 flex h-7 w-7 items-center justify-center rounded-md bg-secondary text-[13px] font-semibold text-primary">
                    {i + 1}
                  </div>
                  <h3 className="mb-1.5 text-[14.5px] font-medium">{s.title}</h3>
                  <p className="text-[13px] leading-relaxed text-muted-foreground">
                    {s.body}
                  </p>
                </Card>
              </HoverLift>
            </Reveal>
          ))}
        </div>
      </section>

      <footer className="border-t border-border">
        <Reveal>
          <div className="mx-auto flex max-w-[1180px] items-center justify-between px-6 py-7 text-xs text-muted-foreground">
            <div>Built by an engineer for engineers</div>
          </div>
        </Reveal>
      </footer>
    </div>
  );
}
