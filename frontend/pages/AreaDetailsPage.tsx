import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { MonitoringArea, AnalysisResult } from '../types';
import * as api from '../services/apiService';
import { Button, Card, Badge, Skeleton } from '../components/common/ui';
import { ChevronLeftIcon, MapPinIcon, ClockIcon, AlertTriangleIcon, ForestIcon, WaterIcon, RefreshCwIcon, DownloadIcon, Loader2Icon } from '../components/common/Icons';
import EditAreaModal from '../components/EditAreaModal';
import DeleteConfirmationModal from '../components/DeleteConfirmationModal';
import ReportViewer from '../components/ReportViewer';
import { fromUrl } from 'geotiff';

declare const L: any; // Use Leaflet global

// Helper function to load and render GeoTIFF on Leaflet map
async function loadGeoTIFF(url: string, map: any, layerRef: any, opacity: number = 0.8, bounds?: any) {
    const tiff = await fromUrl(url);
    const image = await tiff.getImage();
    const rasters = await image.readRasters();
    
    const width = image.getWidth();
    const height = image.getHeight();
    const numBands = rasters.length;
    
    // Create canvas
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d');
    
    if (!ctx) throw new Error('Could not get canvas context');
    
    const imageData = ctx.createImageData(width, height);
    
    // Helper to normalize values to 0-255 range
    const normalize = (value: number, min: number, max: number) => {
        if (max === min) return 0;
        return Math.floor(((value - min) / (max - min)) * 255);
    };
    
    // Find min/max for each band for normalization
    const getMinMax = (band: any) => {
        let min = Infinity;
        let max = -Infinity;
        for (let i = 0; i < band.length; i++) {
            if (band[i] < min) min = band[i];
            if (band[i] > max) max = band[i];
        }
        return { min, max };
    };
    
    if (numBands >= 3) {
        // RGB image - normalize each band
        const r = getMinMax(rasters[0]);
        const g = getMinMax(rasters[1]);
        const b = getMinMax(rasters[2]);
        
        for (let i = 0; i < width * height; i++) {
            imageData.data[i * 4] = normalize(rasters[0][i], r.min, r.max);
            imageData.data[i * 4 + 1] = normalize(rasters[1][i], g.min, g.max);
            imageData.data[i * 4 + 2] = normalize(rasters[2][i], b.min, b.max);
            imageData.data[i * 4 + 3] = 255;
        }
    } else {
        // Single band - grayscale
        const stats = getMinMax(rasters[0]);
        for (let i = 0; i < width * height; i++) {
            const value = normalize(rasters[0][i], stats.min, stats.max);
            imageData.data[i * 4] = value;
            imageData.data[i * 4 + 1] = value;
            imageData.data[i * 4 + 2] = value;
            imageData.data[i * 4 + 3] = 255;
        }
    }
    
    ctx.putImageData(imageData, 0, 0);
    const dataUrl = canvas.toDataURL();
    
    // Use provided bounds (must be passed from caller)
    if (!bounds) {
        throw new Error('Bounds must be provided for image overlay');
    }
    
    const layer = L.imageOverlay(dataUrl, bounds, { opacity, interactive: true });
    layer.addTo(map);
    
    if (layerRef && layerRef.current !== undefined) {
        layerRef.current = layer;
    }
    
    return layer;
}

const AreaDetailMap: React.FC<{ area: MonitoringArea }> = ({ area }) => {
    const mapContainerRef = useRef<HTMLDivElement>(null);
    const mapRef = useRef<any>(null);

    useEffect(() => {
        if (!mapContainerRef.current || !area || !area.polygon || area.polygon.length < 2) return;

        // Initialize map only once
        if (!mapRef.current) {
            mapRef.current = L.map(mapContainerRef.current, {
                dragging: false,
                zoomControl: false,
                scrollWheelZoom: false,
                doubleClickZoom: false,
                boxZoom: false,
                keyboard: false,
                tap: false,
                touchZoom: false,
            });

            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            }).addTo(mapRef.current);
        }

        const map = mapRef.current;
        
        // Clear previous polygons if any
        map.eachLayer((layer: any) => {
            if (layer instanceof L.Polygon || layer instanceof L.Rectangle) {
                map.removeLayer(layer);
            }
        });

        const bounds = L.latLngBounds(area.polygon);
        L.rectangle(bounds, { color: "#3B82F6", weight: 3, fillOpacity: 0.1 }).addTo(map);
        
        map.fitBounds(bounds, { padding: [50, 50] });

        // Ensure map resizes correctly if container was hidden/resized
        setTimeout(() => map.invalidateSize(), 100);

    }, [area]);

    return (
        <div ref={mapContainerRef} className="w-full h-64 bg-gray-200 rounded-lg mt-4 z-0" />
    );
};


