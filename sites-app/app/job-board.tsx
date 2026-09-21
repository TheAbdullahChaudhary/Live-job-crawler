"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowUpRight, Bookmark, BriefcaseBusiness, Building2, Check, Clock3, Globe2, MapPin, RefreshCw, SlidersHorizontal, Sparkles, X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectGroup, SelectItem, SelectLabel, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";

type Job = {
  id: string; title: string; company: string; location: string;
  workType: "remote" | "hybrid" | "onsite" | "unknown";
  source: string; url: string; postedAt: string | null; description: string;
};

type Feed = {
  jobs: Job[]; live: boolean; fetchedAt: string;
  sources: { name: string; ok: boolean; count: number }[];
};

const typeStyles: Record<Job["workType"], string> = {
  remote: "border-emerald-400/25 bg-emerald-400/10 text-emerald-300",
  hybrid: "border-amber-400/25 bg-amber-400/10 text-amber-300",
  onsite: "border-sky-400/25 bg-sky-400/10 text-sky-300",
  unknown: "border-white/10 bg-white/5 text-slate-400",
};

const europeCountries = [
  "Albania", "Andorra", "Armenia", "Austria", "Azerbaijan", "Belarus", "Belgium",
  "Bosnia and Herzegovina", "Bulgaria", "Croatia", "Cyprus", "Czechia", "Denmark",
  "Estonia", "Finland", "France", "Georgia", "Germany", "Greece", "Hungary", "Iceland",
  "Ireland", "Italy", "Kosovo", "Latvia", "Liechtenstein", "Lithuania", "Luxembourg",
  "Malta", "Moldova", "Monaco", "Montenegro", "Netherlands", "North Macedonia", "Norway",
  "Poland", "Portugal", "Romania", "Russia", "San Marino", "Serbia", "Slovakia", "Slovenia",
  "Spain", "Sweden", "Switzerland", "Turkey", "Ukraine", "United Kingdom", "Vatican City",
];

const middleEastCountries = [
  "Bahrain", "Egypt", "Iran", "Iraq", "Israel", "Jordan", "Kuwait", "Lebanon", "Oman",
  "Palestine", "Qatar", "Saudi Arabia", "Syria", "United Arab Emirates", "Yemen",
];

const roleTerms: Record<string, string[]> = {
  devops: ["devops"],
  "site reliability": ["site reliability", "sre"],
  "cloud engineer": ["cloud engineer"],
};

function matchesLocation(jobLocation: string, selected: string) {
  if (selected === "all") return true;
  const value = jobLocation.toLowerCase();
  if (selected === "remote") return ["remote", "worldwide", "anywhere"].some((term) => value.includes(term));
  if (selected === "united states") return ["united states", "usa", "u.s.", "us only"].some((term) => value.includes(term));
  if (selected === "europe") return value.includes("europe") || europeCountries.some((country) => value.includes(country.toLowerCase()));
  if (selected === "middle east") return value.includes("middle east") || [...middleEastCountries, "Turkey", "Cyprus"].some((country) => value.includes(country.toLowerCase()));
  return value.includes(selected);
}

