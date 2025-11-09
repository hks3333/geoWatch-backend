import React from 'react';
import { Modal, Button } from './common/ui';
import { AlertTriangleIcon, Loader2Icon } from './common/Icons';

interface DeleteConfirmationModalProps {
    isOpen: boolean;
    onClose: () => void;
    onConfirm: () => Promise<void>;
    areaName: string;
    isDeleting: boolean;
}

const DeleteConfirmationModal: React.FC<DeleteConfirmationModalProps> = ({ isOpen, onClose, onConfirm, areaName, isDeleting }) => {
    if (!isOpen) return null;

    return (
        <Modal isOpen={isOpen} onClose={onClose} title="Confirm Deletion">
            <div className="p-6">
                <div className="flex items-start">
                    <div className="mx-auto flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-full bg-red-100 sm:mx-0 sm:h-10 sm:w-10">
                        <AlertTriangleIcon className="h-6 w-6 text-red-600" aria-hidden="true" />
                    </div>
                    <div className="mt-3 text-center sm:mt-0 sm:ml-4 sm:text-left">
                        <h3 className="text-lg leading-6 font-medium text-gray-900">
                            Delete Monitoring Area
                        </h3>
                        <div className="mt-2">
                            <p className="text-sm text-gray-500">
                                Are you sure you want to delete <span className="font-bold">{areaName}</span>? This action cannot be undone.
                            </p>
                        </div>
                    </div>
                </div>
                 <div className="mt-8 flex justify-end space-x-3">
                    <Button variant="ghost" onClick={onClose} disabled={isDeleting}>Cancel</Button>
                    <Button variant="destructive" onClick={onConfirm} disabled={isDeleting}>
                        {isDeleting && <Loader2Icon className="h-4 w-4 mr-2 animate-spin" />}
                        Delete
                    </Button>
                </div>
            </div>
        </Modal>
    );
};

export default DeleteConfirmationModal;
