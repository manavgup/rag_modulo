import React, { useState } from 'react';
import { TextInput, Button, Checkbox, FileUploaderDropContainer, FormItem, FormGroup, Form } from '@carbon/react';

const CollectionForm = ({ onSubmit }) => {
  const [collectionName, setCollectionName] = useState('');
  const [isPrivate, setIsPrivate] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit({ collectionName, isPrivate });
  };

  return (
    <Form className="collection-form" onSubmit={handleSubmit}>
        <TextInput id="collection-name" labelText="Collection Name" value={collectionName} onChange={(e) => setCollectionName(e.target.value)}/>
        <Checkbox className='cds--label-description' defaultChecked labelText={`Private Collection? `} id="checkbox-label-1" />
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
            innerRef={{current: '[Circular]'}}
            labelText="Drag and drop files here or click to upload"
            multiple
            name="files"
            onAddFiles={function noRefCheck(){}}
            onChange={function noRefCheck(){}}
        />
        <div className="cds--file-container cds--file-container--drop" />
        </FormItem>
      <Button type="submit" kind="primary">
        Create Collection
      </Button>
    </Form>
  );
};

export default CollectionForm;
