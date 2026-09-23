export function isRealAiMode(): boolean {
  return process.env.AI_SERVICE_MODE === "real";
}

export function aiServiceUrl(): string | null {
  const value = process.env.AI_SERVICE_URL?.trim();
  return value || null;
}
