import { defineRailway, project, service } from "railway/iac";

// operating-cycles: the Operating rhythm cell. Variables stay unmanaged (secrets live in Railway only).
// operating-api sleeps when idle (Railway Serverless) and wakes on the next request.
// operating-publisher is a cron sweep of the outbox that exits after each run.
// Every service runs in Singapore next to Neon (aws-ap-southeast-1) and empire-platform; the IaC does not
// carry the region, so after the first deploy: railway scale --service <svc> asia-southeast1-eqsg3a=1 us-east4-eqdc4a=0
export default defineRailway(() => {
  const api = service("operating-api", {
    healthcheck: "/health",
    healthcheckTimeout: 60,
    deploy: { sleepApplication: true },
  });
  const publisher = service("operating-publisher", {
    startCommand: "operating-publish",
    deploy: { cronSchedule: "*/15 * * * *", restartPolicyType: "NEVER" },
  });

  return project("operating-cycles", {
    variables: { managed: false },
    resources: [api, publisher],
  });
});
