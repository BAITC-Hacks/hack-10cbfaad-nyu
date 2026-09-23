import { randomUUID } from "node:crypto";
import type { CartResult, ChatAction } from "@/lib/types";
import { ttlSeconds } from "@/lib/server/request";

export type ProposalStatus = "AWAITING_CONFIRMATION" | "COMPLETED" | "EXPIRED";

export interface PendingProposal {
  proposal_id: string;
  conversation_id: string;
  product_id: number;
  quantity: number;
  session_id: string;
  status: ProposalStatus;
  created_at: string;
}

interface IdempotencyRecord {
  session_id: string;
  key: string;
  result: CartResult;
}

interface ProposalStore {
  proposals: Map<string, PendingProposal>;
  idempotency: Map<string, IdempotencyRecord>;
}

declare global {
  // Next.js can evaluate different route handlers in separate server bundles.
  // Keep the mock MVP store on globalThis so those bundles share the same maps.
  // eslint-disable-next-line no-var
  var __ektCartProposalStore: ProposalStore | undefined;
}

const store =
  globalThis.__ektCartProposalStore ??
  (globalThis.__ektCartProposalStore = {
    proposals: new Map<string, PendingProposal>(),
    idempotency: new Map<string, IdempotencyRecord>(),
  });

export function saveProposal(action: ChatAction, conversationId: string, sessionId: string): void {
  store.proposals.set(action.proposal_id, {
    proposal_id: action.proposal_id,
    conversation_id: conversationId,
    product_id: action.product_id,
    quantity: action.quantity,
    session_id: sessionId,
    status: "AWAITING_CONFIRMATION",
    created_at: new Date().toISOString(),
  });
}

export function getProposal(proposalId: string, sessionId: string): PendingProposal | null {
  const proposal = store.proposals.get(proposalId);
  if (!proposal || proposal.session_id !== sessionId) return null;

  if (
    proposal.status === "AWAITING_CONFIRMATION" &&
    Date.now() - new Date(proposal.created_at).getTime() > ttlSeconds() * 1000
  ) {
    proposal.status = "EXPIRED";
  }

  return proposal;
}

export function markCompleted(proposalId: string): void {
  const proposal = store.proposals.get(proposalId);
  if (proposal) proposal.status = "COMPLETED";
}

export function getIdempotencyResult(sessionId: string, key: string): CartResult | null {
  const record = store.idempotency.get(`${sessionId}:${key}`);
  return record?.result || null;
}

export function saveIdempotencyResult(sessionId: string, key: string, result: CartResult): void {
  store.idempotency.set(`${sessionId}:${key}`, { session_id: sessionId, key, result });
}

export function makeSessionId(): string {
  return randomUUID();
}
