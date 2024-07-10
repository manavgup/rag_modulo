import React, { useState } from 'react';
import { TextInput, Button, Checkbox, FileUploaderDropContainer, FormItem, Form } from '@carbon/react';
import { createCollectionWithDocuments } from '../api/api';

const CollectionForm = ({ onSubmit }) => {
  const [collectionName, setCollectionName] = useState('');
  const [isPrivate, setIsPrivate] = useState(false);
  const [files, setFiles] = useState([]);

  const handleFileDrop = (event) => {
    const newFiles = Array.from(event.addedFiles);
    setFiles((prevFiles) => [...prevFiles, ...newFiles]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const result = await createCollectionWithDocuments(collectionName, isPrivate, files);
      onSubmit(result);
    } catch (error) {
      console.error(error);
      alert('Failed to create collection');
    }
  };

  return (
    <Form className="collection-form" onSubmit={handleSubmit}>
      <TextInput
        id="collection-name"
        labelText="Collection Name"
        value={collectionName}
        onChange={(e) => setCollectionName(e.target.value)}
      />
      <Checkbox
        className="cds--label-description"
        defaultChecked={isPrivate}
        labelText="Private Collection?"
        id="checkbox-label-1"
        onChange={(e) => setIsPrivate(e.target.checked)}
      />
      <FormItem>
        <p className="cds--file--label"> Upload files </p>
        <p className="cds--label-description"> Max file size is 5MB.</p>
        <FileUploaderDropContainer
          accept={[
            'image/jpeg',
            'image/png',
            'text/plain',
            'application/pdf',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-powerpoint',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'application/vnd.ms-excel',
          ]}
          labelText="Drag and drop files here or click to upload"
          multiple
          onAddFiles={(event) => handleFileDrop(event)}
        />
      </FormItem>
      <Button type="submit" kind="primary">
        Create Collection
      </Button>
    </Form>
  );
};

export default CollectionForm;