// Helper component for synced maps
interface AnalysisMapViewerProps {
    mapId: string;
    imageUrl: string;
    bounds: any; // L.LatLngBoundsExpression
    onViewChange: (center: any, zoom: number) => void;
    view?: { center: any; zoom: number };
}

const AnalysisMapViewer: React.FC<AnalysisMapViewerProps> = ({ mapId, imageUrl, bounds, onViewChange, view }) => {
    const mapContainerRef = useRef<HTMLDivElement>(null);
    const mapRef = useRef<any>(null);
    const layerRef = useRef<any>(null);
    const isSyncedMove = useRef(false);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (mapContainerRef.current && !mapRef.current) {
            const map = L.map(mapContainerRef.current, {
                zoomControl: true,
                attributionControl: false,
                zIndex: 1,
            }).fitBounds(bounds, { padding: [10, 10] });
            mapRef.current = map;

            L.tileLayer('https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png', {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            }).addTo(map);

            // Load GeoTIFF
            setLoading(true);
            loadGeoTIFF(imageUrl, map, layerRef, 0.8, bounds)
                .then(() => {
                    setLoading(false);
                    setError(null);
                })
                .catch(err => {
                    console.error('Error loading GeoTIFF:', err);
                    setError('Failed to load image');
                    setLoading(false);
                });

            map.on('moveend zoomend', () => {
                if (isSyncedMove.current) {
                    isSyncedMove.current = false;
                    return;
                }
                onViewChange(map.getCenter(), map.getZoom());
            });
        }
        
        setTimeout(() => mapRef.current?.invalidateSize(), 100);

    }, [bounds, imageUrl, onViewChange]);

    useEffect(() => {
        if (mapRef.current && view) {
            const currentCenter = mapRef.current.getCenter();
            const currentZoom = mapRef.current.getZoom();
            
            const centerChanged = Math.abs(currentCenter.lat - view.center.lat) > 1e-9 || Math.abs(currentCenter.lng - view.center.lng) > 1e-9;
            const zoomChanged = currentZoom !== view.zoom;

            if (centerChanged || zoomChanged) {
                isSyncedMove.current = true; // Set flag before programmatic move
                mapRef.current.setView(view.center, view.zoom, { animate: false });
            }
        }
    }, [view]);

    return (
        <div className="relative w-full h-full">
            <div ref={mapContainerRef} className="w-full h-full object-cover rounded-lg bg-gray-200" />
            {loading && (
                <div className="absolute inset-0 flex items-center justify-center bg-gray-100 bg-opacity-75 rounded-lg">
                    <Loader2Icon className="h-8 w-8 animate-spin text-blue-500" />
                </div>
            )}
            {error && (
                <div className="absolute inset-0 flex items-center justify-center bg-red-50 bg-opacity-75 rounded-lg">
                    <p className="text-red-600 text-sm">{error}</p>
                </div>
            )}
        </div>
    );
};


// Helper component for layered change detection map
interface ChangeDetectionMapViewerProps {
    mapId: string;
    currentImageUrl: string;
    changeImageUrl: string | null;
    bounds: any; // L.LatLngBoundsExpression
    onViewChange: (center: any, zoom: number) => void;
    view?: { center: any; zoom: number };
}

