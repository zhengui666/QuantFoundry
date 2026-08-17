import type { Preview } from '@storybook/react-vite';
import { mswLoader } from 'msw-storybook-addon/csf3';
import '../src/styles.css';

const preview: Preview = {
  loaders: [mswLoader],
  parameters: {
    a11y: { test: 'error' },
    viewport: {
      options: {
        desktop1180: { name: 'Desktop 1180', styles: { width: '1180px', height: '900px' } },
        desktop1280: { name: 'Desktop 1280', styles: { width: '1280px', height: '900px' } },
        desktop1440: { name: 'Desktop 1440', styles: { width: '1440px', height: '900px' } },
      },
    },
  },
};

export default preview;
