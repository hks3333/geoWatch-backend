import axios, { AxiosError } from 'axios';
import { MonitoringArea, AnalysisResult, NewMonitoringArea } from '../types';

// API Base URL from environment variable
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// Create axios instance with default config
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 seconds
});

// Error handler helper
const handleApiError = (error: unknown): never => {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<{ detail: string }>;
    const message = axiosError.response?.data?.detail || axiosError.message || 'An error occurred';
    throw new Error(message);
  }
  throw error;
};

// Get all monitoring areas
export const getMonitoringAreas = async (): Promise<MonitoringArea[]> => {
  try {
    const response = await api.get<MonitoringArea[]>('/monitoring-areas');
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
};

// Get a specific monitoring area by ID
export const getMonitoringArea = async (areaId: string): Promise<MonitoringArea> => {
  try {
    const response = await api.get<MonitoringArea>(`/monitoring-areas/${areaId}`);
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
};

// Create a new monitoring area
export const createMonitoringArea = async (newArea: NewMonitoringArea): Promise<{ area_id: string }> => {
  try {
    const response = await api.post<{ area_id: string }>('/monitoring-areas', newArea);
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
};

// Update monitoring area name
export const updateMonitoringArea = async (areaId: string, newName: string): Promise<MonitoringArea> => {
  try {
    const response = await api.patch<MonitoringArea>(`/monitoring-areas/${areaId}`, { name: newName });
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
};

// Delete monitoring area (soft delete)
export const deleteMonitoringArea = async (areaId: string): Promise<{ message: string }> => {
  try {
    const response = await api.delete<{ message: string }>(`/monitoring-areas/${areaId}`);
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
};

// Get analysis results for an area (paginated)
export const getAreaResults = async (
  areaId: string,
  limit: number = 10,
  offset: number = 0
): Promise<{ results: AnalysisResult[]; analysis_in_progress: boolean }> => {
  try {
    const response = await api.get<{ results: AnalysisResult[]; analysis_in_progress: boolean }>(
      `/monitoring-areas/${areaId}/results`
      // { params: { limit, offset } }
    );
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
};

// Get latest analysis result for an area
export const getLatestAreaResult = async (areaId: string): Promise<AnalysisResult | null> => {
  try {
    const response = await api.get<AnalysisResult>(`/monitoring-areas/${areaId}/latest`);
    return response.data;
  } catch (error) {
    // Return null if no results found (404)
    if (axios.isAxiosError(error) && error.response?.status === 404) {
      return null;
    }
    handleApiError(error);
  }
};

// Trigger new analysis for an area
export const triggerAnalysis = async (areaId: string): Promise<{ message: string }> => {
  try {
    const response = await api.post<{ message: string }>(`/monitoring-areas/${areaId}/analyze`);
    return response.data;
  } catch (error) {
    handleApiError(error);
  }
};