const ChangeDetectionMapViewer: React.FC<ChangeDetectionMapViewerProps> = ({ mapId, currentImageUrl, changeImageUrl, bounds, onViewChange, view }) => {
    const mapContainerRef = useRef<HTMLDivElement>(null);
    const mapRef = useRef<any>(null);
    const layersRef = useRef<any>({});
    const isSyncedMove = useRef(false);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        if (mapContainerRef.current && !mapRef.current) {
            const map = L.map(mapContainerRef.current, {
                zoomControl: true,
                attributionControl: false,
                zIndex: 1,
            }).fitBounds(bounds, { padding: [10, 10] });
            mapRef.current = map;

            const baseLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png', {
                attribution: '&copy; OpenStreetMap'
            }).addTo(map);

            const satelliteLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
                attribution: 'Esri'
            });

            const baseMaps = {
                "Street": baseLayer,
                "Satellite": satelliteLayer,
            };

            // Load GeoTIFFs
            setLoading(true);
            
            const loadLayers = async () => {
                const overlays: { [key: string]: any } = {};
                
                // Load current image
                const currentLayer = await loadGeoTIFF(currentImageUrl, map, null, 0.8, bounds);
                layersRef.current.current = currentLayer;
                overlays['Current Imagery'] = currentLayer;
                
                // Load change overlay if exists
                if (changeImageUrl) {
                    const changeLayer = await loadGeoTIFF(changeImageUrl, map, null, 0.7, bounds);
                    layersRef.current.change = changeLayer;
                    overlays['Change Overlay'] = changeLayer;
                }
                
                // Add layer control
                L.control.layers(baseMaps, overlays, { position: 'topright' }).addTo(map);
                setLoading(false);
            };
            
            loadLayers().catch(err => {
                console.error('Error loading GeoTIFFs:', err);
                setLoading(false);
            });

            map.on('moveend zoomend', () => {
                if (isSyncedMove.current) {
                    isSyncedMove.current = false;
                    return;
                }
                onViewChange(map.getCenter(), map.getZoom());
            });
        }
        
        setTimeout(() => mapRef.current?.invalidateSize(), 100);

    }, [bounds, currentImageUrl, changeImageUrl, onViewChange]);

    useEffect(() => {
        if (mapRef.current && view) {
            const currentCenter = mapRef.current.getCenter();
            const currentZoom = mapRef.current.getZoom();
            
            const centerChanged = Math.abs(currentCenter.lat - view.center.lat) > 1e-9 || Math.abs(currentCenter.lng - view.center.lng) > 1e-9;
            const zoomChanged = currentZoom !== view.zoom;

            if (centerChanged || zoomChanged) {
                isSyncedMove.current = true;
                mapRef.current.setView(view.center, view.zoom, { animate: false });
            }
        }
    }, [view]);

    return (
        <div className="relative w-full h-full">
            <div ref={mapContainerRef} id={mapId} className="w-full h-full object-cover rounded-lg bg-gray-200" />
            {loading && (
                <div className="absolute inset-0 flex items-center justify-center bg-gray-100 bg-opacity-75 rounded-lg">
                    <Loader2Icon className="h-8 w-8 animate-spin text-blue-500" />
                </div>
            )}
        </div>
    );
};


