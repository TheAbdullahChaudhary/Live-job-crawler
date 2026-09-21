import { NextResponse } from "next/server";

type Job = {
  id: string; title: string; company: string; location: string;
  workType: "remote" | "hybrid" | "onsite" | "unknown";
  source: string; url: string; postedAt: string | null; description: string;
};

type RemoteJob = Record<string, any>;
const roles = /devops|site reliability|\bsre\b|platform engineer|cloud engineer|infrastructure engineer/i;
const roleFilters: Record<string, string[]> = {
  devops: ["devops"],
  "site reliability": ["site reliability", "sre"],
  "cloud engineer": ["cloud engineer"],
};
const europeLocations = ["albania", "andorra", "armenia", "austria", "azerbaijan", "belarus", "belgium", "bosnia and herzegovina", "bulgaria", "croatia", "cyprus", "czechia", "denmark", "estonia", "finland", "france", "georgia", "germany", "greece", "hungary", "iceland", "ireland", "italy", "kosovo", "latvia", "liechtenstein", "lithuania", "luxembourg", "malta", "moldova", "monaco", "montenegro", "netherlands", "north macedonia", "norway", "poland", "portugal", "romania", "russia", "san marino", "serbia", "slovakia", "slovenia", "spain", "sweden", "switzerland", "turkey", "ukraine", "united kingdom", "vatican city"];
const middleEastLocations = ["bahrain", "cyprus", "egypt", "iran", "iraq", "israel", "jordan", "kuwait", "lebanon", "oman", "palestine", "qatar", "saudi arabia", "syria", "turkey", "united arab emirates", "yemen"];

function matchesRequestedLocation(jobLocation: string, selected: string) {
  if (!selected || selected === "all") return true;
  const value = jobLocation.toLowerCase();
  if (selected === "remote") return ["remote", "worldwide", "anywhere"].some((term) => value.includes(term));
  if (selected === "united states") return ["united states", "usa", "u.s.", "us only"].some((term) => value.includes(term));
  if (selected === "europe") return value.includes("europe") || europeLocations.some((term) => value.includes(term));
  if (selected === "middle east") return value.includes("middle east") || middleEastLocations.some((term) => value.includes(term));
  return value.includes(selected);
}

function stripHtml(value = "") {
  return value.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim().slice(0, 260);
}

function workType(...parts: string[]): Job["workType"] {
  const value = parts.join(" ").toLowerCase();
  if (value.includes("remote")) return "remote";
  if (value.includes("hybrid")) return "hybrid";
  if (value.includes("on-site") || value.includes("onsite")) return "onsite";
  return "unknown";
}

async function getJson(url: string) {
  const response = await fetch(url, {
    headers: { "user-agent": "OpsBoard/1.0 (+live job discovery)" },
    signal: AbortSignal.timeout(8000),
  });
  if (!response.ok) throw new Error(`${response.status}`);
  return response.json();
}

async function remotive(): Promise<Job[]> {
  const data = await getJson("https://remotive.com/api/remote-jobs?category=devops-sysadmin&limit=100");
  return (data.jobs || []).filter((item: RemoteJob) => roles.test(item.title || "")).map((item: RemoteJob) => ({
    id: `remotive-${item.id}`, title: item.title, company: item.company_name || "Company not listed",
    location: item.candidate_required_location || "Remote", workType: "remote" as const,
    source: "Remotive", url: item.url, postedAt: item.publication_date || null,
    description: stripHtml(item.description),
  }));
}

async function arbeitnow(): Promise<Job[]> {
  const data = await getJson("https://www.arbeitnow.com/api/job-board-api");
  return (data.data || []).filter((item: RemoteJob) => roles.test(item.title || "")).map((item: RemoteJob) => ({
    id: `arbeitnow-${item.slug || item.url}`, title: item.title,
    company: item.company_name || "Company not listed",
    location: item.location || (item.remote ? "Remote" : "Location not listed"),
    workType: item.remote ? "remote" as const : workType(item.location || ""),
    source: "Arbeitnow", url: item.url,
    postedAt: item.created_at ? new Date(item.created_at * 1000).toISOString() : null,
    description: stripHtml(item.description),
  }));
}

