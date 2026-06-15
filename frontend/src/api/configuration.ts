import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import client from "./client";
import type { Asset, AssetFile, WorldConfig } from "../types/configuration";

export const useWorldConfig = () =>
  useQuery<WorldConfig>({
    queryKey: ["configuration"],
    queryFn: async () => {
      const { data } = await client.get<WorldConfig>("/api/configuration");
      return data;
    },
  });

export const useSaveWorldConfig = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (config: WorldConfig) =>
      client.put("/api/configuration", config),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["configuration"] }),
  });
};

export const useAssets = () =>
  useQuery<AssetFile[]>({
    queryKey: ["configuration-assets"],
    queryFn: async () => {
      const { data } = await client.get<AssetFile[]>(
        "/api/configuration/assets"
      );
      return data;
    },
  });

export const useSaveAsset = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      filename,
      data,
    }: {
      filename: string;
      data: Asset;
    }) => client.put(`/api/configuration/assets/${filename}`, data),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["configuration-assets"] }),
  });
};

export const useDeleteAsset = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (filename: string) =>
      client.delete(`/api/configuration/assets/${filename}`),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["configuration-assets"] }),
  });
};