const ComparisonViewer: React.FC<{ result: AnalysisResult; area: MonitoringArea }> = ({ result, area }) => {
    // Check if analysis is complete and has image URLs
    const isComplete = result.processing_status === 'completed';
    const hasImageUrls = result.image_urls;
    
    // If analysis failed or is in progress, show status message
    if (!isComplete || !hasImageUrls) {
        return (
            <Card className="p-10 text-center">
                <h3 className="text-lg font-semibold">
                    {result.processing_status === 'failed' ? 'Analysis Failed' : 'Analysis In Progress'}
                </h3>
                <p className="mt-2 text-gray-500">
                    {result.error_message || 'Analysis is still being processed. Please check back later.'}
                </p>
                <p className="mt-1 text-sm text-gray-400">
                    Status: {result.processing_status}
                </p>
            </Card>
        );
    }

    // Use detailed metrics if available, otherwise fall back to change_percentage
    const loss = result.metrics?.loss_percentage ?? 0;
    const gain = result.metrics?.gain_percentage ?? 0;
    const stable = result.metrics ? (100 - loss - gain) : (100 - Math.abs(result.change_percentage ?? 0));

    const [mapView, setMapView] = useState<{ center: any; zoom: number } | undefined>();
    const bounds = React.useMemo(() => L.latLngBounds(area.polygon), [area.polygon]);

    const handleViewChange = useCallback((center: any, zoom: number) => {
        setMapView({ center, zoom });
    }, []);

    // Extract image URLs from Sentinel-2 analysis
    const baselineUrl = result.image_urls.baseline_image;
    const currentUrl = result.image_urls.current_image;
    const changeUrl = result.image_urls.difference_image;

    return (
        <Card>
            <h3 className="text-xl font-bold mb-4">Latest Analysis Comparison</h3>
            <p className="text-sm text-gray-500 mb-6">Completed on {new Date(result.timestamp).toLocaleString()}</p>
            
            <div className="space-y-8">
                {/* Baseline and Current Map Row */}
                {baselineUrl && currentUrl && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 h-[550px]">
                        <div className="flex flex-col">
                            <div className="mb-2 text-center">
                                <h4 className="font-semibold text-gray-700">Baseline</h4>
                                {result.metrics && (
                                    <div className="text-xs text-gray-500 mt-1">
                                        <span>{result.metrics.baseline_date}</span>
                                        <span className="mx-2">•</span>
                                        <span>Cloud: {result.metrics.baseline_cloud_coverage?.toFixed(1)}%</span>
                                    </div>
                                )}
                            </div>
                            <AnalysisMapViewer
                                mapId={`map-baseline-${result.result_id}`}
                                imageUrl={baselineUrl}
                                bounds={bounds}
                                onViewChange={handleViewChange}
                                view={mapView}
                            />
                        </div>
                        <div className="flex flex-col">
                            <div className="mb-2 text-center">
                                <h4 className="font-semibold text-gray-700">Current</h4>
                                {result.metrics && (
                                    <div className="text-xs text-gray-500 mt-1">
                                        <span>{result.metrics.current_date}</span>
                                        <span className="mx-2">•</span>
                                        <span>Cloud: {result.metrics.current_cloud_coverage?.toFixed(1)}%</span>
                                    </div>
                                )}
                            </div>
                            <AnalysisMapViewer
                                mapId={`map-current-${result.result_id}`}
                                imageUrl={currentUrl}
                                bounds={bounds}
                                onViewChange={handleViewChange}
                                view={mapView}
                            />
                        </div>
                    </div>
                )}

                {/* Change Detection Map Row */}
                {currentUrl && (
                    <div className="pt-4 flex flex-col h-[550px]">
                        <div className="mb-3">
                            <h4 className="font-semibold text-gray-700 text-center mb-2">Change Detection (Layered)</h4>
                            <div className="flex justify-center items-center gap-6 text-sm">
                                <div className="flex items-center gap-2">
                                    <div className="w-4 h-4 bg-red-500 rounded"></div>
                                    <span className="text-gray-600">{area.type === 'forest' ? 'Forest Loss' : 'Water Loss'}</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <div className="w-4 h-4 bg-green-500 rounded"></div>
                                    <span className="text-gray-600">Stable</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <div className="w-4 h-4 bg-blue-500 rounded"></div>
                                    <span className="text-gray-600">{area.type === 'forest' ? 'Forest Gain' : 'Water Gain'}</span>
                                </div>
                            </div>
                        </div>
                        <ChangeDetectionMapViewer
                            mapId={`map-change-${result.result_id}`}
                            currentImageUrl={currentUrl}
                            changeImageUrl={changeUrl || null}
                            bounds={bounds}
                            onViewChange={handleViewChange}
                            view={mapView}
                        />
                    </div>
                )}
            </div>

            <div className="mt-8 border-t pt-6">
                 <h4 className="font-bold text-lg mb-4">Detailed Statistics</h4>
                 <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-center">
                     <div className="p-4 bg-red-50 rounded-lg">
                         <p className="text-sm text-red-700">Loss</p>
                         <p className="text-2xl font-bold text-red-600">{loss.toFixed(2)}%</p>
                         {result.metrics && (
                             <p className="text-xs text-red-600 mt-2">{result.metrics.loss_hectares.toFixed(2)} ha</p>
                         )}
                     </div>
                     <div className="p-4 bg-green-50 rounded-lg">
                         <p className="text-sm text-green-700">Gain</p>
                         <p className="text-2xl font-bold text-green-600">{gain.toFixed(2)}%</p>
                         {result.metrics && (
                             <p className="text-xs text-green-600 mt-2">{result.metrics.gain_hectares.toFixed(2)} ha</p>
                         )}
                     </div>
                      <div className="p-4 bg-gray-100 rounded-lg">
                         <p className="text-sm text-gray-700">Stable</p>
                         <p className="text-2xl font-bold text-gray-600">{stable.toFixed(2)}%</p>
                         {result.metrics && (
                             <p className="text-xs text-gray-600 mt-2">{result.metrics.stable_hectares.toFixed(2)} ha</p>
                         )}
                     </div>
                 </div>
                 
                 {/* Additional metrics info */}
                 {result.metrics && (
                     <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
                         <p className="text-sm text-blue-900 font-semibold mb-2">Analysis Details</p>
                         <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm text-blue-800">
                             <div>
                                 <p className="text-xs text-blue-700">Total Area</p>
                                 <p className="font-semibold">{result.metrics.total_hectares.toFixed(2)} ha</p>
                             </div>
                             <div>
                                 <p className="text-xs text-blue-700">Valid Pixels</p>
                                 <p className="font-semibold">{result.metrics.valid_pixels_percentage.toFixed(1)}%</p>
                             </div>
                             <div>
                                 <p className="text-xs text-blue-700">Net Change</p>
                                 <p className={`font-semibold ${result.metrics.net_change_percentage > 0 ? 'text-green-600' : result.metrics.net_change_percentage < 0 ? 'text-red-600' : 'text-gray-600'}`}>
                                     {result.metrics.net_change_percentage > 0 ? '+' : ''}{result.metrics.net_change_percentage.toFixed(2)}%
                                 </p>
                             </div>
                             <div>
                                 <p className="text-xs text-blue-700">Cloud Coverage</p>
                                 <p className="font-semibold">{Math.max(result.metrics.baseline_cloud_coverage, result.metrics.current_cloud_coverage).toFixed(1)}%</p>
                             </div>
                         </div>
                     </div>
                 )}
            </div>
        </Card>
    );
};

