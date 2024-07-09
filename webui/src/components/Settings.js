import React from 'react';
import {
  Modal,
  NumberInput,
  Form,
  FormGroup
} from '@carbon/react';

const Settings = ({ isOpen, onClose, settings, onSettingsChange }) => {
  return (
    <Modal
      open={isOpen}
      onRequestClose={onClose}
      modalHeading="LLM Settings"
      primaryButtonText="Save"
      secondaryButtonText="Cancel"
    >
      <Form>
        <FormGroup legendText="LLM Parameters">
          <NumberInput
            id="topK"
            label="Top K"
            value={settings.topK}
            onChange={(e) => onSettingsChange('topK', parseInt(e.imaginaryTarget.value))}
          />
          <NumberInput
            id="numTokens"
            label="Number of Tokens"
            value={settings.numTokens}
            onChange={(e) => onSettingsChange('numTokens', parseInt(e.imaginaryTarget.value))}
          />
          <NumberInput
            id="temperature"
            label="Temperature"
            value={settings.temperature}
            step={0.1}
            min={0}
            max={1}
            onChange={(e) => onSettingsChange('temperature', parseFloat(e.imaginaryTarget.value))}
          />
        </FormGroup>
      </Form>
    </Modal>
  );
};

export default Settings;
