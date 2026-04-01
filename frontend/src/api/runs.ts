import { useQuery } from "@tanstack/react-query";
import client from "./client";
import type { AssetMetricRow, RunDetail, RunSummary, TaxRow } from "../types/runs";

export const useRuns = (tag?: string) =>
  useQuery<RunSummary[]>({
    queryKey: ["runs", tag],
    queryFn: async () => {
      const { data } = await client.get("/api/runs", { params: tag ? { tag } : {} });
      return data;
    },
    staleTime: 5 * 60 * 1000,
  });

export const useRun = (id: number) =>
  useQuery<RunDetail>({
    queryKey: ["run", id],
    queryFn: async () => {
      const { data } = await client.get(`/api/runs/${id}`);
      return data;
    },
    staleTime: 5 * 60 * 1000,
  });

export const useRunAssets = (runId: number, assetName?: string) =>
  useQuery<AssetMetricRow[]>({
    queryKey: ["run-assets", runId, assetName],
    queryFn: async () => {
      const { data } = await client.get(`/api/runs/${runId}/assets`, {
        params: assetName ? { asset: assetName } : {},
      });
      return data;
    },
    staleTime: 5 * 60 * 1000,
  });

export const useRunTax = (runId: number) =>
  useQuery<TaxRow[]>({
    queryKey: ["run-tax", runId],
    queryFn: async () => {
      const { data } = await client.get(`/api/runs/${runId}/tax`);
      return data;
    },
    staleTime: 5 * 60 * 1000,
  });
