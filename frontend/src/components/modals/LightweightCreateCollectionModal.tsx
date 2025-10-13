import React, { useState, useRef } from 'react';
import { FolderIcon } from '@heroicons/react/24/outline';
import { useNotification } from '../../contexts/NotificationContext';
import apiClient from '../../services/apiClient';
import { Button, Input, Modal, FileUpload } from '../ui';
import type { UploadedFile as UIUploadedFile } from '../ui';

interface CreateCollectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCollectionCreated: (collection: any) => void;
}

interface FormData {
  name: string;
  visibility: 'private' | 'public';
}

const LightweightCreateCollectionModal: React.FC<CreateCollectionModalProps> = ({
  isOpen,
  onClose,
  onCollectionCreated,
}) => {
  const { addNotification } = useNotification();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<UIUploadedFile[]>([]);
  const submittingRef = useRef(false); // Prevent double-submission

  const [formData, setFormData] = useState<FormData>({
    name: '',
    visibility: 'private',
  });

  const resetForm = () => {
    setFormData({
      name: '',
      visibility: 'private',
    });
    setUploadedFiles([]);
  };

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const handleInputChange = (field: string, value: any) => {
    setFormData(prev => ({
      ...prev,
      [field]: value,
    }));
  };

  const validateForm = () => {
    return formData.name.trim().length > 0;
  };

  const handleSubmit = async () => {
    if (!validateForm()) return;

    // Prevent double-submission
    if (submittingRef.current) {
      return;
    }

    submittingRef.current = true;
    setIsSubmitting(true);

    try {
      let newCollection;

      // Use different endpoints based on whether files are present
      if (uploadedFiles.length > 0) {
        const files = uploadedFiles.map(f => f.file);
        newCollection = await apiClient.createCollectionWithFiles({
          name: formData.name,
          is_private: formData.visibility === 'private',
          files: files
        });
      } else {
        newCollection = await apiClient.createCollection({
          name: formData.name,
          description: `Collection with ${formData.visibility} visibility`,
          is_private: formData.visibility === 'private'
        });
      }

      onCollectionCreated(newCollection);
      addNotification('success', 'Collection Created', `"${formData.name}" has been created successfully${uploadedFiles.length > 0 ? ` with ${uploadedFiles.length} file(s)` : ''}.`);
      handleClose();
    } catch (error: any) {
      console.error('Error creating collection:', error);
      const errorMessage = error?.response?.data?.detail || error?.message || 'Failed to create collection. Please try again.';

      // Check if it's a duplicate name error
      if (errorMessage.includes('already exists')) {
        addNotification('error', 'Name Already Exists', `A collection named "${formData.name}" already exists. Please choose a different name.`);
      } else {
        addNotification('error', 'Creation Failed', errorMessage);
      }
    } finally {
      setIsSubmitting(false);
      submittingRef.current = false;
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Create New Collection"
      subtitle="Create a collection to organize your documents"
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={handleClose}>
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleSubmit}
            disabled={!validateForm() || isSubmitting}
            loading={isSubmitting}
            icon={<FolderIcon className="w-4 h-4" />}
          >
            Create Collection
          </Button>
        </>
      }
    >
      <div className="space-y-6">
        {/* Collection Name */}
        <Input
          label="Collection Name *"
          type="text"
          value={formData.name}
          onChange={(e) => handleInputChange('name', e.target.value)}
          placeholder="Enter collection name"
          fullWidth
          autoFocus
        />

        {/* Privacy Settings */}
        <div>
          <label className="block text-sm font-medium text-gray-100 mb-3">
            Privacy
          </label>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {[
              { value: 'private', icon: '🔒', title: 'Private', desc: 'Only you can access this collection' },
              { value: 'public', icon: '🌐', title: 'Public', desc: 'Anyone can access this collection' },
            ].map((option) => (
              <div key={option.value} className="cursor-pointer">
                <input
                  type="radio"
                  name="visibility"
                  value={option.value}
                  checked={formData.visibility === option.value}
                  onChange={(e) => handleInputChange('visibility', e.target.value as 'private' | 'public')}
                  className="sr-only"
                  id={`visibility-${option.value}`}
                />
                <label
                  htmlFor={`visibility-${option.value}`}
                  className={`block p-4 border-2 rounded-lg text-center transition-colors cursor-pointer ${
                    formData.visibility === option.value
                      ? 'border-blue-60 bg-blue-10'
                      : 'border-gray-20 hover:border-gray-30'
                  }`}
                >
                  <div className="text-2xl mb-2">{option.icon}</div>
                  <div className="font-medium text-gray-100">{option.title}</div>
                  <div className="text-xs text-gray-70 mt-1">{option.desc}</div>
                </label>
              </div>
            ))}
          </div>
        </div>

        {/* File Upload */}
        <FileUpload
          label="Upload Files (Optional)"
          onFilesChange={setUploadedFiles}
          accept=".pdf,.docx,.txt,.md"
          multiple
          maxSize={100}
        />
      </div>
    </Modal>
  );
};

export default LightweightCreateCollectionModal;