const AreaDetailsPage: React.FC = () => {
    const { areaId } = useParams<{ areaId: string }>();
    const navigate = useNavigate();
    const [area, setArea] = useState<MonitoringArea | null>(null);
    const [results, setResults] = useState<AnalysisResult[]>([]);
    const [analysisInProgress, setAnalysisInProgress] = useState(false);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [isTriggering, setIsTriggering] = useState(false);
    const [isEditModalOpen, setIsEditModalOpen] = useState(false);
    const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
    const [isDeleting, setIsDeleting] = useState(false);
    const resultsRef = useRef<AnalysisResult[]>([]);

    const fetchData = useCallback(async (isPolling = false) => {
        if (!areaId) return;
        try {
            // Only show loading spinner on initial load, not during polling
            if (!isPolling) {
                setLoading(true);
            }
            setError(null);
            
            const areaData = await api.getMonitoringArea(areaId);
            if (!areaData) {
                setError('Monitoring area not found.');
                setLoading(false);
                return;
            }
            
            const resultsData = await api.getAreaResults(areaId, 10, 0);
            
            // Check if any result is still in progress
            const hasInProgress = resultsData.results.some(
                (r: AnalysisResult) => r.processing_status === 'in_progress'
            );
            
            // Only update state if data has actually changed
            const latestResultId = resultsData.results[0]?.result_id;
            const currentLatestId = resultsRef.current[0]?.result_id;
            const latestStatus = resultsData.results[0]?.processing_status;
            const currentStatus = resultsRef.current[0]?.processing_status;
            
            const hasDataChanged = 
                latestResultId !== currentLatestId || 
                latestStatus !== currentStatus ||
                resultsData.results.length !== resultsRef.current.length;
            
            // Update state only if there are changes or it's the initial load
            if (!isPolling || hasDataChanged) {
                setArea(areaData);
                setResults(resultsData.results);
                resultsRef.current = resultsData.results;
                setAnalysisInProgress(hasInProgress || resultsData.analysis_in_progress);
            }
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Failed to fetch area details.';
            setError(errorMessage);
        } finally {
            if (!isPolling) {
                setLoading(false);
            }
        }
    }, [areaId]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    // Poll for updates when analysis is in progress
    useEffect(() => {
        if (!analysisInProgress) return;

        const pollInterval = setInterval(() => {
            fetchData(true); // Pass true to indicate this is a polling request
        }, 20000); // Poll every 20 seconds

        return () => clearInterval(pollInterval);
    }, [analysisInProgress, fetchData]);

    const handleTriggerAnalysis = async () => {
        if (!areaId || analysisInProgress) return;
        setIsTriggering(true);
        try {
            await api.triggerAnalysis(areaId);
            // Refresh data immediately to get the in_progress status
            await fetchData();
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Failed to trigger analysis.';
            alert(errorMessage);
        } finally {
            setIsTriggering(false);
        }
    };

    const handleSaveName = async (newName: string) => {
        if (!areaId || !area) return;

        const originalArea = area;
        setArea(prevArea => prevArea ? { ...prevArea, name: newName } : null);
        
        try {
            await api.updateMonitoringArea(areaId, newName);
        } catch (error) {
             setArea(originalArea);
            const errorMessage = error instanceof Error ? error.message : 'Failed to update area name.';
            alert(errorMessage);
        }
    };

    const handleDelete = async () => {
        if (!areaId) return;
        setIsDeleting(true);
        try {
            await api.deleteMonitoringArea(areaId);
            navigate('/');
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to delete area.';
            alert(errorMessage);
            setIsDeleting(false);
        }
    };


    if (loading) {
        return <div className="p-8"><Skeleton className="h-screen w-full" /></div>;
    }

    if (error) {
        return (
            <div className="flex flex-col items-center justify-center h-screen text-red-500">
                <AlertTriangleIcon className="h-16 w-16" />
                <p className="mt-4 text-xl">{error}</p>
                <Link to="/" className="mt-8">
                    <Button><ChevronLeftIcon className="h-4 w-4 mr-2" />Back to Dashboard</Button>
                </Link>
            </div>
        );
    }

    if (!area) return null;

    const latestResult = results[0];

    return (
        <>
            <div className="min-h-screen bg-gray-50">
                <header className="bg-white shadow-sm">
                    <div className="max-w-screen-2xl mx-auto py-4 px-4 sm:px-6 lg:px-8">
                        <div className="flex items-center justify-between">
                             <div className="flex items-center">
                                <Link to="/" className="text-gray-500 hover:text-gray-700 flex items-center">
                                    <ChevronLeftIcon className="h-5 w-5" />
                                    <span className="ml-1 font-medium">Dashboard</span>
                                </Link>
                                <span className="mx-3 text-gray-300 text-xl">/</span>
                                <h1 className="text-2xl font-bold text-gray-900">{area.name}</h1>
                            </div>
                            <div className="flex items-center space-x-3">
                                <Button variant="outline" onClick={() => setIsEditModalOpen(true)}>Edit</Button>
                                <Button variant="destructive" onClick={() => setIsDeleteModalOpen(true)}>Delete</Button>
                                <Button onClick={handleTriggerAnalysis} disabled={analysisInProgress || isTriggering}>
                                    {analysisInProgress || isTriggering ? (
                                        <><Loader2Icon className="h-4 w-4 mr-2 animate-spin" /> Analyzing...</>
                                    ) : (
                                        <><RefreshCwIcon className="h-4 w-4 mr-2" /> Trigger Analysis</>
                                    )}
                                </Button>
                            </div>
                        </div>
                    </div>
                </header>
                <main className="py-10">
                    <div className="max-w-screen-2xl mx-auto px-4 sm:px-6 lg:px-8 grid grid-cols-1 lg:grid-cols-3 gap-8">
                        {/* Left Column - Area Info */}
                        <div className="lg:col-span-1">
                            <Card>
                                <h2 className="text-xl font-bold mb-4">Area Information</h2>
                                <div className="space-y-3 text-sm text-gray-600">
                                    <div className="flex justify-between"><strong>Name:</strong> <span>{area.name}</span></div>
                                    <div className="flex justify-between items-center"><strong>Type:</strong> <Badge variant={area.type === 'forest' ? 'green' : 'blue'}>{area.type === 'forest' ? <ForestIcon className="h-4 w-4 mr-1.5"/> : <WaterIcon className="h-4 w-4 mr-1.5" />}{area.type}</Badge></div>
                                    <div className="flex justify-between"><strong>Status:</strong> <span>{area.status}</span></div>
                                    <div className="flex justify-between"><strong>Created:</strong> <span>{new Date(area.created_at).toLocaleDateString()}</span></div>
                                    <div className="flex justify-between"><strong>Last Analysis:</strong> <span>{area.last_checked_at ? new Date(area.last_checked_at).toLocaleDateString() : 'N/A'}</span></div>
                                    <div className="flex justify-between"><strong>Total Analyses:</strong> <span>{area.total_analyses}</span></div>
                                </div>
                               <AreaDetailMap area={area} />
                            </Card>
                        </div>

                        {/* Right Column - Analysis Results */}
                        <div className="lg:col-span-2 space-y-8">
                            {analysisInProgress && (
                                 <Card className="text-center">
                                    <Loader2Icon className="h-8 w-8 mx-auto text-blue-500 animate-spin" />
                                    <h3 className="mt-4 text-lg font-semibold">Analysis In Progress...</h3>
                                    <p className="mt-1 text-gray-500">This may take a few minutes. The page will update automatically when complete.</p>
                                </Card>
                            )}
                            {latestResult && area ? (
                                <>
                                    <ComparisonViewer result={latestResult} area={area} />
                                    <ReportViewer resultId={latestResult.result_id} areaName={area.name} />
                                </>
                            ) : !analysisInProgress && (
                                <Card className="p-10 text-center">
                                    <h3 className="text-lg font-semibold">No analysis results yet</h3>
                                    <p className="mt-2 text-gray-500">Trigger an analysis to get started.</p>
                                </Card>
                            )}

                            {/* Analysis History */}
                            <Card>
                                <h3 className="text-xl font-bold mb-4">Analysis History</h3>
                                {results.length > 0 ? (
                                    <ul className="divide-y divide-gray-200">
                                        {results.map(r => (
                                            <li key={r.result_id} className="py-4 flex items-center justify-between">
                                                <div>
                                                    <p className="font-semibold">{new Date(r.timestamp).toLocaleString()}</p>
                                                    <p className={`text-sm ${r.change_percentage && r.change_percentage > 0 ? 'text-green-600' : (r.change_percentage && r.change_percentage < 0 ? 'text-red-600' : 'text-gray-500')}`}>
                                                        Change: {r.change_percentage !== null ? `${r.change_percentage.toFixed(1)}%` : 'N/A'}
                                                    </p>
                                                </div>
                                                <div className='flex items-center space-x-4'>
                                                    <Badge className={r.processing_status === 'completed' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}>{r.processing_status}</Badge>
                                                    <Button variant="outline" size="sm">
                                                        <DownloadIcon className="h-4 w-4 mr-2" />
                                                        Download
                                                    </Button>
                                                </div>
                                            </li>
                                        ))}
                                    </ul>
                                ) : (
                                    <p className="text-gray-500 text-center py-4">No analysis history available.</p>
                                )}
                            </Card>
                        </div>
                    </div>
                </main>
            </div>
            {area && <EditAreaModal 
                isOpen={isEditModalOpen}
                onClose={() => setIsEditModalOpen(false)}
                onSave={handleSaveName}
                currentName={area.name}
            />}
            {area && <DeleteConfirmationModal 
                isOpen={isDeleteModalOpen}
                onClose={() => setIsDeleteModalOpen(false)}
                onConfirm={handleDelete}
                areaName={area.name}
                isDeleting={isDeleting}
            />}
        </>
    );
};

export default AreaDetailsPage;