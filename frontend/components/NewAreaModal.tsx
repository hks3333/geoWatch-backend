import React, { useState, useEffect, useRef, useCallback } from 'react';
import { LatLng, MonitoringType, NewMonitoringArea } from '../types';
import * as api from '../services/apiService';
import { Modal, Button, Input, RadioGroup, RadioGroupItem } from './common/ui';
import { MapPinIcon, Loader2Icon, SearchIcon, SquareDashedIcon } from './common/Icons';

declare const L: any; // Use Leaflet global

// Helper to calculate area
const calculateArea = (bounds: any): number => {
    const sw = bounds.getSouthWest();
    const ne = bounds.getNorthEast();
    // A simplified calculation for area. For production, a more accurate geodesic calculation would be better.
    const west = L.latLng(sw.lat, sw.lng);
    const east = L.latLng(sw.lat, ne.lng);
    const north = L.latLng(ne.lat, sw.lng);
    const width = west.distanceTo(east) / 1000; // in km
    const height = west.distanceTo(north) / 1000; // in km
    return width * height;
};

interface NewAreaModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSuccess: () => void;
}

const NewAreaModal: React.FC<NewAreaModalProps> = ({ isOpen, onClose, onSuccess }) => {
    const [step, setStep] = useState(1);
    const [name, setName] = useState('');
    const [type, setType] = useState<MonitoringType | ''>('');
    const [bounds, setBounds] = useState<{ southWest: LatLng, northEast: LatLng } | null>(null);
    const [areaSize, setAreaSize] = useState(0);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);
    
    // Search state
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState<any[]>([]);
    const [isSearching, setIsSearching] = useState(false);
    const [mapCenter, setMapCenter] = useState<[number, number] | null>(null);
    const searchTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const selectionMadeRef = useRef(false);

    // Map state
    const mapContainerRef = useRef<HTMLDivElement>(null);
    const leafletMap = useRef<any>(null);
    const rectangleRef = useRef<any>(null);
    const [isDrawing, setIsDrawing] = useState(false);

    const isStep1Valid = name.length >= 3 && name.length <= 100 && type !== '';
    const isStep2Valid = bounds !== null && areaSize >= 1 && areaSize <= 500;

    // Map Initialization
    useEffect(() => {
        if (step === 2 && mapContainerRef.current && !leafletMap.current) {
            const map = L.map(mapContainerRef.current);
            leafletMap.current = map;

            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            }).addTo(map);

            navigator.geolocation.getCurrentPosition(
                (position) => map.setView([position.coords.latitude, position.coords.longitude], 10),
                () => map.setView([20, 0], 2)
            );
        }
        
        // Always invalidate size when step 2 is shown to prevent grey map bug
        if (step === 2 && leafletMap.current) {
            setTimeout(() => leafletMap.current.invalidateSize(), 150);
        }
    }, [step]);
    
    // Center map on search
    useEffect(() => {
        if (leafletMap.current && mapCenter) {
            leafletMap.current.setView(mapCenter, 12);
        }
    }, [mapCenter]);

    // Drawing Logic
    useEffect(() => {
        const map = leafletMap.current;
        if (!map) return;

        // Invalidate size when toggling draw mode as well for extra safety
        setTimeout(() => map.invalidateSize(), 0);

        document.body.classList.toggle('drawing-mode', isDrawing);
        map.getContainer().style.cursor = isDrawing ? 'crosshair' : 'grab';

        if (!isDrawing) {
            map.dragging.enable();
            return;
        }

        map.dragging.disable();
        
        const handleDrawStart = (startEvent: any) => {
            const startLatLng = startEvent.latlng;
            
            if (rectangleRef.current) {
                map.removeLayer(rectangleRef.current);
            }

            const handleDrawMove = (moveEvent: MouseEvent) => {
                const currentLatLng = map.mouseEventToLatLng(moveEvent);

                if (rectangleRef.current) {
                    map.removeLayer(rectangleRef.current);
                }
                const bounds = L.latLngBounds(startLatLng, currentLatLng);
                rectangleRef.current = L.rectangle(bounds, { color: "#3B82F6", weight: 2, fillOpacity: 0.1 }).addTo(map);
            };

            const handleDrawEnd = () => {
                document.removeEventListener('mousemove', handleDrawMove);
                document.removeEventListener('mouseup', handleDrawEnd);
                
                if (rectangleRef.current) {
                    const finalBounds = rectangleRef.current.getBounds();
                    const area = calculateArea(finalBounds);
                    const sw = finalBounds.getSouthWest();
                    const ne = finalBounds.getNorthEast();
                    setBounds({ southWest: { lat: sw.lat, lng: sw.lng }, northEast: { lat: ne.lat, lng: ne.lng } });
                    setAreaSize(area);
                }
                setIsDrawing(false); // This triggers this effect to clean up
            };

            // Use document to capture mouseup anywhere on the page
            document.addEventListener('mousemove', handleDrawMove);
            document.addEventListener('mouseup', handleDrawEnd);
        };

        map.on('mousedown', handleDrawStart);

        return () => {
            map.off('mousedown', handleDrawStart);
            map.dragging.enable();
            document.body.classList.remove('drawing-mode');
        };

    }, [isDrawing]);


    // Debounced search effect
    useEffect(() => {
        if (selectionMadeRef.current) {
            selectionMadeRef.current = false;
            return;
        }

        if (searchTimeoutRef.current) {
            clearTimeout(searchTimeoutRef.current);
        }

        if (searchQuery.length < 3) {
            setSearchResults([]);
            return;
        }

        searchTimeoutRef.current = setTimeout(async () => {
            setIsSearching(true);
            try {
                const response = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(searchQuery)}&limit=5`);
                const data = await response.json();
                setSearchResults(data);
            } catch (error) {
                console.error("Failed to fetch search results:", error);
                setSearchResults([]);
            } finally {
                setIsSearching(false);
            }
        }, 500);

        return () => {
            if (searchTimeoutRef.current) {
                clearTimeout(searchTimeoutRef.current);
            }
        };
    }, [searchQuery]);


    const handleNext = () => {
        if (isStep1Valid) setStep(2);
    };

    const handleBack = () => {
        setStep(1);
    };
    
    const handleSearchResultClick = (result: any) => {
        selectionMadeRef.current = true;
        setMapCenter([parseFloat(result.lat), parseFloat(result.lon)]);
        setSearchQuery(result.display_name);
        setSearchResults([]);
    };

    const handleSubmit = async () => {
        if (!isStep2Valid || !type || !bounds) return;
        setIsSubmitting(true);
        setError(null);
        try {
            const newArea: NewMonitoringArea = {
                name,
                type,
                rectangle_bounds: bounds,
            };
            await api.createMonitoringArea(newArea);
            onSuccess();
        } catch (err) {
            const errorMessage = err instanceof Error ? err.message : 'Failed to create monitoring area. Please try again.';
            setError(errorMessage);
        } finally {
            setIsSubmitting(false);
        }
    };

    const resetState = () => {
        setStep(1);
        setName('');
        setType('');
        setBounds(null);
        setAreaSize(0);
        setError(null);
        setIsSubmitting(false);
        setIsDrawing(false);
        setSearchQuery('');
        setSearchResults([]);
        setMapCenter(null);
    }
    
    const handleClose = () => {
        resetState();
        onClose();
    }
    
    if (!isOpen) return null;

    return (
        <Modal isOpen={isOpen} onClose={handleClose} title="New Monitoring Area">
            <div className="p-6">
                <p className="text-sm text-gray-500 mb-4">Step {step} of 2: {step === 1 ? 'Basic Information' : 'Select Monitoring Area'}</p>
                {step === 1 && (
                    <div className="space-y-6">
                        <div>
                            <label htmlFor="area-name" className="block text-sm font-medium text-gray-700">Area Name</label>
                            <Input
                                id="area-name"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                placeholder="e.g., Redwood National Park"
                                className="mt-1"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-gray-700">Monitoring Type</label>
                            <RadioGroup value={type} onValueChange={(value) => setType(value as MonitoringType)} className="mt-2 grid grid-cols-2 gap-4">
                                <div>
                                    <RadioGroupItem value="forest" id="forest" className="sr-only" />
                                    <label htmlFor="forest" className={`flex flex-col items-center justify-center rounded-md border-2 p-4 text-sm font-medium hover:bg-gray-50 cursor-pointer ${type === 'forest' ? 'bg-green-50 border-green-300' : 'border-gray-200'}`}>Forest</label>
                                </div>
                                <div>
                                    <RadioGroupItem value="water" id="water" className="sr-only" />
                                    <label htmlFor="water" className={`flex flex-col items-center justify-center rounded-md border-2 p-4 text-sm font-medium hover:bg-gray-50 cursor-pointer ${type === 'water' ? 'bg-blue-50 border-blue-300' : 'border-gray-200'}`}>Water</label>
                                </div>
                            </RadioGroup>
                        </div>
                    </div>
                )}
                {step === 2 && (
                    <div className="space-y-4">
                         <div className="flex space-x-2 items-center">
                            <div className="relative flex-grow">
                                <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
                                <Input
                                    type="text"
                                    placeholder="Search for a location..."
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    className="pl-10"
                                />
                                {isSearching && <Loader2Icon className="absolute right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400 animate-spin" />}
                                {searchResults.length > 0 && (
                                    <div className="absolute z-[1001] w-full mt-1 bg-white border border-gray-200 rounded-md shadow-lg max-h-60 overflow-y-auto">
                                        {searchResults.map((result) => (
                                            <div
                                                key={result.place_id}
                                                onClick={() => handleSearchResultClick(result)}
                                                className="px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 cursor-pointer"
                                            >
                                                {result.display_name}
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                            <Button variant={isDrawing ? 'default' : 'outline'} onClick={() => setIsDrawing(!isDrawing)}>
                                <SquareDashedIcon className="h-4 w-4 mr-2" />
                                {isDrawing ? 'Cancel' : 'Draw Area'}
                            </Button>
                        </div>
                        <p className="text-sm text-gray-600 flex items-center">
                            <MapPinIcon className="h-4 w-4 mr-2" /> 
                            {isDrawing ? "Click and drag on the map to select an area." : "Explore the map or use the search."}
                        </p>
                         <div ref={mapContainerRef} className="w-full h-[400px] rounded-md bg-gray-200"></div>
                        <div className="p-3 bg-gray-100 rounded-md text-sm text-center">
                            <span className="font-medium text-gray-800">Area Size:</span>
                            <span className={`ml-2 font-bold ${!bounds ? 'text-gray-500' : (isStep2Valid ? 'text-green-600' : 'text-red-600')}`}>
                                {areaSize.toFixed(2)} sq km
                            </span>
                            {bounds && !isStep2Valid && (
                                <p className="text-red-600 text-xs mt-1">Area must be between 1 and 500 sq km.</p>
                            )}
                        </div>
                    </div>
                )}
                
                {error && <p className="mt-4 text-sm text-red-600 text-center">{error}</p>}

                <div className="mt-8 flex justify-end space-x-3">
                    <Button variant="ghost" onClick={handleClose}>Cancel</Button>
                    {step === 2 && <Button variant="outline" onClick={handleBack}>Back</Button>}
                    {step === 1 && <Button onClick={handleNext} disabled={!isStep1Valid}>Next</Button>}
                    {step === 2 && (
                        <Button onClick={handleSubmit} disabled={!isStep2Valid || isSubmitting}>
                            {isSubmitting ? <Loader2Icon className="h-4 w-4 mr-2 animate-spin"/> : null}
                            Create
                        </Button>
                    )}
                </div>
            </div>
        </Modal>
    );
};

export default NewAreaModal;