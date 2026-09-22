import { apiRequest } from "./client";
import { ShowcaseStatus } from "@/types/api";

export async function startShowcase(): Promise<any> {
  return apiRequest<any>("/internal/showcase/start", {
    method: "POST",
    timeoutMs: 12000,
  });
}

export async function nextShowcaseStep(): Promise<any> {
  return apiRequest<any>("/internal/showcase/next", {
    method: "POST",
    timeoutMs: 12000,
  });
}

export async function resetShowcase(): Promise<any> {
  return apiRequest<any>("/internal/showcase/reset", {
    method: "POST",
    timeoutMs: 8000,
  });
}

export async function fetchShowcaseStatus(): Promise<ShowcaseStatus> {
  return apiRequest<ShowcaseStatus>("/internal/showcase/status", {
    timeoutMs: 4000,
  });
}
