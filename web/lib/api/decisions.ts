import { apiRequest } from "./client";
import { NirnayCard } from "@/types/api";

export interface DecisionQueryParams {
  location: string;
  question: string;
  domain?: string;
  include_explanation?: boolean;
}

export async function evaluateDecision(
  params: DecisionQueryParams
): Promise<NirnayCard> {
  return apiRequest<NirnayCard>("/decisions", {
    method: "POST",
    body: JSON.stringify({
      location: params.location,
      question: params.question,
      domain: params.domain || "agriculture",
      include_explanation: params.include_explanation ?? true,
    }),
    cacheKey: `decision_${params.location}_${params.domain || "default"}`,
    timeoutMs: 8000,
  });
}
