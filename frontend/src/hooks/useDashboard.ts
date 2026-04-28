import { useQuery } from '@tanstack/react-query';
import {
  fetchStats,
  fetchOpenBets,
  fetchResolvedBets,
  fetchTimeseries,
} from '../lib/api';

export function useStats() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['stats'],
    queryFn: fetchStats,
    refetchInterval: 5000,
    staleTime: 4000,
  });
  return { data, isLoading, error };
}

export function useOpenBets() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['openBets'],
    queryFn: fetchOpenBets,
    refetchInterval: 5000,
    staleTime: 4000,
  });
  return { data, isLoading, error };
}

export function useResolvedBets(limit = 50) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['resolvedBets', limit],
    queryFn: () => fetchResolvedBets(limit),
    refetchInterval: 5000,
    staleTime: 4000,
  });
  return { data, isLoading, error };
}

export function useTimeseries(days = 30) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['timeseries', days],
    queryFn: () => fetchTimeseries(days),
    refetchInterval: 5000,
    staleTime: 4000,
  });
  return { data, isLoading, error };
}
