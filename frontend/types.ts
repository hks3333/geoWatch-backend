export type MonitoringType = 'forest' | 'water';
export type AreaStatus = 'active' | 'pending' | 'paused' | 'error' | 'deleted';
export type ProcessingStatus = 'in_progress' | 'completed' | 'failed';

export interface LatLng {
  lat: number;
  lng: number;
}

export interface MonitoringArea {
  area_id: string;
  name: string;
  type: MonitoringType;
  user_id: string;
  polygon: LatLng[];
  rectangle_bounds?: {
    southWest: LatLng;
    northEast: LatLng;
  };
  status: AreaStatus;
  created_at: string;
  last_checked_at: string | null;
  baseline_captured: boolean;
  total_analyses: number;
  latest_change_percentage?: number | null;
}

export interface ImageUrls {
  baseline_image: string;
  current_image: string;
  baseline_computed: string;
  current_computed: string;
  difference_image: string;
}

export interface AnalysisMetrics {
  analysis_type: string;
  baseline_date: string;
  current_date: string;
  baseline_cloud_coverage: number;
  current_cloud_coverage: number;
  valid_pixels_percentage: number;
  loss_hectares: number;
  gain_hectares: number;
  stable_hectares: number;
  total_hectares: number;
  loss_percentage: number;
  gain_percentage: number;
  net_change_percentage: number;
}

export interface AnalysisResult {
  result_id: string;
  area_id: string;
  area_type?: string;
  timestamp: string;
  processing_status: ProcessingStatus;
  
  // New Sentinel-2 fields
  image_urls?: ImageUrls | null;
  metrics?: AnalysisMetrics | null;
  bounds?: number[] | null;
  
  // Top-level fields
  baseline_date?: string | null;
  current_date?: string | null;
  analysis_type?: string | null;
  
  // Backward compatibility
  change_percentage: number | null;
  generated_map_url?: string | null;
  
  // Error handling
  error_message: string | null;
  
  // Legacy fields (for backward compatibility)
  change_detected?: boolean;
  change_type?: MonitoringType;
  baseline_map_url?: string;
  current_map_url?: string;
  change_map_url?: string | null;
}

export interface NewMonitoringArea {
  name: string;
  type: MonitoringType;
  rectangle_bounds: {
    southWest: LatLng;
    northEast: LatLng;
  }
}