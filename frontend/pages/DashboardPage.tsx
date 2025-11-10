import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import { MonitoringArea } from '../types';
import * as api from '../services/apiService';
import Header from '../components/common/Header';
import { Button, Card, Badge, Skeleton } from '../components/common/ui';
import { PlusIcon, MapPinIcon, ClockIcon, AlertTriangleIcon, SearchIcon, ForestIcon, WaterIcon } from '../components/common/Icons';
import NewAreaModal from '../components/NewAreaModal';

declare const L: any; // Use Leaflet global

// Custom Leaflet Icons
const createColorIcon = (color: string) => {
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="32" height="32" fill="${color}" stroke="white" stroke-width="1.5"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/></svg>`;
    return new (L as any).Icon({
        iconUrl: `data:image/svg+xml;base64,${btoa(svg)}`,
        iconSize: [32, 32],
        iconAnchor: [16, 32],
        popupAnchor: [0, -32],
    });
};

const forestIcon = createColorIcon('#10B981'); // Green
const waterIcon = createColorIcon('#3B82F6'); // Blue

const DashboardMap: React.FC<{ areas: MonitoringArea[] }> = ({ areas }) => {
    const mapContainerRef = useRef<HTMLDivElement>(null);
    const mapRef = useRef<any>(null); // To hold Leaflet map instance

    useEffect(() => {
        if (mapContainerRef.current && !mapRef.current) {
            mapRef.current = L.map(mapContainerRef.current, {
                scrollWheelZoom: false
            }).setView([20, 0], 2); // Default view

            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            }).addTo(mapRef.current);
        }
    }, []);

    useEffect(() => {
        const map = mapRef.current;
        if (!map || !areas) return;

        // Clear existing markers
        map.eachLayer((layer: any) => {
            if (layer instanceof L.Marker) {
                map.removeLayer(layer);
            }
        });
        
        const activeAreas = areas.filter(a => 
            a && 
            a.status === 'active' && 
            a.polygon && 
            a.polygon.length >= 4 &&
            a.polygon[0] &&
            a.polygon[2]
        );

        if (activeAreas.length === 0) {
             map.setView([20, 0], 2);
             return;
        }

        const markers = activeAreas.map(area => {
            // Calculate center of the rectangular polygon
            const center: any = [
                (area.polygon[0].lat + area.polygon[2].lat) / 2, 
                (area.polygon[0].lng + area.polygon[2].lng) / 2
            ];
            const icon = area.type === 'forest' ? forestIcon : waterIcon;
            
            const marker = L.marker(center, { icon }).addTo(map);
            marker.bindPopup(`
                <div class="font-sans">
                    <h4 class="font-bold text-md">${area.name}</h4>
                    <p class="text-sm text-gray-600">Status: <span class="font-medium">${area.status}</span></p>
                    <a href="#/areas/${area.area_id}" class="text-blue-600 hover:underline text-sm font-semibold mt-1 inline-block">View Details &rarr;</a>
                </div>
            `);
            return marker;
        });

        if (markers.length > 0) {
            const group = new L.featureGroup(markers);
            map.fitBounds(group.getBounds().pad(0.5));
        }

    }, [areas]);

    return (
        <div ref={mapContainerRef} className="w-full h-[400px] md:h-[500px] bg-gray-200 rounded-lg z-0" />
    );
};

const AreaCard: React.FC<{ area: MonitoringArea }> = ({ area }) => {
    const statusConfig = {
        active: { color: 'bg-green-100 text-green-800', text: 'Active' },
        pending: { color: 'bg-yellow-100 text-yellow-800', text: 'Pending' },
        error: { color: 'bg-red-100 text-red-800', text: 'Error' },
        paused: { color: 'bg-gray-100 text-gray-800', text: 'Paused' },
        deleted: { color: 'bg-gray-100 text-gray-800', text: 'Deleted' },
    };

    const change = area.latest_change_percentage;
    const changeColor = change == null ? 'text-gray-500' : change > 0 ? 'text-green-600' : change < 0 ? 'text-red-600' : 'text-gray-500';
    const changeText = change == null ? 'N/A' : `${change > 0 ? '+' : ''}${change.toFixed(1)}%`;

    return (
        <Card className="flex flex-col justify-between hover:shadow-lg hover:-translate-y-1 transition-all duration-300">
            <div>
                <div className="flex justify-between items-start mb-2">
                    <Badge variant={area.type === 'forest' ? 'green' : 'blue'}>
                       {area.type === 'forest' ? <ForestIcon className="h-4 w-4 mr-1.5"/> : <WaterIcon className="h-4 w-4 mr-1.5" />}
                        {area.type.charAt(0).toUpperCase() + area.type.slice(1)}
                    </Badge>
                     <Badge className={`${statusConfig[area.status].color}`}>{statusConfig[area.status].text}</Badge>
                </div>
                <h3 className="text-xl font-bold text-gray-800 truncate">{area.name}</h3>
                <div className="mt-4 space-y-2 text-sm text-gray-500">
                    <div className="flex items-center">
                        <ClockIcon className="h-4 w-4 mr-2" />
                        <span>Last Analysis: {area.last_checked_at ? new Date(area.last_checked_at).toLocaleDateString() : 'N/A'}</span>
                    </div>
                    <div className="flex items-center">
                        <span className={`font-semibold mr-2 ${changeColor}`}>Change:</span>
                        <span className={`font-bold text-lg ${changeColor}`}>{changeText}</span>
                    </div>
                </div>
            </div>
            <Link to={`/areas/${area.area_id}`} className="mt-6">
                <Button variant="outline" className="w-full">View Details</Button>
            </Link>
        </Card>
    );
};

const DashboardPage: React.FC = () => {
    const [areas, setAreas] = useState<MonitoringArea[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const areasRef = useRef<MonitoringArea[]>([]);

    const fetchAreas = useCallback(async (isPolling = false) => {
        try {
            // Only show loading spinner on initial load, not during background refresh
            if (!isPolling) {
                setLoading(true);
            }
            setError(null);
            
            const data = await api.getMonitoringAreas();
            
            // Only update state if data has actually changed
            if (!isPolling || JSON.stringify(data) !== JSON.stringify(areasRef.current)) {
                setAreas(data);
                areasRef.current = data;
            }
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Failed to fetch monitoring areas.';
            setError(errorMessage);
        } finally {
            if (!isPolling) {
                setLoading(false);
            }
        }
    }, []);

    useEffect(() => {
        fetchAreas();
    }, [fetchAreas]);

    const handleNewAreaSuccess = () => {
        setIsModalOpen(false);
        fetchAreas();
    };

    return (
        <>
            <Header onNewAreaClick={() => setIsModalOpen(true)} />
            <main>
                {/* Hero Section */}
                <div className="bg-white">
                    <div className="max-w-7xl mx-auto py-16 px-4 sm:px-6 lg:px-8 text-center">
                        <h1 className="text-4xl font-extrabold tracking-tight text-gray-900 sm:text-5xl md:text-6xl">
                            Monitor Forest & Water Changes
                        </h1>
                        <p className="mt-6 max-w-2xl mx-auto text-xl text-gray-500">
                            Powered by satellite imagery & AI, GeoWatch provides actionable insights into environmental changes in your areas of interest.
                        </p>
                        <div className="mt-8">
                            <DashboardMap areas={areas} />
                        </div>
                    </div>
                </div>

                {/* Monitoring Areas Grid */}
                <div className="py-12 bg-gray-50">
                    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                        <h2 className="text-3xl font-bold text-gray-900 mb-8">Your Monitoring Areas</h2>
                        {loading ? (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                                {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-64" />)}
                            </div>
                        ) : error ? (
                            <div className="text-center py-12 text-red-500">
                                <AlertTriangleIcon className="mx-auto h-12 w-12" />
                                <p className="mt-4">{error}</p>
                            </div>
                        ) : areas.length > 0 ? (
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
                                {areas.map(area => <AreaCard key={area.area_id} area={area} />)}
                            </div>
                        ) : (
                            <div className="text-center py-16 border-2 border-dashed border-gray-300 rounded-lg">
                                <SearchIcon className="mx-auto h-12 w-12 text-gray-400" />
                                <h3 className="mt-2 text-lg font-medium text-gray-900">No monitoring areas yet</h3>
                                <p className="mt-1 text-sm text-gray-500">Create your first monitoring area to get started.</p>
                                <div className="mt-6">
                                    <Button onClick={() => setIsModalOpen(true)}>
                                        <PlusIcon className="h-4 w-4 mr-2" />
                                        Create First Area
                                    </Button>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </main>
            {isModalOpen && <NewAreaModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} onSuccess={handleNewAreaSuccess} />}
        </>
    );
};

export default DashboardPage;