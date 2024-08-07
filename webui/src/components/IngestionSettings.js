import React from 'react';
import {
  Modal,
  NumberInput,
  Dropdown,
  Form,
  FormGroup
} from '@carbon/react';

const IngestionSettings = ({ isOpen, onClose, settings, onSettingsChange }) => {
  return (
    <Modal
      open={isOpen}
      onRequestClose={onClose}
      modalHeading="Ingestion Settings"
      primaryButtonText="Save"
      secondaryButtonText="Cancel"
    >
      <Form>
        <FormGroup legendText="Ingestion Configurations">
          <NumberInput
            id="chunking_strategy"
            label="Chunking Strategy"
            value={settings.chunking_strategy}
            onChange={(e) => onSettingsChange('chunking_strategy', parseInt(e.imaginaryTarget.value))}
          />
          <NumberInput
            id="chunk_overlap"
            label="Chunk Overlap"
            value={settings.chunk_overlap}
            onChange={(e) => onSettingsChange('chunk_overlap', parseInt(e.imaginaryTarget.value))}
          />
          <NumberInput
            id="chunk_size"
            label="Chunk Size"
            value={settings.chunk_size}
            step={0.1}
            min={0}
            max={1}
            onChange={(e) => onSettingsChange('chunk_size', parseFloat(e.imaginaryTarget.value))}
          />
          <Dropdown
            id="database"
            titleText="Select Database"
            label="Database"
            items={['Milvus', 'Elastic', 'Pinecone', 'Chroma']}
            selectedItem={settings.database}
            onChange={(e) => onSettingsChange('database', e.selectedItem)}
          />
        </FormGroup>
      </Form>
    </Modal>
  );
};

export default IngestionSettings;
