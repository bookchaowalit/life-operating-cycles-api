import { defineRailway, project, service } from "railway/iac";

// life-operating-cycles-api: the Operating rhythm cell. Variables stay unmanaged (secrets live in Railway only).
// operating-api sleeps when idle (Railway Serverless) and wakes on the next request.
// operating-publisher is a cron sweep of the outbox that exits after each run.
// Every service runs in Singapore next to Neon (aws-ap-southeast-1) and empire-platform; the IaC does not
// carry the region, so after the first deploy: railway scale --service <svc> asia-southeast1-eqsg3a=1 us-east4-eqdc4a=0
// Every service deploys from GitHub main after CI passes (Railway Wait for CI, 2026-10-18).
// Declared here so `railway config apply` keeps the connection instead of removing it.
const github = {
  type: "github" as const,
  repo: "bookchaowalit/life-operating-cycles-api",
  branch: "main",
  checkSuites: true,
};

export default defineRailway(() => {
  const api = service("operating-api", {
    source: github,
    healthcheck: "/health",
    healthcheckTimeout: 60,
    deploy: { sleepApplication: true },
  });
  const publisher = service("operating-publisher", {
    source: github,
    startCommand: "operating-publish",
    deploy: { cronSchedule: "*/15 * * * *", restartPolicyType: "NEVER" },
  });

  return project("life-operating-cycles-api", {
    variables: { managed: false },
    resources: [api, publisher],
  });
});