function relativeDate(value: string | null) {
  if (!value) return "Date not listed";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const days = Math.max(0, Math.floor((Date.now() - date.getTime()) / 86_400_000));
  if (days === 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 30) return `${days} days ago`;
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export default function JobBoard() {
  const [feed, setFeed] = useState<Feed | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [role, setRole] = useState("all");
  const [location, setLocation] = useState("all");
  const [workType, setWorkType] = useState("all");
  const [sort, setSort] = useState("newest");
  const [saved, setSaved] = useState<string[]>([]);
  const [showSaved, setShowSaved] = useState(false);

  useEffect(() => {
    try { setSaved(JSON.parse(localStorage.getItem("opsboard-saved") || "[]")); }
    catch { setSaved([]); }
  }, []);

  const loadJobs = useCallback(async (filters?: { role: string; location: string }) => {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams();
      if (filters?.role && filters.role !== "all") params.set("role", filters.role);
      if (filters?.location && filters.location !== "all") params.set("location", filters.location);
      const response = await fetch(`/api/jobs${params.size ? `?${params}` : ""}`, { cache: "no-store" });
      if (!response.ok) throw new Error("Feed unavailable");
      setFeed(await response.json());
    } catch {
      setError("The job feeds could not be reached. Try refreshing in a moment.");
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { loadJobs(); }, [loadJobs]);

  const searchLiveJobs = () => loadJobs({ role, location });

  const toggleSaved = (id: string) => {
    setSaved((current) => {
      const next = current.includes(id) ? current.filter((item) => item !== id) : [...current, id];
      localStorage.setItem("opsboard-saved", JSON.stringify(next));
      return next;
    });
  };

  const filtered = useMemo(() => {
    const jobs = (feed?.jobs || []).filter((job) => {
      const title = job.title.toLowerCase();
      const matchesRole = role === "all" || roleTerms[role].some((term) => title.includes(term));
      const hasMatchingLocation = matchesLocation(job.location, location);
      const matchesType = workType === "all" || job.workType === workType;
      const matchesSaved = !showSaved || saved.includes(job.id);
      return matchesRole && hasMatchingLocation && matchesType && matchesSaved;
    });
    return jobs.sort((a, b) => {
      if (sort === "company") return a.company.localeCompare(b.company);
      if (sort === "title") return a.title.localeCompare(b.title);
      return new Date(b.postedAt || 0).getTime() - new Date(a.postedAt || 0).getTime();
    });
  }, [feed, location, role, saved, showSaved, sort, workType]);

  const remoteCount = feed?.jobs.filter((job) => job.workType === "remote").length || 0;
  const sourceCount = feed?.sources.filter((source) => source.ok).length || 0;
  const filtersActive = Boolean(role !== "all" || location !== "all" || workType !== "all" || showSaved);
  const clearFilters = () => { setRole("all"); setLocation("all"); setWorkType("all"); setShowSaved(false); };

  return (
    <main className="min-h-screen bg-[#07100f] text-slate-100">
      <header className="border-b border-white/8 bg-[#081312]/90 backdrop-blur-xl">
        <div className="mx-auto flex max-w-[1480px] items-center justify-between px-5 py-4 lg:px-8">
          <div className="flex items-center gap-3">
            <div className="grid size-10 place-items-center rounded-xl border border-emerald-300/20 bg-emerald-300/10 text-emerald-300 shadow-[0_0_28px_rgba(52,211,153,.12)]"><BriefcaseBusiness className="size-5" /></div>
            <div>
              <div className="flex items-center gap-2"><span className="text-[15px] font-semibold tracking-tight">OpsBoard</span><Badge className="border-emerald-400/20 bg-emerald-400/10 text-[10px] text-emerald-300">LIVE</Badge></div>
              <p className="text-xs text-slate-500">DevOps · SRE · Platform Engineering</p>
            </div>
          </div>
          <Button variant="outline" className="border-white/10 bg-white/[.03] text-slate-200 hover:bg-white/[.07] hover:text-white" onClick={searchLiveJobs} disabled={loading}>
            <RefreshCw className={`size-4 ${loading ? "animate-spin" : ""}`} /><span className="hidden sm:inline">Refresh feeds</span>
          </Button>
        </div>
      </header>

      <section className="border-b border-white/8 bg-[radial-gradient(circle_at_15%_0%,rgba(52,211,153,.12),transparent_30%),linear-gradient(180deg,#091716_0%,#07100f_100%)]">
        <div className="mx-auto grid max-w-[1480px] gap-7 px-5 py-8 lg:grid-cols-[minmax(0,1fr)_auto] lg:px-8 lg:py-10">
          <div>
            <div className="mb-3 flex items-center gap-2 text-xs font-medium uppercase tracking-[.18em] text-emerald-300/80"><Sparkles className="size-3.5" /> Curated engineering roles</div>
            <h1 className="max-w-3xl text-3xl font-semibold tracking-[-.035em] text-white sm:text-4xl lg:text-[44px] lg:leading-[1.08]">Find the infrastructure role worth your time.</h1>
            <p className="mt-3 max-w-2xl text-[15px] leading-7 text-slate-400">One focused feed for DevOps, SRE, platform and cloud engineers—without the noise of a general job board.</p>
          </div>
          <div className="grid grid-cols-3 gap-px self-end overflow-hidden rounded-2xl border border-white/10 bg-white/10">
            {[[feed?.jobs.length || 0, "Open roles"], [remoteCount, "Remote"], [sourceCount, "Sources live"]].map(([value, label]) => (
              <div key={label} className="min-w-[102px] bg-[#0b1716] px-4 py-4 text-center sm:min-w-[124px]"><div className="font-mono text-2xl font-semibold text-white">{loading ? "—" : value}</div><div className="mt-1 text-[11px] uppercase tracking-wider text-slate-500">{label}</div></div>
            ))}
          </div>
        </div>
      </section>

      <div className="mx-auto grid max-w-[1480px] gap-6 px-5 py-6 lg:grid-cols-[280px_minmax(0,1fr)] lg:px-8 lg:py-8">
        <aside className="h-fit rounded-2xl border border-white/8 bg-[#0b1514] p-4 lg:sticky lg:top-6">
          <div className="mb-5 flex items-center justify-between"><div className="flex items-center gap-2 text-sm font-semibold"><SlidersHorizontal className="size-4 text-emerald-300" /> Filters</div>{filtersActive && <button className="text-xs text-slate-500 hover:text-white" onClick={clearFilters}>Reset</button>}</div>
          <div className="space-y-5">
            <div className="space-y-2">
              <Label>Role and technology</Label>
              <Select value={role} onValueChange={setRole}>
                <SelectTrigger className="w-full border-white/10 bg-[#07100f] text-white"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All roles</SelectItem>
                  <SelectItem value="devops">DevOps Engineer</SelectItem>
                  <SelectItem value="site reliability">Site Reliability Engineer</SelectItem>
                  <SelectItem value="cloud engineer">Cloud Engineer</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Location</Label>
              <Select value={location} onValueChange={setLocation}>
                <SelectTrigger className="w-full border-white/10 bg-[#07100f] text-white"><SelectValue /></SelectTrigger>
                <SelectContent className="max-h-[360px]">
                  <SelectGroup>
                    <SelectLabel>All locations</SelectLabel>
                    <SelectItem value="all">All locations</SelectItem>
                    <SelectItem value="remote">Remote / Worldwide</SelectItem>
                  </SelectGroup>
                  <SelectGroup>
                    <SelectLabel>Americas and Oceania</SelectLabel>
                    <SelectItem value="united states">United States</SelectItem>
                    <SelectItem value="australia">Australia</SelectItem>
                  </SelectGroup>
                  <SelectGroup>
                    <SelectLabel>Europe</SelectLabel>
                    <SelectItem value="europe">Europe — All countries</SelectItem>
                    {europeCountries.map((country) => <SelectItem key={country} value={country.toLowerCase()}>{country}</SelectItem>)}
                  </SelectGroup>
                  <SelectGroup>
                    <SelectLabel>Middle East</SelectLabel>
                    <SelectItem value="middle east">Middle East — All countries</SelectItem>
                    {middleEastCountries.map((country) => <SelectItem key={country} value={country.toLowerCase()}>{country}</SelectItem>)}
                  </SelectGroup>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2"><Label>Work style</Label><Select value={workType} onValueChange={setWorkType}><SelectTrigger className="w-full border-white/10 bg-[#07100f] text-white"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="all">All work styles</SelectItem><SelectItem value="remote">Remote</SelectItem><SelectItem value="hybrid">Hybrid</SelectItem><SelectItem value="onsite">On-site</SelectItem></SelectContent></Select></div>
            <Button className="w-full bg-emerald-300 text-[#06100e] shadow-[0_10px_30px_rgba(52,211,153,.12)] hover:bg-emerald-200" onClick={searchLiveJobs} disabled={loading}>
              <RefreshCw className={`size-4 ${loading ? "animate-spin" : ""}`} />
              {loading ? "Searching live sources…" : "Search live jobs"}
            </Button>
            <Button variant={showSaved ? "default" : "outline"} className={showSaved ? "w-full bg-emerald-300 text-[#06100e] hover:bg-emerald-200" : "w-full border-white/10 bg-transparent text-slate-300 hover:bg-white/5 hover:text-white"} onClick={() => setShowSaved((value) => !value)}><Bookmark className="size-4" /> Saved roles <span className="ml-auto font-mono text-xs">{saved.length}</span></Button>
          </div>
          <div className="mt-6 border-t border-white/8 pt-5">
            <p className="mb-3 text-[11px] font-semibold uppercase tracking-[.16em] text-slate-600">Source health</p>
            <div className="space-y-2.5">{(feed?.sources || [{ name: "Remotive", ok: false, count: 0 }, { name: "Arbeitnow", ok: false, count: 0 }]).map((source) => <div className="flex items-center gap-2 text-xs" key={source.name}><span className={`size-1.5 rounded-full ${source.ok ? "bg-emerald-400" : "bg-slate-700"}`} /><span className="text-slate-400">{source.name}</span><span className="ml-auto font-mono text-slate-600">{source.ok ? source.count : "offline"}</span></div>)}</div>
          </div>
        </aside>

        <section>
          <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div><p className="text-lg font-semibold text-white">{showSaved ? "Saved roles" : "Matching roles"}</p><p className="mt-0.5 text-xs text-slate-500">{loading ? "Checking live sources…" : `${filtered.length} roles · Updated ${feed ? relativeDate(feed.fetchedAt) : "just now"}`}</p></div>
            <Select value={sort} onValueChange={setSort}><SelectTrigger className="w-full border-white/10 bg-[#0b1514] text-slate-300 sm:w-[170px]"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="newest">Newest first</SelectItem><SelectItem value="company">Company A–Z</SelectItem><SelectItem value="title">Role A–Z</SelectItem></SelectContent></Select>
          </div>
          {feed && !feed.live && <div className="mb-4 flex items-start gap-3 rounded-xl border border-amber-300/15 bg-amber-300/[.06] px-4 py-3 text-sm text-amber-100/80"><Clock3 className="mt-0.5 size-4 shrink-0 text-amber-300" />Live providers are slow right now, so example roles are shown until the next refresh.</div>}
          {error ? (
            <div className="rounded-2xl border border-rose-300/15 bg-rose-300/[.05] p-8 text-center"><p className="text-sm text-rose-100">{error}</p><Button className="mt-4 bg-white text-slate-950 hover:bg-slate-200" onClick={loadJobs}>Try again</Button></div>
          ) : loading ? (
            <div className="grid gap-3 xl:grid-cols-2">{Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-[224px] rounded-2xl bg-white/[.05]" />)}</div>
          ) : filtered.length ? (
            <div className="grid gap-3 xl:grid-cols-2">{filtered.map((job) => {
              const isSaved = saved.includes(job.id);
              return <article key={job.id} className="group flex min-h-[224px] flex-col rounded-2xl border border-white/8 bg-[#0b1514] p-5 transition hover:-translate-y-0.5 hover:border-emerald-300/25 hover:bg-[#0d1918] hover:shadow-[0_18px_55px_rgba(0,0,0,.2)]">
                <div className="flex items-start gap-4"><div className="grid size-11 shrink-0 place-items-center rounded-xl border border-white/8 bg-white/[.035] text-base font-semibold text-slate-300">{job.company.slice(0, 1).toUpperCase()}</div><div className="min-w-0 flex-1"><a href={job.url} target="_blank" rel="noreferrer" className="inline-flex items-start gap-1.5 text-[16px] font-semibold leading-6 text-white transition group-hover:text-emerald-200">{job.title}<ArrowUpRight className="mt-1 size-3.5 shrink-0 opacity-0 transition group-hover:opacity-100" /></a><p className="mt-1 flex items-center gap-1.5 text-sm text-slate-400"><Building2 className="size-3.5" /> {job.company}</p></div><button aria-label={isSaved ? "Remove saved job" : "Save job"} onClick={() => toggleSaved(job.id)} className={`grid size-9 shrink-0 place-items-center rounded-lg border transition ${isSaved ? "border-emerald-300/25 bg-emerald-300/10 text-emerald-300" : "border-white/8 text-slate-600 hover:border-white/15 hover:text-white"}`}>{isSaved ? <Check className="size-4" /> : <Bookmark className="size-4" />}</button></div>
                <p className="mt-4 line-clamp-2 text-sm leading-6 text-slate-500">{job.description || "Explore the full role, responsibilities and requirements on the employer’s job page."}</p>
                <div className="mt-auto flex flex-wrap items-end justify-between gap-3 border-t border-white/6 pt-4"><div className="flex flex-wrap gap-2"><Badge variant="outline" className={typeStyles[job.workType]}>{job.workType === "unknown" ? "Flexible" : job.workType}</Badge><span className="inline-flex items-center gap-1.5 text-xs text-slate-500"><MapPin className="size-3.5" /> {job.location}</span></div><div className="text-right text-[11px] leading-5 text-slate-600"><div>{relativeDate(job.postedAt)}</div><div>{job.source}</div></div></div>
              </article>;
            })}</div>
          ) : (
            <div className="grid min-h-[320px] place-items-center rounded-2xl border border-dashed border-white/10 bg-white/[.015] p-8 text-center"><div><Globe2 className="mx-auto size-8 text-slate-600" /><p className="mt-4 font-medium text-white">No roles match those filters</p><p className="mt-1 text-sm text-slate-500">Try a broader location or clear one of your filters.</p><Button variant="outline" className="mt-4 border-white/10 bg-transparent text-slate-300" onClick={clearFilters}><X className="size-4" /> Clear filters</Button></div></div>
          )}
        </section>
      </div>
    </main>
  );
}
