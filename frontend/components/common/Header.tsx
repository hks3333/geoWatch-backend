
import React from 'react';
import { Link } from 'react-router-dom';
import { PlusIcon, UserIcon, SatelliteIcon } from './Icons';
import { Button } from './ui';

interface HeaderProps {
    onNewAreaClick: () => void;
}

const Header: React.FC<HeaderProps> = ({ onNewAreaClick }) => {
    return (
        <header className="bg-white/80 backdrop-blur-lg border-b border-gray-200 sticky top-0 z-40">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex justify-between items-center h-16">
                    <div className="flex items-center space-x-2">
                        <SatelliteIcon className="h-8 w-8 text-blue-600" />
                        <Link to="/" className="text-2xl font-bold text-gray-800 tracking-tight">
                            GeoWatch
                        </Link>
                    </div>
                    <div className="flex items-center space-x-4">
                        <Button onClick={onNewAreaClick}>
                            <PlusIcon className="h-4 w-4 mr-2" />
                            New Monitoring Area
                        </Button>
                        <button className="p-2 rounded-full hover:bg-gray-100">
                            <UserIcon className="h-6 w-6 text-gray-500" />
                        </button>
                    </div>
                </div>
            </div>
        </header>
    );
};

export default Header;