async function greenhouse(company: string, label: string): Promise<Job[]> {
  const data = await getJson(`https://boards-api.greenhouse.io/v1/boards/${company}/jobs?content=true`);
  return (data.jobs || []).filter((item: RemoteJob) => roles.test(item.title || "")).map((item: RemoteJob) => {
    const location = item.location?.name || "Location not listed";
    const description = stripHtml(item.content);
    return {
      id: `greenhouse-${item.id}`, title: item.title, company: label, location,
      workType: workType(location, description.slice(0, 180)), source: "Greenhouse",
      url: item.absolute_url, postedAt: item.updated_at || null, description,
    };
  });
}

const fallback: Job[] = [
  { id: "sample-1", title: "Senior Site Reliability Engineer", company: "CloudScale", location: "Remote · Europe", workType: "remote", source: "Example", url: "https://github.com/TheAbdullahChaudhary/Live-job-crawler", postedAt: new Date().toISOString(), description: "Own service reliability, observability and incident response for a distributed cloud platform." },
  { id: "sample-2", title: "Platform Engineer", company: "Northstar Labs", location: "Remote · Worldwide", workType: "remote", source: "Example", url: "https://github.com/TheAbdullahChaudhary/Live-job-crawler", postedAt: new Date(Date.now() - 86_400_000).toISOString(), description: "Build Kubernetes platform capabilities and reusable infrastructure modules for product teams." },
  { id: "sample-3", title: "DevOps Engineer", company: "SignalWorks", location: "London, UK", workType: "hybrid", source: "Example", url: "https://github.com/TheAbdullahChaudhary/Live-job-crawler", postedAt: new Date(Date.now() - 172_800_000).toISOString(), description: "Improve CI/CD, cloud security and production monitoring across a growing engineering organisation." },
  { id: "sample-4", title: "Cloud Infrastructure Engineer", company: "Binary Harbor", location: "Toronto, Canada", workType: "onsite", source: "Example", url: "https://github.com/TheAbdullahChaudhary/Live-job-crawler", postedAt: new Date(Date.now() - 259_200_000).toISOString(), description: "Design secure AWS foundations, Terraform modules and scalable deployment workflows." },
];

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const requestedRole = (searchParams.get("role") || "all").toLowerCase();
  const requestedLocation = (searchParams.get("location") || "all").toLowerCase();
  const providers = [
    { name: "Remotive", run: remotive },
    { name: "Arbeitnow", run: arbeitnow },
    { name: "Cloudflare", run: () => greenhouse("cloudflare", "Cloudflare") },
    { name: "Datadog", run: () => greenhouse("datadog", "Datadog") },
    { name: "GitLab", run: () => greenhouse("gitlab", "GitLab") },
  ];
  const results = await Promise.allSettled(providers.map((provider) => provider.run()));
  const sources = results.map((result, index) => ({ name: providers[index].name, ok: result.status === "fulfilled", count: result.status === "fulfilled" ? result.value.length : 0 }));
  const liveJobs = results.flatMap((result) => result.status === "fulfilled" ? result.value : []);
  const unique = [...new Map(liveJobs.map((job) => [job.url, job])).values()];
  const providersAvailable = results.some((result) => result.status === "fulfilled");
  const baseJobs = providersAvailable ? unique : fallback;
  const jobs = baseJobs.filter((job) => {
    const title = job.title.toLowerCase();
    const matchesRole = requestedRole === "all" || (roleFilters[requestedRole] || [requestedRole]).some((term) => title.includes(term));
    return matchesRole && matchesRequestedLocation(job.location, requestedLocation);
  });
  return NextResponse.json(
    { jobs, live: providersAvailable, fetchedAt: new Date().toISOString(), sources },
    { headers: { "cache-control": "public, max-age=120, s-maxage=300, stale-while-revalidate=600" } },
  );
}
