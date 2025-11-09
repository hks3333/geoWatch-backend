import React, { useState, useEffect } from 'react';
import { Modal, Button, Input } from './common/ui';
import { Loader2Icon } from './common/Icons';

interface EditAreaModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSave: (newName: string) => Promise<void>;
    currentName: string;
}

const EditAreaModal: React.FC<EditAreaModalProps> = ({ isOpen, onClose, onSave, currentName }) => {
    const [name, setName] = useState(currentName);
    const [isSaving, setIsSaving] = useState(false);

    useEffect(() => {
        if (isOpen) {
            setName(currentName);
        }
    }, [isOpen, currentName]);

    const handleSave = async () => {
        if (!name.trim() || name.trim() === currentName) {
            onClose();
            return;
        }
        setIsSaving(true);
        try {
            await onSave(name.trim());
        } catch (error) {
            console.error("Failed to save new name", error);
        } finally {
            setIsSaving(false);
            onClose();
        }
    };

    if (!isOpen) return null;

    return (
        <Modal isOpen={isOpen} onClose={onClose} title="Edit Area Name">
            <div className="p-6">
                <div className="space-y-4">
                    <label htmlFor="area-name-edit" className="block text-sm font-medium text-gray-700">Area Name</label>
                    <Input
                        id="area-name-edit"
                        value={name}
                        onChange={(e) => setName(e.target.value)}
                        placeholder="Enter a new name"
                        className="mt-1"
                    />
                </div>
                <div className="mt-8 flex justify-end space-x-3">
                    <Button variant="ghost" onClick={onClose}>Cancel</Button>
                    <Button onClick={handleSave} disabled={isSaving || !name.trim() || name.trim() === currentName}>
                        {isSaving && <Loader2Icon className="h-4 w-4 mr-2 animate-spin" />}
                        Save Changes
                    </Button>
                </div>
            </div>
        </Modal>
    );
};

export default EditAreaModal;
