import React, { useState, useEffect } from 'react';
import {
  TextInput,
  Button,
  Checkbox,
  FileUploaderDropContainer,
  FormItem,
  Form,
  Tag,
  ProgressBar,
  ToastNotification,
  ExpandableTile,
  TileAboveTheFoldContent,
  TileBelowTheFoldContent,
  Loading
} from '@carbon/react';
import { TrashCan } from '@carbon/icons-react';
import { createCollectionWithDocuments, getUserCollections } from '../api/api';
import { getUser } from '../services/authService';

const CollectionForm = ({ onSubmit }) => {
  const [collectionName, setCollectionName] = useState('');
  const [isPrivate, setIsPrivate] = useState(false);
  const [files, setFiles] = useState([]);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [showError, setShowError] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [showSuccessToast, setShowSuccessToast] = useState(false);
  const [userCollections, setUserCollections] = useState([]);
  const [user, setUser] = useState(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isLoadingCollections, setIsLoadingCollections] = useState(true);

  useEffect(() => {
    const fetchUserAndCollections = async () => {
      const currentUser = await getUser();
      setUser(currentUser);
      if (currentUser) {
        fetchUserCollections(currentUser.id);
      }
    };
    fetchUserAndCollections();
  }, []);

  const fetchUserCollections = async (userId) => {
    setIsLoadingCollections(true);
    try {
      const collections = await getUserCollections(userId);
      setUserCollections(collections);
    } catch (error) {
      console.error('Error fetching user collections:', error);
      setErrorMessage('Failed to fetch user collections. Please try again later.');
      setShowError(true);
    } finally {
      setIsLoadingCollections(false);
    }
  };

  const handleFileDrop = (event) => {
    const newFiles = Array.from(event.target.files || []);
    const filteredFiles = newFiles.filter((file) => {
      const fileType = file.type.toLowerCase();
      return (
        fileType === 'application/pdf' ||
        fileType === 'application/vnd.ms-powerpoint' ||
        fileType === 'text/plain' ||
        fileType === 'application/msword' ||
        fileType === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' ||
        fileType === 'application/vnd.ms-excel' ||
        fileType === 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
      );
    });

    if (filteredFiles.length !== newFiles.length) {
      setErrorMessage('Only PDF, PPT, Text, Word, and Excel files are allowed.');
      setShowError(true);
    } else {
      setShowError(false);
    }

    setFiles((prevFiles) => [...prevFiles, ...filteredFiles]);
  };

  const handleFileRemove = (index) => {
    setFiles((prevFiles) => prevFiles.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!user) {
      setErrorMessage('User not authenticated. Please sign in.');
      setShowError(true);
      return;
    }

    if (files.length === 0) {
      setErrorMessage('Please add at least one file to the collection.');
      setShowError(true);
      return;
    }

    setIsUploading(true);
    const formData = new FormData();
    formData.append('collection_name', collectionName);
    formData.append('is_private', isPrivate);
    formData.append('user_id', user.id);

    files.forEach((file) => {
      formData.append('files', file);
    });

    try {
      const response = await createCollectionWithDocuments(formData, (event) => {
        const percentCompleted = Math.round((event.loaded * 100) / event.total);
        setUploadProgress(percentCompleted);
      });
      console.log('API Response:', response);
      setShowSuccessToast(true);
      onSubmit(response);
      fetchUserCollections(user.id); // Refresh the list of collections
      // Reset form
      setCollectionName('');
      setIsPrivate(false);
      setFiles([]);
      setUploadProgress(0);
    } catch (error) {
      console.error('API Error:', error);
      setShowError(true);
      setErrorMessage(error.response?.data?.message || 'An error occurred while creating the collection.');
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div>
      <h2>Your Collections</h2>
      {isLoadingCollections ? (
        <Loading description="Loading collections" withOverlay={false} />
      ) : userCollections && userCollections.length > 0 ? (
        userCollections.map((collection) => (
          <ExpandableTile key={collection.id}>
            <TileAboveTheFoldContent>
              <h3>{collection.name}</h3>
              <p>{collection.files && collection.files.slice(0, 3).map(file => file.filename).join(', ')}</p>
            </TileAboveTheFoldContent>
            <TileBelowTheFoldContent>
              {collection.files && collection.files.slice(3, 10).map(file => (
                <p key={file.id}>{file.filename}</p>
              ))}
            </TileBelowTheFoldContent>
          </ExpandableTile>
        ))
      ) : (
        <p>No collections found. Create your first collection below!</p>
      )}

      <h2>Create New Collection</h2>
      <Form className="collection-form" onSubmit={handleSubmit}>
        <TextInput
          id="collection-name"
          labelText="Collection Name"
          value={collectionName}
          onChange={(e) => setCollectionName(e.target.value)}
          disabled={isUploading}
        />
        <Checkbox
          className="cds--label-description"
          checked={isPrivate}
          labelText="Private Collection?"
          id="checkbox-label-1"
          onChange={(e) => setIsPrivate(e.target.checked)}
          disabled={isUploading}
        />
        <FormItem>
          <p className="cds--file--label">Upload files</p>
          <p className="cds--label-description">Max file size is 5MB.</p>
          <FileUploaderDropContainer
            accept={[
              'text/plain',
              'application/pdf',
              'application/msword',
              'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
              'application/vnd.ms-powerpoint',
              'application/vnd.openxmlformats-officedocument.presentationml.presentation',
              'application/vnd.ms-excel',
              'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            ]}
            labelText="Drag and drop files here or click to upload"
            multiple
            onAddFiles={handleFileDrop}
            disabled={isUploading}
          />
          {files.length > 0 && (
            <div className="selected-files">
              <p>Selected Files:</p>
              {files.map((file, index) => (
                <div key={index} style={{ display: 'flex', alignItems: 'center', marginBottom: '8px' }}>
                  <Tag type="gray">{file.name}</Tag>
                  <Button
                    kind="ghost"
                    size="sm"
                    hasIconOnly
                    renderIcon={TrashCan}
                    iconDescription="Remove file"
                    tooltipPosition="right"
                    onClick={() => handleFileRemove(index)}
                    style={{ marginLeft: '8px' }}
                    disabled={isUploading}
                  />
                </div>
              ))}
            </div>
          )}
        </FormItem>

        {uploadProgress > 0 && (
          <ProgressBar
            label="Uploading..."
            value={uploadProgress}
          />
        )}

        <Button type="submit" kind="primary" disabled={isUploading || files.length === 0}>
          Create Collection
        </Button>
      </Form>

      {showError && (
        <ToastNotification
          kind="error"
          title="Error"
          subtitle={errorMessage}
          caption=""
          timeout={5000}
          onClose={() => setShowError(false)}
        />
      )}

      {showSuccessToast && (
        <ToastNotification
          kind="success"
          title="Collection Created"
          subtitle="The files are being indexed in the vector DB, please check back later."
          caption=""
          timeout={5000}
          onClose={() => setShowSuccessToast(false)}
        />
      )}
    </div>
  );
};

export default CollectionForm;