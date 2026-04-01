import { useQuery } from "@tanstack/react-query";
import client from "./client";
import type { McSetDetail, McSetSummary } from "../types/mc";

export const useMcSets = (tag?: string) =>
  useQuery<McSetSummary[]>({
    queryKey: ["mc-sets", tag],
    queryFn: async () => {
      const { data } = await client.get("/api/mc", { params: tag ? { tag } : {} });
      return data;
    },
    staleTime: 5 * 60 * 1000,
  });

export const useMcSet = (id: number, includeRuns = false) =>
  useQuery<McSetDetail>({
    queryKey: ["mc-set", id, includeRuns],
    queryFn: async () => {
      const { data } = await client.get(`/api/mc/${id}`, {
        params: includeRuns ? { include_runs: "true" } : {},
      });
      return data;
    },
    staleTime: 5 * 60 * 1000,
  });
